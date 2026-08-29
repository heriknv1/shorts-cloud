#!/usr/bin/env python3
import json, math, os, subprocess, hashlib, re
from pathlib import Path
from urllib.parse import quote, quote_plus
import numpy as np
import requests
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]; WORK=ROOT/'work_turbo'; OUT=ROOT/'output'; WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
PIPER_MODEL=os.getenv('PIPER_MODEL_PATH','models/pt_BR-faber-medium.onnx'); PEXELS_API_KEY=os.getenv('PEXELS_API_KEY','')

def run(cmd,stdin=None):
    print('+',' '.join(map(str,cmd)),flush=True); kw={'check':True}
    if stdin is not None: kw['input']=stdin
    return subprocess.run(cmd,**kw)

def duration(path):
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True,check=True); return float(p.stdout.strip())

def synthesize(text,idx):
    wav=WORK/f'voice_{idx:02d}.wav'; mp3=WORK/f'voice_{idx:02d}.mp3'; voice=os.getenv('INPUT_VOICE','pt-BR-AntonioNeural'); rate=os.getenv('EDGE_TTS_RATE','-5%')
    try:
        run(['edge-tts','--voice',voice,f'--rate={rate}','--text',text,'--write-media',str(mp3)])
        if not mp3.exists() or mp3.stat().st_size<1000: raise RuntimeError('Edge TTS não gerou mídia válida')
        run(['ffmpeg','-y','-i',str(mp3),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(wav)])
        if duration(wav)<.3: raise RuntimeError('áudio curto demais')
        return wav,'edge-tts'
    except Exception as exc:
        print(f'Cena {idx+1}: Edge TTS falhou ({exc}); usando Piper.',flush=True)
        run(['piper','--model',PIPER_MODEL,'--output_file',str(wav)],stdin=text.encode('utf-8'))
        return wav,'piper-fallback'

def download(url,path):
    with requests.get(url,stream=True,timeout=120,headers={'User-Agent':'ShortCloudStudio/3.0'}) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for chunk in r.iter_content(1024*1024):
                if chunk: f.write(chunk)

def clean_query(q):
    q=re.sub(r'\b(illustration|cartoon|drawing|animated|animation)\b',' ',str(q),flags=re.I)
    return ' '.join(q.split())[:220]

def pexels_photo(queries,used):
    if not PEXELS_API_KEY: return None,None,''
    for q in queries:
        q=clean_query(q)
        if not q: continue
        r=requests.get(f'https://api.pexels.com/v1/search?query={quote_plus(q)}&orientation=portrait&per_page=20',headers={'Authorization':PEXELS_API_KEY},timeout=45); r.raise_for_status()
        for p in r.json().get('photos',[]):
            if p.get('id') in used: continue
            src=p.get('src') or {}; link=src.get('portrait') or src.get('large2x') or src.get('large') or src.get('original')
            if link: used.add(p.get('id')); return p.get('id'),link,q
    return None,None,''

def pexels_video(queries,used):
    if not PEXELS_API_KEY: return None,None,''
    for q in queries:
        q=clean_query(q)
        if not q: continue
        r=requests.get(f'https://api.pexels.com/videos/search?query={quote_plus(q)}&orientation=portrait&per_page=20',headers={'Authorization':PEXELS_API_KEY},timeout=45); r.raise_for_status()
        for v in r.json().get('videos',[]):
            if v.get('id') in used: continue
            files=[x for x in v.get('video_files',[]) if x.get('link') and x.get('width') and x.get('height')]
            files.sort(key=lambda x:(0 if x['height']>=x['width'] else 1,abs((x.get('width') or 0)-1080)))
            if files: used.add(v.get('id')); return v.get('id'),files[0]['link'],q
    return None,None,''

