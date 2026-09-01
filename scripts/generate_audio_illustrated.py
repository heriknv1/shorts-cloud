#!/usr/bin/env python3
import base64
import hashlib
import json
import math
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont

import flux_runtime
import visual_engine

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work_illustrated'
OUT=ROOT/'output'
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

SOURCE_URL=os.getenv('INPUT_SOURCE_URL','').strip()
SOURCE_KIND=os.getenv('INPUT_SOURCE_KIND','link').strip()
SOURCE_MIME=os.getenv('INPUT_SOURCE_MIME','application/octet-stream').strip()
DOODLE_STYLE=os.getenv('INPUT_DOODLE_STYLE','clean-doodle').strip()

def run(cmd,quiet=False,sensitive=False):
    print('+',' '.join('[endereço temporário protegido]' if sensitive and str(part)==SOURCE_URL else str(part) for part in cmd),flush=True)
    return subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL if quiet else None,stderr=subprocess.DEVNULL if quiet else None)

def duration(path):
    value=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],text=True).strip()
    return float(value)

def source_extension():
    mapping={'audio/mpeg':'.mp3','audio/mp4':'.m4a','audio/m4a':'.m4a','audio/aac':'.aac','audio/x-aac':'.aac','audio/wav':'.wav','audio/ogg':'.ogg','audio/opus':'.opus','audio/webm':'.webm','audio/flac':'.flac','video/mp4':'.mp4','video/webm':'.webm','video/quicktime':'.mov','video/x-m4v':'.m4v','video/mpeg':'.mpeg','video/3gpp':'.3gp','video/x-matroska':'.mkv'}
    if SOURCE_MIME.lower() in mapping:return mapping[SOURCE_MIME.lower()]
    ext=Path(urlparse(SOURCE_URL).path).suffix.lower()
    return ext if ext in {'.mp3','.m4a','.aac','.wav','.ogg','.opus','.webm','.flac','.mp4','.mov','.m4v','.mpeg','.3gp','.mkv'} else '.bin'

def direct_download():
    target=WORK/f'source{source_extension()}';total=0
    try:
        with requests.get(SOURCE_URL,stream=True,timeout=120,headers={'User-Agent':'ShortCloudStudio/5.0'}) as response:
            response.raise_for_status()
            if 'text/html' in (response.headers.get('content-type') or '').lower():raise RuntimeError('O link não entregou um arquivo de mídia.')
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
    return target

def download_source():
    template=str(WORK/'source.%(ext)s');fmt='bestaudio/best' if SOURCE_KIND=='audio' else 'bv*+ba/b'
    try:
        run(['yt-dlp','--no-playlist','--quiet','--no-progress','--no-warnings','--restrict-filenames','--max-filesize','250M','--merge-output-format','mp4','-f',fmt,'-o',template,SOURCE_URL],quiet=True,sensitive=True)
        files=[p for p in WORK.glob('source.*') if p.is_file() and p.stat().st_size>1000]
        if files:return max(files,key=lambda p:p.stat().st_mtime)
    except Exception:print('Leitura principal indisponível; tentando acesso direto.',flush=True)
    return direct_download()

def font_path():
    candidates=[ROOT/'assets/PatrickHand-Regular.ttf',Path('/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')]
    return next((p for p in candidates if p.exists()),candidates[-1])

def style_direction():
    return {
        'clean-doodle':'clean confident black monoline, warm white background, one muted violet accent, balanced negative space',
        'soft-accent':'clean elegant black monoline, warm white background, sparse soft pastel accents, balanced negative space',
        'playful-ink':'expressive controlled black ink line, warm white background, one muted coral accent, handmade but polished'
    }.get(DOODLE_STYLE,'clean confident black monoline, warm white background, one muted violet accent, balanced negative space')

def scene_prompt(scene):
    ids=', '.join(scene.get('character_ids') or []) or 'the appropriate recurring character'
    visual=str(scene.get('visual_query') or scene.get('visual_description') or '').strip()
    return f'''{visual}. Use exactly the recurring original characters {ids} from the supplied character reference, preserving their silhouettes, faces, hair, clothing and proportions. {style_direction()}. One clear readable action and one strong expressive reaction tied to this exact audio beat. Minimal purposeful props only, generous clean space above the characters for later typography. Flat 2D editorial doodle, simple beautiful shapes, crisp high-resolution vertical 9:16 composition. No written words, no letters, no captions, no speech bubbles, no watermark, no logo, no photorealism, no 3D.'''

