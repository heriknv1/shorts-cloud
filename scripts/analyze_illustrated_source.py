#!/usr/bin/env python3
import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image, ImageDraw, ImageFont
from secure_workflow_payload import load_secure_payload

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work_illustrated_analysis'
OUT=ROOT/'output'
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

GROQ_KEY=os.getenv('GROQ_API_KEY','').strip()
MODEL=os.getenv('GROQ_MODEL','qwen/qwen3.8-27b').strip()
GEMINI_KEY=os.getenv('GEMINI_API_KEY','').strip()
GEMINI_MODEL=os.getenv('GEMINI_VISION_MODEL','gemini-3.1-flash-lite').strip() or 'gemini-3.1-flash-lite'

SOURCE_URL=''
SOURCE_KIND='link'
SOURCE_MIME='application/octet-stream'
SOURCE_NAME='conteudo'
USER_CONTEXT=''
DOODLE_STYLE='clean-doodle'
REQUEST_ID=''
PLAN_KEY=''

RETRYABLE={408,425,429,500,502,503,504}
GENERIC_RX=re.compile(r'\b(personagem|pessoa|homem|mulher|character|person)\s+(fala|falando|olha|olhando|talks?|talking|looks?|looking)\b',re.I)

def load_configuration():
    global SOURCE_URL,SOURCE_KIND,SOURCE_MIME,SOURCE_NAME,USER_CONTEXT,DOODLE_STYLE,REQUEST_ID,PLAN_KEY
    payload=load_secure_payload()
    SOURCE_URL=str(payload.get('source_url') or '').strip()
    SOURCE_KIND=str(payload.get('source_kind') or 'link').strip()
    SOURCE_MIME=str(payload.get('source_mime') or 'application/octet-stream').strip()
    SOURCE_NAME=str(payload.get('source_name') or 'conteudo').strip()[:160]
    USER_CONTEXT=str(payload.get('user_context') or '').strip()[:600]
    DOODLE_STYLE=str(payload.get('doodle_style') or 'clean-doodle').strip()
    REQUEST_ID=str(payload.get('request_id') or '').strip()
    PLAN_KEY=str(payload.get('plan_key') or '').strip()

def run(cmd,quiet=False,sensitive=False):
    print('+',' '.join('[endereço temporário protegido]' if sensitive and str(part)==SOURCE_URL else str(part) for part in cmd),flush=True)
    return subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL if quiet else None,stderr=subprocess.DEVNULL if quiet else None)

def safe_extension():
    mime_map={'audio/mpeg':'.mp3','audio/mp4':'.m4a','audio/m4a':'.m4a','audio/aac':'.aac','audio/x-aac':'.aac','audio/wav':'.wav','audio/ogg':'.ogg','audio/opus':'.opus','audio/webm':'.webm','audio/flac':'.flac','video/mp4':'.mp4','video/webm':'.webm','video/quicktime':'.mov','video/x-m4v':'.m4v','video/mpeg':'.mpeg','video/3gpp':'.3gp','video/x-matroska':'.mkv'}
    ext=mime_map.get(SOURCE_MIME.lower())
    if ext:return ext
    candidate=Path(urlparse(SOURCE_URL).path).suffix.lower()
    return candidate if candidate in {'.mp3','.m4a','.aac','.wav','.ogg','.opus','.webm','.flac','.mp4','.mov','.m4v','.mpeg','.3gp','.mkv'} else '.bin'

def direct_download():
    target=WORK/f'source{safe_extension()}'
    total=0
    try:
        with requests.get(SOURCE_URL,stream=True,timeout=120,headers={'User-Agent':'ShortCloudStudio/5.0'}) as response:
            response.raise_for_status()
            ctype=(response.headers.get('content-type') or '').lower()
            if 'text/html' in ctype:
                raise RuntimeError('O endereço retornou uma página, não um arquivo de mídia.')
            with target.open('wb') as handle:
                for chunk in response.iter_content(1024*1024):
                    if not chunk:continue
                    total+=len(chunk)
                    if total>250*1024*1024:raise RuntimeError('O conteúdo ultrapassa 250 MB.')
                    handle.write(chunk)
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError('Não foi possível obter o arquivo nesse endereço.') from None
    if target.stat().st_size<1000:raise RuntimeError('O arquivo recebido está vazio.')
    return target