def palette(style,niche):
    p={'classic-2d':((24,30,48),(236,170,82),(70,111,167),(244,221,175)),'comic':((14,18,30),(211,70,64),(230,177,67),(58,73,117)),'paper-cut':((36,45,67),(235,107,78),(241,193,82),(94,163,139)),'retro-surreal':((52,41,63),(219,126,105),(224,189,124),(80,126,137)),'interdimensional':((20,18,48),(162,86,225),(59,211,181),(240,177,72))}
    if niche in {'biblical','devotional'}: return ((74,48,31),(225,161,80),(104,78,55),(245,218,166))
    if niche=='science': return ((7,20,42),(39,106,172),(55,203,199),(194,225,255))
    return p.get(style,p['classic-2d'])

def font(size):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def procedural_scene(scene,path,style,niche,idx):
    W,H=1080,1920; c0,c1,c2,c3=palette(style,niche); im=Image.new('RGB',(W,H),c0); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,760),fill=c0); d.ellipse((720,120,990,390),fill=c1); d.polygon([(0,850),(300,560),(560,830),(820,510),(1080,780),(1080,1400),(0,1400)],fill=c2); d.rectangle((0,1390,W,H),fill=c0)
    text=(str(scene.get('visual_description',''))+' '+str(scene.get('narration',''))).lower(); people=4 if any(k in text for k in ['army','exército','soldados','multidão']) else 2
    for n in range(people):
        x=190+n*(700//max(1,people-1)); giant=any(k in text for k in ['golias','gigante','giant']) and n==people-1; s=1.45 if giant else 1; r=int(62*s); bh=int(280*s); y=1380-bh-r*2
        d.ellipse((x-r,y,x+r,y+r*2),fill=c3,outline=(20,20,24),width=9); d.polygon([(x-120,y+r*2),(x+120,y+r*2),(x+65,1380),(x-65,1380)],fill=c1 if n%2 else c2,outline=(20,20,24)); d.line((x-35,1380,x-70,1530),fill=(20,20,24),width=18); d.line((x+35,1380,x+70,1530),fill=(20,20,24),width=18)
    im=im.filter(ImageFilter.SMOOTH_MORE); im.save(path,quality=94)

def ai_image(scene,path,style,niche,idx,realistic=False):
    desc=str(scene.get('visual_description') or scene.get('visual_query') or 'cinematic scene')
    if realistic:
        style_text='photorealistic cinematic documentary still, natural skin, realistic lighting, authentic environment, vertical composition, no text, no watermark'
    else:
        style_text={'classic-2d':'high quality polished 2D animated film illustration, expressive characters, detailed environment, cinematic lighting, professional animation concept art','comic':'premium cinematic comic book illustration, detailed ink, dramatic lighting, strong composition','paper-cut':'high quality layered paper cutout illustration, sophisticated shapes, depth and handmade texture','retro-surreal':'polished retro surreal animation artwork, cinematic composition, detailed environment','interdimensional':'premium sci-fi surreal 2D animation artwork, vibrant lighting, detailed original characters'}.get(style,'high quality 2D animated film illustration')
        style_text+=', no photo, no photorealism, no text, no watermark'
    if niche in {'biblical','devotional'}: style_text+=', ancient biblical Middle East when historical, authentic tunics and sandals, no modern objects, no medieval European armor'
    prompt=f'{desc}. {style_text}'; seed=int(hashlib.sha256((prompt+str(idx)).encode()).hexdigest()[:8],16); url=f'https://image.pollinations.ai/prompt/{quote(prompt)}?width=768&height=1344&nologo=true&seed={seed}&enhance=true'
    try:
        r=requests.get(url,timeout=100,headers={'User-Agent':'ShortCloudStudio/3.0'}); r.raise_for_status()
        if len(r.content)<20000: raise RuntimeError('imagem remota pequena')
        tmp=path.with_suffix('.download'); tmp.write_bytes(r.content)
        with Image.open(tmp) as im: im.convert('RGB').resize((1080,1920),Image.Resampling.LANCZOS).save(path,quality=94)
        tmp.unlink(missing_ok=True); return 'ai-realistic' if realistic else 'ai-illustration'
    except Exception as exc:
        print(f'Cena {idx+1}: geração visual remota falhou ({exc}).',flush=True)
        if realistic:
            im=Image.new('RGB',(1080,1920),(35,40,48)); im.save(path,quality=92); return 'neutral-fallback'
        procedural_scene(scene,path,style,niche,idx); return 'vector-fallback'

def render_image(img,out,seconds,idx):
    frames=max(1,int(math.ceil(seconds*30))); z="min(zoom+0.0008,1.10)" if idx%2 else '1.08'; x="iw/2-(iw/zoom/2)" if idx%2 else f'(iw-iw/zoom)*on/{frames}'; y='ih/2-(ih/zoom/2)'; vf=f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps=30,format=yuv420p"
    run(['ffmpeg','-y','-loop','1','-i',str(img),'-t',f'{seconds:.3f}','-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p',str(out)])

def render_video(src,out,seconds):
    vf='scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p'; run(['ffmpeg','-y','-stream_loop','-1','-i',str(src),'-t',f'{seconds:.3f}','-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p',str(out)])

def concat(files,kind,out):
    m=WORK/f'concat_{kind}.txt'; m.write_text('\n'.join(f"file '{p.resolve()}'" for p in files),encoding='utf-8')
    if kind=='video': run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(m),'-c','copy',str(out)])
    else: run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(m),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(out)])