def make_character_reference(plan):
    if not (visual_engine.CF_ACCOUNT_ID and visual_engine.CF_API_TOKEN):raise RuntimeError('O motor de desenhos consistentes ainda não está configurado.')
    characters=plan.get('characters') or []
    descriptions='; '.join(f"{x.get('id','C')}: {x.get('description','original rounded doodle character')}" for x in characters[:5])
    prompt=f'''ORIGINAL character reference sheet for an audio-driven limited 2D doodle animation. {style_direction()}. Characters shown separately in clear full-body neutral poses with simple front and three-quarter views. Locked memorable silhouettes, stable facial proportions, hair, clothing and accent color. Character definitions: {descriptions}. Beautiful professional editorial doodle design, expressive eyes, simple readable hands, pure uncluttered background, no scenery, no words, no letters, no watermark, no logo, no resemblance to an existing cartoon franchise.'''
    target=WORK/'character_reference.jpg';seed=int(hashlib.sha256((descriptions+DOODLE_STYLE).encode()).hexdigest()[:8],16)
    if not visual_engine.cf_klein(prompt,target,seed,None) or not target.exists() or target.stat().st_size<20000:raise RuntimeError('Não foi possível fixar a aparência dos personagens. A geração foi interrompida para não entregar desenhos incoerentes.')
    return target

