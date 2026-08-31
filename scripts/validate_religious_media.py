#!/usr/bin/env python3
import base64,json,os,subprocess,time
from pathlib import Path
import requests
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]; WORK=ROOT/'work_turbo'; API_KEY=os.getenv('GROQ_API_KEY','').strip(); MODEL='qwen/qwen3.6-27b'
def duration(path):
 p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True,check=True);return max(.1,float(p.stdout.strip() or .1))
def frame(clip,out):
 at=max(.05,duration(clip)*.5);subprocess.run(['ffmpeg','-y','-ss',f'{at:.3f}','-i',str(clip),'-frames:v','1','-vf','scale=360:640:force_original_aspect_ratio=increase,crop=360:640','-q:v','4',str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def contact_sheet(paths,out):
 cols=3; rows=(len(paths)+cols-1)//cols; sheet=Image.new('RGB',(cols*360,rows*640),(0,0,0));draw=ImageDraw.Draw(sheet)
 for i,p in enumerate(paths):
  with Image.open(p) as im: sheet.paste(im.convert('RGB').resize((360,640)),((i%cols)*360,(i//cols)*640))
  x=(i%cols)*360+10;y=(i//cols)*640+10;draw.rounded_rectangle((x,y,x+58,y+48),8,fill=(0,0,0));draw.text((x+13,y+8),str(i+1),fill=(255,255,255))
 sheet.save(out,quality=80,optimize=True)
def inspect(path,count):
 raw=base64.b64encode(path.read_bytes()).decode('ascii');prompt=f'''Esta é uma grade com {count} cenas numeradas de um vídeo bíblico evangélico. Analise somente elementos VISÍVEIS explícitos; nunca infira religião, etnia ou origem pelas pessoas. Bloqueie uma cena somente se mostrar claramente: iconografia/ritual católico (rosário, Maria/santos em devoção, papa, missa, ostensório, crucifixo ornamental); contexto religioso islâmico explícito (mesquita/minarete, Alcorão, oração ritual, caligrafia/símbolo religioso inequívoco); ou ritual/altar/entidade/símbolo explicitamente ligado a religião afro-brasileira/de matriz africana (terreiro, orixá, ritual identificável). Não bloqueie cruz simples, paisagem, ruínas, roupas antigas do Oriente Médio, lenços/turbantes genéricos, pessoas negras, cultura africana comum ou instrumentos comuns sem marcador religioso explícito. Retorne SOMENTE JSON: {{"blocked_indices":[],"reasons":[]}}.'''
 body={'model':MODEL,'temperature':0,'max_completion_tokens':220,'response_format':{'type':'json_object'},'messages':[{'role':'user','content':[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':f'data:image/jpeg;base64,{raw}'}}]}]}
 last=None
 for n in range(3):
  try:
   r=requests.post('https://api.groq.com/openai/v1/chat/completions',headers={'Authorization':f'Bearer {API_KEY}','Content-Type':'application/json'},json=body,timeout=90)
   if r.status_code==429:time.sleep(3+n*3);continue
   r.raise_for_status();data=json.loads(str(r.json().get('choices',[{}])[0].get('message',{}).get('content','{}')));return [int(x) for x in data.get('blocked_indices',[]) if str(x).isdigit()]
  except Exception as e:last=e;time.sleep(2+n*2)
 raise RuntimeError(f'Validação visual indisponível: {last}')
def main():
 plan=json.loads(os.getenv('INPUT_PLAN_JSON','{}'));niche=os.getenv('INPUT_NICHE_KEY','custom');text=' '.join(str(x) for x in [plan.get('title',''),plan.get('summary','')]+[s.get('narration','') for s in plan.get('scenes',[])])
 religious=niche in {'biblical','devotional'} or any(k in text.lower() for k in ['jesus','cristo','bíblia','deus','evangelho','batismo','oração','paulo','moisés','davi','daniel','noé','abraão','pentecost'])
 if not religious:print('Validação religiosa visual não necessária.',flush=True);return
 if not API_KEY:raise SystemExit('Validação visual religiosa obrigatória indisponível.')
 clips=sorted(WORK.glob('scene_*.mp4'));frames=[];fd=WORK/'policy_frames';fd.mkdir(exist_ok=True)
 for i,c in enumerate(clips):p=fd/f'f{i}.jpg';frame(c,p);frames.append(p)
 sheet=fd/'contact.jpg';contact_sheet(frames,sheet);blocked=inspect(sheet,len(frames))
 if blocked:raise SystemExit('Geração interrompida: mídia religiosa incompatível detectada nas cenas '+', '.join(map(str,sorted(set(blocked)))))
 print(f'Política visual validada em {len(frames)} cenas.',flush=True)
if __name__=='__main__':main()