def download_source():
    template=str(WORK/'source.%(ext)s')
    fmt='bestaudio/best' if SOURCE_KIND=='audio' else 'bv*+ba/b'
    cmd=['yt-dlp','--no-playlist','--no-warnings','--restrict-filenames','--max-filesize','250M','--merge-output-format','mp4','-f',fmt,'-o',template,SOURCE_URL]
    try:
        run(cmd,quiet=True,sensitive=True)
        candidates=[p for p in WORK.glob('source.*') if p.is_file() and p.stat().st_size>1000]
        if candidates:return max(candidates,key=lambda p:p.stat().st_mtime)
    except Exception:
        print('Leitura principal não concluída; tentando acesso direto.',flush=True)
    return direct_download()

def probe(path):
    raw=subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],text=True)
    data=json.loads(raw)
    streams=data.get('streams') or []
    duration=float(data.get('format',{}).get('duration') or max([float(x.get('duration') or 0) for x in streams] or [0]))
    return data,duration,any(x.get('codec_type')=='video' for x in streams),any(x.get('codec_type')=='audio' for x in streams)

def font(size):
    for path in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf']:
        if Path(path).exists():return ImageFont.truetype(path,size)
    return ImageFont.load_default()

def make_contact_sheets(source,duration_seconds):
    frames=[]
    frame_dir=WORK/'frames';frame_dir.mkdir(exist_ok=True)
    for index in range(12):
        at=max(.05,min(duration_seconds-.05,(index+.5)*duration_seconds/12))
        target=frame_dir/f'frame_{index:02d}.jpg'
        run(['ffmpeg','-y','-ss',f'{at:.3f}','-i',str(source),'-frames:v','1','-vf','scale=240:426:force_original_aspect_ratio=decrease,pad=240:426:(ow-iw)/2:(oh-ih)/2:white','-q:v','4',str(target)],quiet=True)
        frames.append((target,at))
    sheets=[]
    for group in range(3):
        sheet=Image.new('RGB',(480,852),'white');draw=ImageDraw.Draw(sheet);items=frames[group*4:(group+1)*4]
        for local,(path,at) in enumerate(items):
            with Image.open(path) as image:sheet.paste(image.convert('RGB'),((local%2)*240,(local//2)*426))
            x=(local%2)*240+7;y=(local//2)*426+7;label=f'{at:.1f}s';box=draw.textbbox((0,0),label,font=font(15));w=box[2]-box[0]
            draw.rounded_rectangle((x,y,x+w+16,y+27),6,fill=(12,12,16));draw.text((x+8,y+5),label,font=font(15),fill='white')
        output=WORK/f'contact_{group+1}.jpg';sheet.save(output,quality=76,optimize=True);sheets.append(output)
    return sheets

def extract_audio(source):
    target=WORK/'source_audio.flac'
    run(['ffmpeg','-y','-i',str(source),'-vn','-ar','16000','-ac','1','-c:a','flac',str(target)],quiet=True)
    if not target.exists() or target.stat().st_size<1000:raise RuntimeError('Não encontrei áudio utilizável no conteúdo.')
    return target

def request_with_retry(url,**kwargs):
    last=None
    for attempt in range(5):
        try:
            response=requests.post(url,timeout=180,**kwargs)
            if response.status_code not in RETRYABLE:return response
            last=response
        except requests.RequestException as exc:last=exc
        retry_after=0
        if isinstance(last,requests.Response):
            try:retry_after=float(last.headers.get('retry-after') or 0)
            except ValueError:retry_after=0
        time.sleep(min(25,max(retry_after,2+attempt*5)))
    if isinstance(last,requests.Response):return last
    raise last or RuntimeError('Falha de comunicação.')

def transcribe(audio):
    with audio.open('rb') as handle:
        response=request_with_retry('https://api.groq.com/openai/v1/audio/transcriptions',headers={'Authorization':f'Bearer {GROQ_KEY}'},files={'file':(audio.name,handle,'audio/flac')},data=[('model','whisper-large-v3'),('response_format','verbose_json'),('timestamp_granularities[]','segment'),('timestamp_granularities[]','word'),('temperature','0')])
    if not response.ok:
        raise RuntimeError(f'A transcrição não foi concluída (HTTP {response.status_code}).')
    data=response.json()
    if len(str(data.get('text') or '').strip())<3:raise RuntimeError('Não identifiquei falas suficientes nesse áudio.')
    return data

def compact_transcript(data):
    segments=[]
    for item in data.get('segments') or []:
        text=' '.join(str(item.get('text') or '').split())
        if text:segments.append({'start':round(float(item.get('start') or 0),2),'end':round(float(item.get('end') or 0),2),'text':text})
    if not segments:segments=[{'start':0,'end':float(data.get('duration') or 0),'text':' '.join(str(data.get('text') or '').split())}]
    return segments

def compact_visual_summary(value):
    if not isinstance(value,dict):raise RuntimeError('A compreensão visual não retornou dados válidos.')
    timeline=[]
    for item in (value.get('timeline') or [])[:24]:
        if not isinstance(item,dict):continue
        timeline.append({
            'start':round(max(0,float(item.get('start') or 0)),2),
            'end':round(max(0,float(item.get('end') or item.get('start') or 0)),2),
            'people':' '.join(str(item.get('people') or '').split())[:220],
            'visible_action':' '.join(str(item.get('visible_action') or '').split())[:320],
            'objects':' '.join(str(item.get('objects') or '').split())[:220],
            'setting':' '.join(str(item.get('setting') or '').split())[:220],
            'expression':' '.join(str(item.get('expression') or '').split())[:180],
        })
    characters=[]
    for item in (value.get('characters') or [])[:8]:
        if not isinstance(item,dict):continue
        characters.append({
            'label':' '.join(str(item.get('label') or '').split())[:50],
            'appearance':' '.join(str(item.get('appearance') or '').split())[:300],
        })
    if not timeline:raise RuntimeError('O Gemini não identificou acontecimentos visuais suficientes no vídeo.')
    return{
        'overall_context':' '.join(str(value.get('overall_context') or '').split())[:700],
        'characters':characters,
        'timeline':timeline,
    }

def understand_video_with_gemini(paths,duration_seconds):
    if not paths:return{'overall_context':'Fonte somente em áudio; use a transcrição como verdade principal.','characters':[],'timeline':[]}
    if not GEMINI_KEY:raise RuntimeError('O analisador visual do Gemini ainda não está configurado.')
    prompt=f'''Analise estas três grades cronológicas de um vídeo vertical com duração de {duration_seconds:.3f}s. Cada quadro possui o horário impresso.
Retorne um resumo visual factual e compacto para outro modelo criar um storyboard de desenho sincronizado.

REGRAS:
- Siga a ordem dos horários e descreva apenas o que realmente está visível.
- Identifique pessoas recorrentes por rótulos neutros, como Pessoa 1 e Pessoa 2, usando somente cabelo, roupa, óculos e características visuais objetivas.
- Não infira etnia, religião, saúde, orientação, parentesco ou identidade.
- Para cada mudança útil, registre intervalo aproximado, pessoa, ação, expressão, objetos e ambiente.
- Não copie nem transcreva marca d'água, nome de perfil, legenda ou identidade do vídeo.
- Seja específico e conciso; não invente ações entre quadros.

Retorne SOMENTE JSON:
{{"overall_context":"contexto visual em português","characters":[{{"label":"Pessoa 1","appearance":"descrição objetiva"}}],"timeline":[{{"start":0.0,"end":2.3,"people":"Pessoa 1","visible_action":"ação observada","objects":"objetos relevantes","setting":"ambiente","expression":"expressão visível"}}]}}'''
    parts=[{'text':prompt}]
    for path in paths[:3]:parts.append({'inlineData':{'mimeType':'image/jpeg','data':base64.b64encode(path.read_bytes()).decode('ascii')}})
    body={'contents':[{'role':'user','parts':parts}],'generationConfig':{'temperature':.15,'maxOutputTokens':3600,'responseMimeType':'application/json'}}
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'
    response=request_with_retry(url,headers={'x-goog-api-key':GEMINI_KEY,'Content-Type':'application/json'},json=body)
    if not response.ok:raise RuntimeError(f'A compreensão visual do Gemini não foi concluída (HTTP {response.status_code}).')
    data=response.json();text=''.join(str(part.get('text') or '') for part in data.get('candidates',[{}])[0].get('content',{}).get('parts',[]))
    return compact_visual_summary(extract_json(text))

def plan_prompt(transcription,duration_seconds,visual_summary,attempt):
    segments=compact_transcript(transcription)
    has_video=bool(visual_summary.get('timeline'))
    target=max(6,min(22,round(duration_seconds/1.35)))
    correction='' if attempt==0 else '\nA tentativa anterior foi rejeitada por conter cenas vagas ou pouca criatividade. Refaça com uma ação visual específica, uma reação e um detalhe cômico diferente em CADA trecho.'
    return f'''Você é diretor de uma animação 2D curta guiada por ÁUDIO REAL. Crie um storyboard original, coerente, muito criativo e divertido em português do Brasil.

DURAÇÃO EXATA: {duration_seconds:.3f} segundos
TIPO DA FONTE: {'vídeo previamente analisado pelo Gemini' if has_video else 'áudio sem imagens'}
ORIENTAÇÃO DO USUÁRIO: {USER_CONTEXT or 'nenhuma; respeite integralmente o contexto detectado'}
ESTILO ESCOLHIDO: {DOODLE_STYLE}
TRANSCRIÇÃO TEMPORIZADA: {json.dumps(segments,ensure_ascii=False)}
RESUMO VISUAL TEMPORIZADO DO GEMINI: {json.dumps(visual_summary,ensure_ascii=False)}

COMPREENSÃO OBRIGATÓRIA:
- Entenda primeiro assunto, participantes visíveis, mudanças de contexto, intenção, subtexto e momento da graça. Use o resumo visual somente como observação dos quadros e a transcrição como verdade das falas.
- Descreva apenas características visuais objetivas úteis à continuidade, como cabelo, óculos, roupa e formato do personagem. Não infira etnia, religião, saúde, orientação ou identidade.
- Preserve as falas; não invente, reescreva ou acrescente diálogo.

DIREÇÃO CRIATIVA OBRIGATÓRIA:
- Produza aproximadamente {target} beats, normalmente entre 0,8 e 2,0 segundos, com início/fim cobrindo o áudio inteiro sem lacunas.
- É proibido entregar cenas vagas como “personagem falando”, “pessoa olhando” ou “alguém pensando”. Cada beat deve ter uma ação visível, expressão, pose, objeto e/ou piada visual diretamente ligada àquela fala.
- Use timing cômico: preparação, reação, surpresa, exagero, contraste, repetição com variação e callback quando o áudio permitir. Nunca force humor que contradiga o contexto sério.
- Crie personagens ORIGINAIS e consistentes. Não copie personagens, marca d’água, assinatura ou estilo identificável do vídeo de origem.
- Estética fixa: fundo branco quente, traço preto limpo e bonito, formas simples, expressões muito legíveis, poucos detalhes e no máximo uma cor de acento. Sem cenário genérico, sem fotografia, sem 3D.
- on_screen_text deve ter de 1 a 4 palavras realmente faladas naquele intervalo. O texto será aplicado depois; visual_prompt deve pedir explicitamente NO TEXT.
- visual_prompt deve estar EM INGLÊS e descrever composição, personagem por ID, ação, expressão e objeto específico do beat.
- Alterne enquadramentos e poses, mas não use zoom, movimento de câmera, tremor, glitch ou transições chamativas.

Retorne SOMENTE JSON válido:
{{
 "title":"título curto",
 "summary":"o contexto compreendido em 1 ou 2 frases",
 "characters":[{{"id":"C1","name":"nome funcional","description":"aparência objetiva e fixa em inglês"}}],
 "visual_context":"bíblia visual completa em inglês, com traço, paleta e continuidade",
 "scenes":[{{
   "start":0.0,"end":1.4,"speaker":"Pessoa 1","beat":"nome curto",
   "narration":"fala exata deste intervalo","emotion":"emoção visível",
   "character_ids":["C1"],"on_screen_text":"palavras exatas",
   "visual_gag":"ação/reação criativa e coerente em português",
   "visual_description":"descrição clara para revisão em português",
   "visual_prompt":"prompt visual específico em inglês, terminando com no text, no watermark"
 }}]
}}{correction}'''

def extract_json(text):
    raw=re.sub(r'^```(?:json)?\s*|\s*```$','',str(text or '').strip(),flags=re.I)
    match=re.search(r'\{[\s\S]*\}',raw)
    if not match:raise RuntimeError('A direção criativa não retornou um storyboard válido.')
    return json.loads(match.group(0))

def ask_storyboard(transcription,duration_seconds,visual_summary):
    for attempt in range(2):
        content=plan_prompt(transcription,duration_seconds,visual_summary,attempt)
        payload={'model':MODEL,'temperature':.72 if attempt==0 else .66,'max_completion_tokens':7600,'response_format':{'type':'json_object'},'messages':[{'role':'user','content':content}]}
        response=request_with_retry('https://api.groq.com/openai/v1/chat/completions',headers={'Authorization':f'Bearer {GROQ_KEY}','Content-Type':'application/json'},json=payload)
        if not response.ok:
            if attempt:raise RuntimeError(f'A direção criativa não foi concluída (HTTP {response.status_code}).')
            continue
        try:raw=extract_json(response.json().get('choices',[{}])[0].get('message',{}).get('content',''))
        except Exception:
            if attempt:raise
            continue
        scenes=raw.get('scenes') or []
        generic=sum(1 for scene in scenes if len(str(scene.get('visual_gag') or ''))<18 or len(str(scene.get('visual_prompt') or ''))<30 or GENERIC_RX.search(str(scene.get('visual_description') or '')))
        if 4<=len(scenes)<=28 and generic<=max(1,len(scenes)//6):return raw
    raise RuntimeError('O storyboard ficou genérico e foi recusado automaticamente.')

def timestamp_words(transcription,start,end):
    picked=[]
    for item in transcription.get('words') or []:
        mid=(float(item.get('start') or 0)+float(item.get('end') or 0))/2
        if start-.03<=mid<end+.03:
            word=str(item.get('word') or '').strip()
            if word:picked.append(word)
    if picked:return ' '.join(picked).strip()
    segments=[]
    for item in transcription.get('segments') or []:
        a=float(item.get('start') or 0);b=float(item.get('end') or a)
        if b>start and a<end:
            text=' '.join(str(item.get('text') or '').split())
            if text:segments.append(text)
    return ' '.join(segments).strip()

def safe_screen_text(value,narration):
    value=' '.join(str(value or '').split())[:48]
    spoken=set(re.findall(r'[\wÀ-ÿ]+',str(narration or '').lower()))
    chosen=re.findall(r'[\wÀ-ÿ]+',value.lower())
    if chosen and all(word in spoken for word in chosen):return value
    words=re.findall(r'[\wÀ-ÿ]+',str(narration or ''))
    return ' '.join(words[:min(3,len(words))])[:48]

def normalize_plan(raw,transcription,duration_seconds):
    source_scenes=(raw.get('scenes') or [])[:24]
    if len(source_scenes)<4:raise RuntimeError('O storyboard retornou poucas cenas.')
    normalized=[];cursor=0.0
    for index,scene in enumerate(source_scenes):
        remaining=len(source_scenes)-index-1
        if index==len(source_scenes)-1:end=duration_seconds
        else:
            proposed=float(scene.get('end') or (cursor+duration_seconds/len(source_scenes)))
            maximum=duration_seconds-remaining*.45
            end=min(maximum,max(cursor+.45,proposed))
        narration=timestamp_words(transcription,cursor,end) or ' '.join(str(scene.get('narration') or '').split())
        if not narration:narration='Trecho sem fala'
        visual_gag=' '.join(str(scene.get('visual_gag') or scene.get('visual_description') or '').split())[:700]
        visual_description=' '.join(str(scene.get('visual_description') or visual_gag).split())[:900]
        visual_prompt=' '.join(str(scene.get('visual_prompt') or '').split())[:1100]
        if 'no text' not in visual_prompt.lower():visual_prompt=f'{visual_prompt}, no text, no watermark'.strip(' ,')
        ids=scene.get('character_ids') if isinstance(scene.get('character_ids'),list) else []
        normalized.append({'start':round(cursor,3),'end':round(end,3),'speaker':str(scene.get('speaker') or 'Voz').strip()[:60],'beat':str(scene.get('beat') or f'Beat {index+1}').strip()[:100],'narration':narration[:700],'emotion':str(scene.get('emotion') or '').strip()[:100],'character_ids':[str(x)[:20] for x in ids[:5]],'on_screen_text':safe_screen_text(scene.get('on_screen_text'),narration),'visual_gag':visual_gag,'visual_description':visual_description,'visual_query':visual_prompt,'visual_query_backup':visual_prompt,'recommended_media':'image'})
        cursor=end
    normalized[-1]['end']=round(duration_seconds,3)
    chars=[]
    for index,item in enumerate((raw.get('characters') or [])[:5]):
        if not isinstance(item,dict):continue
        chars.append({'id':str(item.get('id') or f'C{index+1}')[:20],'name':str(item.get('name') or f'Personagem {index+1}')[:60],'description':' '.join(str(item.get('description') or '').split())[:500]})
    if not chars:chars=[{'id':'C1','name':'Personagem principal','description':'original simple rounded doodle character with a memorable silhouette and expressive eyes'}]
    fixed_style={'clean-doodle':'clean confident black monoline, warm white background, balanced negative space, one muted violet accent','soft-accent':'clean black monoline, warm white background, sparse soft pastel accents, elegant negative space','playful-ink':'expressive black ink line with controlled handmade variation, warm white background, one muted coral accent'}[DOODLE_STYLE if DOODLE_STYLE in {'clean-doodle','soft-accent','playful-ink'} else 'clean-doodle']
    context=f"Original audio-driven limited 2D doodle animation. {fixed_style}. Stable character proportions, clothing and facial features across every frame. Expressive readable poses, tasteful humorous timing, no photorealism, no 3D, no text inside generated art, no watermark. {str(raw.get('visual_context') or '')[:900]}"
    title=str(raw.get('title') or 'Áudio Ilustrado').strip()[:180]
    summary=str(raw.get('summary') or 'Animação ilustrada criada a partir do áudio original.').strip()[:700]
    return {'title':title,'summary':summary,'description':summary,'hashtags':['#AudioIlustrado','#Animacao2D','#Storytime'],'niche_key':'audio-illustrated','analysis_id':REQUEST_ID,'duration_seconds':round(duration_seconds,3),'visual_context':context[:1800],'characters':chars,'source':{'kind':SOURCE_KIND,'mime':SOURCE_MIME,'name':SOURCE_NAME,'duration_seconds':round(duration_seconds,3),'audio_preserved':True},'scenes':normalized}

def write_protected_json(path,value):
    serialized=json.dumps(value,ensure_ascii=False,indent=2).encode('utf-8')
    nonce=os.urandom(12)
    encrypted=b'ILA1'+nonce+AESGCM(bytes.fromhex(PLAN_KEY)).encrypt(nonce,serialized,REQUEST_ID.encode('utf-8'))
    path.write_bytes(encrypted)

def safe_error_message(error):
    text=' '.join(str(error or '').split())
    if 'HTTP 413' in text:return 'O pacote de compreensão ficou grande demais. O processamento foi interrompido sem gerar um vídeo incompleto.'
    if 'HTTP 429' in text:return 'Muita atividade nos serviços de inteligência no momento. Aguarde alguns instantes e tente novamente.'
    if 'Gemini' in text:return 'O Gemini não conseguiu concluir a compreensão visual desse vídeo agora. Tente novamente em alguns instantes.'
    if 'transcrição' in text.lower() or 'falas suficientes' in text.lower():return text[:300]
    if 'duração entre' in text or 'faixa de áudio' in text or 'arquivo recebido' in text:return text[:300]
    if 'obter o arquivo' in text or 'retornou uma página' in text:return 'Não foi possível acessar o conteúdo enviado. Se for um link protegido, envie o arquivo diretamente.'
    if 'storyboard' in text.lower() or 'direção criativa' in text.lower():return text[:300]
    return 'A análise foi interrompida por uma falha interna. Tente novamente; se persistir, o diagnóstico ficará registrado sem expor seu conteúdo.'

def main():
    load_configuration()
    if not SOURCE_URL.startswith('https://'):raise RuntimeError('Fonte pública inválida.')
    if not GROQ_KEY:raise RuntimeError('O motor de compreensão ainda não está configurado.')
    if not re.fullmatch(r'[a-f0-9]{64}',PLAN_KEY):raise RuntimeError('A proteção temporária do storyboard não foi configurada.')
    source=download_source();data,duration_seconds,has_video,has_audio=probe(source)
    if not has_audio:raise RuntimeError('O conteúdo não possui uma faixa de áudio utilizável.')
    if duration_seconds<5 or duration_seconds>180:raise RuntimeError('Use conteúdo com duração entre 5 segundos e 3 minutos.')
    print(f'Conteúdo preparado: {duration_seconds:.2f}s, vídeo={has_video}, áudio={has_audio}',flush=True)
    audio=extract_audio(source);transcription=transcribe(audio);sheets=make_contact_sheets(source,duration_seconds) if has_video else []
    visual_summary=understand_video_with_gemini(sheets,duration_seconds)
    print('Compreensão visual compacta concluída.',flush=True)
    raw=ask_storyboard(transcription,duration_seconds,visual_summary);plan=normalize_plan(raw,transcription,duration_seconds)
    write_protected_json(OUT/'illustrated_plan.enc',plan)
    print(json.dumps({'ok':True,'duration':duration_seconds,'scenes':len(plan['scenes']),'characters':len(plan['characters'])},ensure_ascii=False),flush=True)

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        message=safe_error_message(error)
        if re.fullmatch(r'[a-f0-9]{64}',PLAN_KEY or '') and REQUEST_ID:
            try:write_protected_json(OUT/'illustrated_error.enc',{'error':message})
            except Exception:pass
        print(f'Falha segura da análise: {message}',flush=True)
        raise SystemExit(1)