def draw_top_text(image_path,text,index):
    text=' '.join(str(text or '').split())[:48]
    with Image.open(image_path) as raw:
        image=raw.convert('RGB').resize((1080,1920),Image.Resampling.LANCZOS)
    if text:
        draw=ImageDraw.Draw(image);size=106 if len(text)<=13 else 88 if len(text)<=24 else 72;face=ImageFont.truetype(str(font_path()),size)
        max_width=900;words=text.upper().split();lines=[];current=[]
        for word in words:
            candidate=' '.join([*current,word]);box=draw.textbbox((0,0),candidate,font=face,stroke_width=1)
            if current and box[2]-box[0]>max_width:lines.append(' '.join(current));current=[word]
            else:current.append(word)
        if current:lines.append(' '.join(current))
        lines=lines[:2];heights=[draw.textbbox((0,0),line,font=face,stroke_width=1)[3] for line in lines];total=sum(heights)+max(0,len(lines)-1)*8;y=max(80,255-total//2)
        for line,h in zip(lines,heights):
            box=draw.textbbox((0,0),line,font=face,stroke_width=1);w=box[2]-box[0];x=(1080-w)//2
            draw.rounded_rectangle((x-24,y-10,x+w+24,y+h+13),18,fill=(255,253,249,232))
            draw.text((x,y),line,font=face,fill=(22,20,27),stroke_width=1,stroke_fill=(22,20,27));y+=h+8
    final=WORK/f'illustrated_{index:02d}.jpg';image.save(final,quality=94,optimize=True);return final

def generate_scenes(plan,reference):
    images=[];previous=None
    for index,scene in enumerate(plan.get('scenes') or []):
        raw=WORK/f'raw_{index:02d}.jpg';visual=str(scene.get('visual_query') or scene.get('visual_description') or '').strip();prompt=scene_prompt(scene)
        seed=int(hashlib.sha256((visual+str(index)+os.getenv('GITHUB_RUN_ID','')).encode()).hexdigest()[:8],16)
        ok=visual_engine.cf_klein(prompt,raw,seed,reference)
        if not ok and previous is not None:ok=visual_engine.cf_klein(prompt+' Preserve the exact identity from the previous beat while changing only pose and action.',raw,seed+17,previous)
        if not ok or not raw.exists() or raw.stat().st_size<20000:raise RuntimeError(f'A cena {index+1} não manteve o padrão visual e foi interrompida em vez de usar uma imagem genérica.')
        final=draw_top_text(raw,scene.get('on_screen_text'),index);images.append(final);previous=final
        print(f'Desenho {index+1}/{len(plan.get("scenes") or [])} concluído.',flush=True)
    return images

def image_sheets(images):
    sheets=[]
    for group in range(math.ceil(len(images)/8)):
        batch=images[group*8:(group+1)*8];sheet=Image.new('RGB',(480,1704),'white');draw=ImageDraw.Draw(sheet);label_font=ImageFont.truetype(str(font_path()),22)
        for local,path in enumerate(batch):
            with Image.open(path) as raw:thumb=raw.convert('RGB').resize((240,426),Image.Resampling.LANCZOS)
            x=(local%2)*240;y=(local//2)*426;sheet.paste(thumb,(x,y));number=str(group*8+local+1);draw.rounded_rectangle((x+7,y+7,x+45,y+40),7,fill=(15,14,19));draw.text((x+17,y+9),number,font=label_font,fill='white',anchor='ma')
        target=WORK/f'quality_sheet_{group+1}.jpg';sheet.save(target,quality=74,optimize=True);sheets.append(target)
    return sheets[:3]

def visual_quality_review(plan,images):
    key=os.getenv('GROQ_API_KEY','').strip();model=os.getenv('GROQ_MODEL','qwen/qwen3.8-27b').strip()
    if not key:return []
    expectations=[{'index':i+1,'characters':s.get('character_ids',[]),'spoken':s.get('narration',''),'required_action':s.get('visual_gag') or s.get('visual_description',''),'intentional_top_text':s.get('on_screen_text','')} for i,s in enumerate(plan.get('scenes') or [])]
    prompt=f'''Você é revisor visual rigoroso de uma animação doodle. As grades anexas contêm as cenas numeradas. Compare cada desenho SOMENTE com a expectativa correspondente: {json.dumps(expectations,ensure_ascii=False)}
Marque uma cena apenas se houver erro material: personagem trocou de aparência/roupa, ação ou objeto contradiz a fala, desenho virou foto/3D, apareceu texto ilegível além da palavra intencional no topo, surgiram pessoas/objetos sem relação, ou a imagem é uma pose genérica sem representar a ação exigida. Variações normais de pose e enquadramento são desejáveis. Não avalie nem reproduza marcas d'água do conteúdo original. Retorne SOMENTE JSON: {{"bad_indices":[1],"reasons":["motivo curto"]}}.'''
    content=[{'type':'text','text':prompt}]
    for path in image_sheets(images):content.append({'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(path.read_bytes()).decode('ascii')}})
    payload={'model':model,'temperature':0,'max_completion_tokens':900,'response_format':{'type':'json_object'},'messages':[{'role':'user','content':content}]}
    for attempt in range(2):
        try:
            response=requests.post('https://api.groq.com/openai/v1/chat/completions',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=payload,timeout=150)
            if response.status_code in {408,425,429,500,502,503,504}:time.sleep(2+attempt*4);continue
            if not response.ok:return []
            text=str(response.json().get('choices',[{}])[0].get('message',{}).get('content','{}'));match=re.search(r'\{[\s\S]*\}',text);data=json.loads(match.group(0) if match else '{}');indices=[int(x)-1 for x in data.get('bad_indices',[]) if str(x).isdigit() and 1<=int(x)<=len(images)];reasons=data.get('reasons') or []
            return [(idx,str(reasons[pos] if pos<len(reasons) else 'corrigir coerência visual')[:240]) for pos,idx in enumerate(indices)]
        except Exception:time.sleep(2+attempt*3)
    return []

def repair_rejected_images(plan,images,reference):
    rejected=visual_quality_review(plan,images)
    if not rejected:
        print('Revisão visual: cenas aprovadas.',flush=True);return images
    print(f'Revisão visual pediu correção de {len(rejected)} cena(s).',flush=True)
    for index,reason in rejected:
        scene=plan['scenes'][index];raw=WORK/f'raw_repaired_{index:02d}.jpg';prompt=scene_prompt(scene)+f' QUALITY CORRECTION: {reason}. Rebuild this beat clearly while keeping the exact reference character identity.';seed=int(hashlib.sha256((prompt+os.getenv('GITHUB_RUN_ID','')).encode()).hexdigest()[:8],16)
        if not visual_engine.cf_klein(prompt,raw,seed,reference) or not raw.exists() or raw.stat().st_size<20000:raise RuntimeError(f'A cena {index+1} foi recusada pela revisão visual e não pôde ser corrigida.')
        images[index]=draw_top_text(raw,scene.get('on_screen_text'),index)
    remaining=visual_quality_review(plan,images)
    if remaining:
        numbers=', '.join(str(index+1) for index,_ in remaining)
        raise RuntimeError(f'As cenas {numbers} continuaram incoerentes após a correção; o vídeo foi interrompido para não entregar um resultado genérico.')
    print('Revisão visual final: cenas corrigidas e aprovadas.',flush=True)
    return images

def srt_time(seconds):
    millis=max(0,int(round(seconds*1000)));hours,millis=divmod(millis,3600000);minutes,millis=divmod(millis,60000);secs,millis=divmod(millis,1000)
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'

def ass_time(seconds):
    centis=max(0,int(round(seconds*100)));hours,centis=divmod(centis,360000);minutes,centis=divmod(centis,6000);secs,centis=divmod(centis,100)
    return f'{hours}:{minutes:02d}:{secs:02d}.{centis:02d}'

def caption_chunks(scene,font_size):
    words=str(scene.get('narration') or '').split();per=6 if font_size<=48 else 5 if font_size<=62 else 4 if font_size<=76 else 3
    return [' '.join(words[i:i+per]) for i in range(0,len(words),per)] or ['']

def write_captions(plan,font_name,font_size):
    srt=[];events=[];number=1
    for scene in plan.get('scenes') or []:
        start=float(scene.get('start') or 0);end=float(scene.get('end') or start+.5);chunks=caption_chunks(scene,font_size);part=max(.08,(end-start)/len(chunks))
        for index,text in enumerate(chunks):
            a=start+index*part;b=end if index==len(chunks)-1 else min(end,a+part);srt.extend([str(number),f'{srt_time(a)} --> {srt_time(b)}',text,'']);number+=1
            safe=str(text).replace('\\',' ').replace('{','(').replace('}',')').replace('\n',' ');events.append(f'Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{safe}')
    (OUT/'captions.srt').write_text('\n'.join(srt),encoding='utf-8')
    header=f'''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Default,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H88000000,-1,0,0,0,100,100,0,0,3,3,0,2,72,72,120,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'''
    target=WORK/'captions.ass';target.write_text(header+'\n'.join(events)+'\n',encoding='utf-8');return target

def make_silent_video(images,scenes,total):
    manifest=WORK/'illustrated_images.txt';rows=[]
    for image,scene in zip(images,scenes):
        seconds=max(.1,float(scene.get('end') or 0)-float(scene.get('start') or 0));rows.extend([f"file '{image.resolve()}'",f'duration {seconds:.6f}'])
    rows.append(f"file '{images[-1].resolve()}'");manifest.write_text('\n'.join(rows),encoding='utf-8')
    target=WORK/'illustrated_silent.mp4';run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(manifest),'-t',f'{total:.3f}','-vf','fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p','-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(target)],quiet=True);return target

def mux_audio(video,source,total,captions_ass,captions_on):
    audio=WORK/'original_audio.m4a';run(['ffmpeg','-y','-i',str(source),'-vn','-ar','48000','-ac','2','-c:a','aac','-b:a','192k',str(audio)],quiet=True)
    final=OUT/'final.mp4';cmd=['ffmpeg','-y','-i',str(video),'-i',str(audio)]
    if captions_on:cmd.extend(['-vf',f'ass={captions_ass}'])
    cmd.extend(['-map','0:v:0','-map','1:a:0','-t',f'{total:.3f}','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-profile:v','high','-level','4.1','-c:a','aac','-b:a','192k','-movflags','+faststart',str(final)])
    run(cmd,quiet=True)
    if os.getenv('INPUT_CLEAN_EXPORT','off')=='on' and captions_on:
        clean=OUT/'final_sem_legenda.mp4';run(['ffmpeg','-y','-i',str(video),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-t',f'{total:.3f}','-c:v','copy','-c:a','copy','-movflags','+faststart',str(clean)],quiet=True)
    return final

def main():
    plan=json.loads(os.environ['INPUT_PLAN_JSON']);scenes=plan.get('scenes') or []
    if len(scenes)<4:raise RuntimeError('Storyboard ilustrado com poucas cenas.')
    if not SOURCE_URL.startswith('https://'):raise RuntimeError('Fonte do áudio inválida.')
    flux_runtime.install();source=download_source();source_duration=duration(source);planned=float(plan.get('source',{}).get('duration_seconds') or plan.get('duration_seconds') or source_duration);total=min(source_duration,planned)
    if total<5 or total>180:raise RuntimeError('Duração do conteúdo fora da faixa permitida.')
    reference=make_character_reference(plan);images=generate_scenes(plan,reference);images=repair_rejected_images(plan,images,reference);silent=make_silent_video(images,scenes,total)
    font_name=re.sub(r'[^A-Za-z0-9 _-]','',os.getenv('INPUT_CAPTION_FONT','Montserrat'))[:50] or 'Montserrat';font_size=max(36,min(92,int(os.getenv('INPUT_CAPTION_SIZE','70'))));captions=write_captions(plan,font_name,font_size);captions_on=os.getenv('INPUT_CAPTIONS','on')=='on';final=mux_audio(silent,source,total,captions,captions_on)
    metadata={'title':plan.get('title') or 'Áudio Ilustrado','summary':plan.get('summary',''),'niche_key':'audio-illustrated','visual_style':'original-minimal-doodle','doodle_style':DOODLE_STYLE,'characters':plan.get('characters',[]),'audio_preserved':True,'captions':captions_on,'caption_position':'bottom','caption_size':font_size,'source_duration_seconds':round(source_duration,3),'duration_seconds':round(duration(final),3),'scene_sources':[{'scene':i+1,'type':'consistent-generated-doodle'} for i in range(len(scenes))],'engine':'Short Cloud Studio'}
    (OUT/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'media_usage.json').write_text(json.dumps({'photos':[],'videos':[],'generated_doodles':len(scenes)},ensure_ascii=False),encoding='utf-8')
    if not final.exists() or final.stat().st_size<150000:raise RuntimeError('O vídeo ilustrado final ficou inválido.')
    print(json.dumps({'ok':True,'duration':metadata['duration_seconds'],'scenes':len(scenes)},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
