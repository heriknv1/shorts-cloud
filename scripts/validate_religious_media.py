#!/usr/bin/env python3
import base64
import json
import os
import subprocess
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work_turbo'
API_KEY=os.getenv('GROQ_API_KEY','').strip()
configured=os.getenv('GROQ_MODEL','').strip()
MODEL=configured if configured in {'qwen/qwen3.6-27b','qwen/qwen3.8-27b'} else 'qwen/qwen3.8-27b'

def duration(path):
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True,check=True)
    return max(.1,float(p.stdout.strip() or .1))

def frame(clip,out):
    at=max(.05,duration(clip)*.5)
    subprocess.run(['ffmpeg','-y','-ss',f'{at:.3f}','-i',str(clip),'-frames:v','1','-vf','scale=240:426:force_original_aspect_ratio=increase,crop=240:426','-q:v','5',str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def contact_sheet(paths,out):
    cols=4
    rows=(len(paths)+cols-1)//cols
    sheet=Image.new('RGB',(cols*240,rows*426),(0,0,0))
    draw=ImageDraw.Draw(sheet)
    for i,p in enumerate(paths):
        with Image.open(p) as im:
            sheet.paste(im.convert('RGB').resize((240,426)),((i%cols)*240,(i//cols)*426))
        x=(i%cols)*240+7
        y=(i//cols)*426+7
        draw.rounded_rectangle((x,y,x+42,y+34),6,fill=(0,0,0))
        draw.text((x+11,y+7),str(i+1),fill=(255,255,255))
    sheet.save(out,quality=72,optimize=True)

def inspect(path,count):
    raw=base64.b64encode(path.read_bytes()).decode('ascii')
    prompt=f'''Esta grade contém {count} cenas numeradas de um vídeo bíblico evangélico.
Analise SOMENTE elementos visuais explícitos. Nunca infira religião, etnia, nacionalidade ou origem pela aparência das pessoas.
Marque uma cena apenas quando houver símbolo, ritual, objeto ou arquitetura religiosa explicitamente incompatível com a proposta do editor:
- devoção católica explícita, como rosário, imagem/estátua de Maria ou santos, papa, missa, ostensório ou crucifixo ornamental;
- contexto religioso islâmico explícito, como mesquita/minarete claramente identificável, Alcorão, oração ritual ou símbolo/caligrafia religiosa inequívoca;
- ritual, altar, entidade ou símbolo explicitamente ligado a religião afro-brasileira/de matriz africana, como terreiro, orixá ou ritual identificável.
Não marque cruz simples, paisagem, ruínas, roupa antiga do Oriente Médio, lenço/turbante genérico, pessoa negra, cultura africana comum ou instrumento comum sem marcador religioso explícito.
Responda SOMENTE JSON: {{"blocked_indices":[],"reasons":[]}}.'''
    body={'model':MODEL,'temperature':0,'max_completion_tokens':220,'response_format':{'type':'json_object'},'messages':[{'role':'user','content':[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':f'data:image/jpeg;base64,{raw}'}}]}]}
    for attempt in range(2):
        try:
            r=requests.post('https://api.groq.com/openai/v1/chat/completions',headers={'Authorization':f'Bearer {API_KEY}','Content-Type':'application/json'},json=body,timeout=90)
            if r.status_code in (429,500,502,503,504):
                time.sleep(2+attempt*3)
                continue
            if not r.ok:
                return None
            content=str(r.json().get('choices',[{}])[0].get('message',{}).get('content','{}'))
            data=json.loads(content)
            return [int(x) for x in data.get('blocked_indices',[]) if str(x).isdigit()]
        except Exception:
            time.sleep(2+attempt*2)
    return None

def main():
    plan=json.loads(os.getenv('INPUT_PLAN_JSON','{}'))
    niche=os.getenv('INPUT_NICHE_KEY','custom')
    text=' '.join(str(x) for x in [plan.get('title',''),plan.get('summary','')]+[s.get('narration','') for s in plan.get('scenes',[])]).lower()
    religious=niche in {'biblical','devotional'} or any(k in text for k in ['jesus','cristo','bíblia','deus','evangelho','batismo','oração','paulo','moisés','davi','daniel','noé','abraão','pentecost'])
    if not religious:
        print('Validação visual adicional não necessária.',flush=True)
        return
    if not API_KEY:
        print('Validação visual adicional indisponível; filtros preventivos mantidos.',flush=True)
        return
    clips=sorted(WORK.glob('scene_*.mp4'))
    if not clips:
        print('Validação visual adicional sem cenas para analisar.',flush=True)
        return
    frames=[]
    fd=WORK/'policy_frames'
    fd.mkdir(exist_ok=True)
    for i,c in enumerate(clips):
        p=fd/f'f{i}.jpg'
        frame(c,p)
        frames.append(p)
    sheet=fd/'contact.jpg'
    contact_sheet(frames,sheet)
    blocked=inspect(sheet,len(frames))
    if blocked is None:
        print('Validação visual adicional temporariamente indisponível; filtros preventivos mantidos.',flush=True)
        return
    if blocked:
        raise SystemExit('Geração interrompida: uma ou mais cenas não passaram pela política visual.')
    print(f'Política visual adicional aprovada em {len(frames)} cenas.',flush=True)

if __name__=='__main__':
    main()