def ts(sec):
    ms=int(round(sec*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000); return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def make_srt(scenes,durations,path):
    lines=[]; offset=0.; n=1
    for scene,dur in zip(scenes,durations):
        words=str(scene.get('narration','')).split(); chunks=[words[i:i+6] for i in range(0,len(words),6)] or [['']]; cursor=offset
        for ch in chunks:
            part=dur/max(1,len(chunks)); end=min(offset+dur,cursor+part); lines += [str(n),f'{ts(cursor)} --> {ts(end)}',' '.join(ch),'']; n+=1; cursor=end
        offset+=dur
    path.write_text('\n'.join(lines),encoding='utf-8')

def music_track(total,style,path):
    if style=='off': return None
    sr=48000; n=int(total*sr); t=np.arange(n,dtype=np.float32)/sr; configs={'viral-pulse':(104,220.),'cinematic-rise':(76,146.8),'mystery-tension':(68,110.),'emotional-ambient':(64,174.6),'epic-ancient':(82,130.8)}; bpm,freq=configs.get(style,(72,146.8)); audio=.08*np.sin(2*np.pi*freq*t)+.035*np.sin(2*np.pi*freq*1.5*t); beat=max(1,int(sr*60/bpm))
    for start in range(0,n,beat):
        ln=min(int(.11*sr),n-start); env=np.linspace(1,0,ln,dtype=np.float32); audio[start:start+ln]+=.13*np.sin(2*np.pi*55*np.arange(ln)/sr)*env
    sf.write(path,np.tanh(audio*1.4).astype(np.float32),sr); return path

def main():
    plan=json.loads(os.environ['INPUT_PLAN_JSON']); scenes=plan.get('scenes') or []
    if len(scenes)<6: raise RuntimeError('plano com poucas cenas')
    style=os.getenv('INPUT_CARTOON_STYLE','classic-2d'); niche=os.getenv('INPUT_NICHE_KEY','custom'); visual=os.getenv('INPUT_VISUAL_STYLE','realistic'); media_mode=os.getenv('INPUT_MEDIA_MODE','hybrid'); captions=os.getenv('INPUT_CAPTIONS','on'); music=os.getenv('INPUT_MUSIC','off'); voice=os.getenv('INPUT_VOICE','pt-BR-AntonioNeural'); font_name=os.getenv('INPUT_CAPTION_FONT','DejaVu Sans'); font_size=int(os.getenv('INPUT_CAPTION_SIZE','38')); volume={'low':'0.08','medium':'0.13','high':'0.18'}.get(os.getenv('INPUT_MUSIC_VOLUME','medium'),'0.13')
    font_name=re.sub(r"[^A-Za-z0-9 _-]",'',font_name)[:50] or 'DejaVu Sans'; font_size=max(24,min(64,font_size)); voices=[]; clips=[]; durations=[]; sources=[]; engines=[]; used_photo=set(); used_video=set()
    for i,scene in enumerate(scenes):
        text=str(scene.get('narration') or '').strip()
        if not text: raise RuntimeError(f'cena {i+1} sem narração')
        wav,engine=synthesize(text,i); dur=duration(wav); voices.append(wav); durations.append(dur); engines.append(engine); clip=WORK/f'scene_{i:02d}.mp4'; queries=[scene.get('visual_query',''),scene.get('visual_query_backup','')]
        if visual=='cartoon':
            img=WORK/f'illustration_{i:02d}.jpg'; source=ai_image(scene,img,style,niche,i,False); render_image(img,clip,dur,i); sources.append({'scene':i+1,'type':'animated-illustration' if media_mode!='photos' else 'illustration','source':source})
        else:
            requested='image' if media_mode=='photos' else 'video' if media_mode=='videos' else ('video' if scene.get('recommended_media')=='video' else 'image')
            if requested=='video':
                vid,url,q=pexels_video(queries,used_video)
                if url:
                    src=WORK/f'real_{i:02d}.mp4'; download(url,src); render_video(src,clip,dur); sources.append({'scene':i+1,'type':'video','pexels_id':vid,'query':q})
                elif media_mode=='videos':
                    raise RuntimeError(f'Não encontrei vídeo real compatível para a cena {i+1}. Ajuste o roteiro ou use Fotos + vídeos.')
                else: requested='image'
            if requested=='image':
                pid,url,q=pexels_photo(queries,used_photo); img=WORK/f'real_{i:02d}.jpg'
                if url: download(url,img); source='pexels-photo'; sources.append({'scene':i+1,'type':'photo','pexels_id':pid,'query':q})
                else: source=ai_image(scene,img,style,niche,i,True); sources.append({'scene':i+1,'type':'photo-fallback','source':source})
                render_image(img,clip,dur,i)
        clips.append(clip)
    video=WORK/'video.mp4'; narration=WORK/'narration.wav'; concat(clips,'video',video); concat(voices,'audio',narration); total=duration(narration); srt=WORK/'captions.srt'; make_srt(scenes,durations,srt); bgm=music_track(total,music,WORK/'music.wav'); final=OUT/'final.mp4'; vf=[]
    if captions=='on': vf=['-vf',f"subtitles={srt}:force_style='FontName={font_name},FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=110,Bold=1'"]
    if bgm: run(['ffmpeg','-y','-i',str(video),'-i',str(narration),'-i',str(bgm),'-filter_complex',f'[1:a]volume=1.0[v];[2:a]volume={volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]',*vf,'-map','0:v','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','22','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(final)])
    else: run(['ffmpeg','-y','-i',str(video),'-i',str(narration),*vf,'-map','0:v','-map','1:a','-c:v','libx264','-preset','veryfast','-crf','22','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(final)])
    meta={'title':plan.get('title') or os.getenv('INPUT_TOPIC','Short Cloud Studio'),'summary':plan.get('summary',''),'visual_style':visual,'cartoon_style':style if visual=='cartoon' else None,'media_mode':media_mode,'scene_sources':sources,'voice':voice,'voice_engine':'edge-tts' if all(x=='edge-tts' for x in engines) else 'edge-tts-with-piper-fallback','captions':captions=='on','caption_font':font_name,'caption_size':font_size,'duration_seconds':round(duration(final),2),'engine':'Short Cloud Studio unified renderer'}; (OUT/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    if not final.exists() or final.stat().st_size<500000: raise RuntimeError('MP4 final inválido')
    print(json.dumps(meta,ensure_ascii=False),flush=True)

if __name__=='__main__': main()
