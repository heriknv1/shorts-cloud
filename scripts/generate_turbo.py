#!/usr/bin/env python3
import json, math, os, subprocess, hashlib, re, textwrap
from pathlib import Path
from urllib.parse import quote, quote_plus
import numpy as np
import requests
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]; WORK=ROOT/'work_turbo'; OUT=ROOT/'output'; WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
PIPER_MODEL=os.getenv('PIPER_MODEL_PATH','models/pt_BR-faber-medium.onnx'); PEXELS_API_KEY=os.getenv('PEXELS_API_KEY','')

RELIGIOUS_RX=re.compile(r'\b(jesus|christ|cristo|messiah|messias|bible|biblical|bíblia|bíblico|bíblica|god|deus|gospel|evangelho|baptism|batismo|prayer|oração|church|igreja|apostle|apóstolo|disciple|discípulo|noah|noé|abraham|abraão|moses|moisés|david|davi|samson|sansão|elijah|elias|daniel|jonah|jonas|paul|paulo|peter|pedro|pentecost|pentecostes|tessalonic|thessalonic)\b',re.I)
CATHOLIC_RX=re.compile(r'\b(catholic|católico|católica|catolicismo|cathedral|catedral|pope|papa|papal|rosary|terço|crucifix|crucifixo|statue|estátua|saint|santo|santa|virgin mary|virgem maria|madonna|marian|mariana|mass|missa|monstrance|ostensório|religious icon|ícone religioso|altar|basilica|basílica|chapel|capela|nun|freira|priest|padre)\b',re.I)
GENERIC_RELIGIOUS_STOCK_RX=re.compile(r'\b(jesus|christ|cristo|messiah|messias|bible|biblical|bíblia|bíblico|bíblica|gospel|evangelho|church|igreja|saint|holy|religious|religion|christian|cristão|cristã|devotional|scripture|faith|fé)\b',re.I)

def run(cmd,stdin=None):
    print('+',' '.join(map(str,cmd)),flush=True); kw={'check':True}
    if stdin is not None: kw['input']=stdin
    return subprocess.run(cmd,**kw)

def duration(path):
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True,check=True); return float(p.stdout.strip())

def voice_settings():
    pitch_mode=os.getenv('INPUT_VOICE_PITCH','default'); speed_mode=os.getenv('INPUT_VOICE_SPEED','default')
    pitch={'low':'-18Hz','default':'+0Hz','high':'+18Hz'}.get(pitch_mode,'+0Hz')
    rate={'slow':'-14%','default':'-5%','fast':'+10%'}.get(speed_mode,'-5%')
    return pitch_mode,speed_mode,pitch,rate

def postprocess_fallback_voice(src,dst):
    pitch_mode,speed_mode,_,_=voice_settings(); tempo={'slow':0.88,'default':1.0,'fast':1.12}.get(speed_mode,1.0); ratio={'low':0.92,'default':1.0,'high':1.08}.get(pitch_mode,1.0)
    filters=[]
    if abs(ratio-1.0)>.001: filters += [f'asetrate=48000*{ratio:.4f}', 'aresample=48000', f'atempo={1/ratio:.4f}']
    if abs(tempo-1.0)>.001: filters.append(f'atempo={tempo:.4f}')
    if filters: run(['ffmpeg','-y','-i',str(src),'-af',','.join(filters),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(dst)])
    else: run(['ffmpeg','-y','-i',str(src),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(dst)])

def synthesize(text,idx):
    wav=WORK/f'voice_{idx:02d}.wav'; raw=WORK/f'voice_raw_{idx:02d}.wav'; mp3=WORK/f'voice_{idx:02d}.mp3'; voice=os.getenv('INPUT_VOICE','pt-BR-AntonioNeural'); _,_,pitch,rate=voice_settings()
    try:
        run(['edge-tts','--voice',voice,f'--rate={rate}',f'--pitch={pitch}','--text',text,'--write-media',str(mp3)])
        if not mp3.exists() or mp3.stat().st_size<1000: raise RuntimeError('voz inválida')
        run(['ffmpeg','-y','-i',str(mp3),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(wav)])
        if duration(wav)<.3: raise RuntimeError('áudio curto demais')
        return wav,'edge-tts'
    except Exception as exc:
        print(f'Cena {idx+1}: voz principal indisponível ({exc}); usando alternativa.',flush=True)
        run(['piper','--model',PIPER_MODEL,'--output_file',str(raw)],stdin=text.encode('utf-8'))
        postprocess_fallback_voice(raw,wav)
        return wav,'voice-fallback'

def download(url,path):
    with requests.get(url,stream=True,timeout=120,headers={'User-Agent':'ShortCloudStudio/3.1'}) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for chunk in r.iter_content(1024*1024):
                if chunk: f.write(chunk)

def scene_is_religious(scene,niche):
    text=' '.join([str(scene.get('visual_description','')),str(scene.get('narration','')),str(scene.get('visual_query','')),str(scene.get('visual_query_backup',''))])
    return niche in {'biblical','devotional'} or bool(RELIGIOUS_RX.search(text))

def clean_query(q,religious=False):
    q=re.sub(r'\b(illustration|cartoon|drawing|animated|animation)\b',' ',str(q),flags=re.I)
    q=CATHOLIC_RX.sub(' ',q)
    if religious:
        q=GENERIC_RELIGIOUS_STOCK_RX.sub(' ',q)
        q=re.sub(r'\b(no|without|sem)\b',' ',q,flags=re.I)
    return ' '.join(q.split())[:220]

def safe_scene_queries(scene,niche):
    raw=[str(scene.get('visual_query','')),str(scene.get('visual_query_backup',''))]
    if not scene_is_religious(scene,niche):
        cleaned=[clean_query(q,False) for q in raw if clean_query(q,False)]
        return cleaned or ['cinematic documentary scene']
    text=(' '.join([str(scene.get('visual_description','')),str(scene.get('narration',''))])).lower()
    if any(k in text for k in ['office','escritório','trabalho','work','família','family','modern','moderno','sala de estar']):
        base='modern person at home or office natural window light calm authentic lifestyle'; backup='thoughtful person indoors natural daylight realistic everyday environment'
    elif any(k in text for k in ['tempestade','storm','barco','boat','mar','sea','lago','lake']):
        base='ancient Galilee wooden fishing boat storm lake people simple tunics historical reenactment'; backup='ancient middle east fishermen wooden boat rough water historical reenactment'
    elif any(k in text for k in ['batismo','baptism','jordão','jordan','rio','river']):
        base='Jordan river ancient middle east people simple tunics outdoor historical reenactment'; backup='ancient middle east riverbank people simple tunics historical reenactment'
    elif any(k in text for k in ['túmulo','tumulo','tomb','ressurrei','resurrect']):
        base='ancient Jerusalem rock tomb sunrise empty landscape historical reenactment'; backup='ancient stone tomb entrance sunrise middle east historical landscape'
    elif any(k in text for k in ['moisés','moses','deserto','desert','êxodo','exodus']):
        base='ancient middle east desert travelers simple tunics historical reenactment'; backup='desert caravan people simple ancient clothing historical reenactment'
    elif any(k in text for k in ['davi','david','golias','goliath']):
        base='ancient middle east shepherd warrior battlefield simple tunics historical reenactment'; backup='ancient valley shepherd and warrior historical reenactment middle east'
    elif any(k in text for k in ['daniel','leões','leoes','lions']):
        base='ancient stone courtyard lions historical reenactment middle east'; backup='ancient stone chamber lions historical reenactment'
    elif any(k in text for k in ['paulo','paul','tessalonic','thessalonic','grega','greek','pergaminho','scroll','carta','letter']):
        if any(k in text for k in ['pergaminho','scroll','carta','letter','mãos','hands']):
            base='hands holding ancient parchment scroll natural light historical reenactment'; backup='ancient parchment letter hands wooden table historical reenactment'
        else:
            base='ancient Greek city street people simple tunics historical reenactment'; backup='first century Mediterranean street people simple tunics historical reenactment'
    elif any(k in text for k in ['oração','orar','orando','prayer','praying']):
        base='person praying quietly at home natural window light simple room'; backup='hands folded in quiet reflection at home natural daylight'
    elif any(k in text for k in ['bíblia','bible','livro','book','palavra','scripture']):
        base='open old book on wooden table natural window light simple room'; backup='hands reading old book wooden table soft natural daylight'
    elif any(k in text for k in ['céu','sky','nuvens','clouds','luz','light','montanha','mountain']):
        base='dramatic clouds opening sunlight over mountain landscape cinematic nature'; backup='sun rays through storm clouds over empty landscape cinematic nature'
    elif any(k in text for k in ['jesus','cristo','christ','messias','messiah']):
        base='ancient Galilee village people simple tunics historical reenactment wide landscape'; backup='ancient middle east crowd simple tunics historical reenactment landscape'
    else:
        base='ancient middle east village people simple tunics historical reenactment'; backup='first century Mediterranean people simple tunics outdoor historical reenactment'
    return [base,backup]

def stock_result_allowed(text):
    return not CATHOLIC_RX.search(str(text or ''))

def pexels_photo(queries,used):
    if not PEXELS_API_KEY: return None,None,''
    for q in queries:
        q=clean_query(q,False)
        if not q: continue
        r=requests.get(f'https://api.pexels.com/v1/search?query={quote_plus(q)}&orientation=portrait&per_page=20',headers={'Authorization':PEXELS_API_KEY},timeout=45); r.raise_for_status()
        for p in r.json().get('photos',[]):
            if p.get('id') in used: continue
            if not stock_result_allowed(p.get('alt','')): continue
            src=p.get('src') or {}; link=src.get('portrait') or src.get('large2x') or src.get('large') or src.get('original')
            if link: used.add(p.get('id')); return p.get('id'),link,q
    return None,None,''

def pexels_video(queries,used):
    if not PEXELS_API_KEY: return None,None,''
    for q in queries:
        q=clean_query(q,False)
        if not q: continue
        r=requests.get(f'https://api.pexels.com/videos/search?query={quote_plus(q)}&orientation=portrait&per_page=20',headers={'Authorization':PEXELS_API_KEY},timeout=45); r.raise_for_status()
        for v in r.json().get('videos',[]):
            if v.get('id') in used: continue
            if not stock_result_allowed(v.get('url','')): continue
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
        x=190+n*(700//max(1,people-1)); giant=any(k in text for k in ['golias','gigante','giant']) and n==people-1; scale=1.45 if giant else 1; radius=int(62*scale); body=int(280*scale); y=1380-body-radius*2
        d.ellipse((x-radius,y,x+radius,y+radius*2),fill=c3,outline=(20,20,24),width=9); d.polygon([(x-120,y+radius*2),(x+120,y+radius*2),(x+65,1380),(x-65,1380)],fill=c1 if n%2 else c2,outline=(20,20,24)); d.line((x-35,1380,x-70,1530),fill=(20,20,24),width=18); d.line((x+35,1380,x+70,1530),fill=(20,20,24),width=18)
    im=im.filter(ImageFilter.SMOOTH_MORE); im.save(path,quality=94)

def ai_image(scene,path,style,niche,idx,realistic=False):
    desc=str(scene.get('visual_description') or scene.get('visual_query') or 'cinematic scene'); religious=scene_is_religious(scene,niche)
    if religious:
        desc=CATHOLIC_RX.sub(' ',desc)
        if re.search(r'\b(jesus|cristo|christ|messias|messiah)\b',desc+' '+str(scene.get('narration','')),re.I):
            desc=re.sub(r'\b(jesus|cristo|christ|messias|messiah)\b',' ',desc,flags=re.I); desc+=' ancient Galilee environment, people in simple tunics, wide indirect environmental composition'
    if realistic: style_text='photorealistic cinematic documentary still, natural skin, realistic lighting, authentic environment, vertical composition, no text, no watermark'
    else:
        style_text={'classic-2d':'high quality polished 2D animated film illustration, expressive characters, detailed environment, cinematic lighting, professional animation concept art','comic':'premium cinematic comic book illustration, detailed ink, dramatic lighting, strong composition','paper-cut':'high quality layered paper cutout illustration, sophisticated shapes, depth and handmade texture','retro-surreal':'polished retro surreal animation artwork, cinematic composition, detailed environment','interdimensional':'premium sci-fi surreal 2D animation artwork, vibrant lighting, detailed original characters'}.get(style,'high quality 2D animated film illustration'); style_text+=', no photo, no photorealism, no text, no watermark'
    if religious: style_text+=', simple first-century Middle Eastern or Mediterranean setting when historical, authentic simple tunics and sandals, scripture-centered evangelical Protestant visual language, unadorned setting, no ornate religious objects'
    prompt=f'{desc}. {style_text}'; seed=int(hashlib.sha256((prompt+str(idx)).encode()).hexdigest()[:8],16); url=f'https://image.pollinations.ai/prompt/{quote(prompt)}?width=768&height=1344&nologo=true&seed={seed}&enhance=true'
    try:
        r=requests.get(url,timeout=100,headers={'User-Agent':'ShortCloudStudio/3.1'}); r.raise_for_status()
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

def ass_ts(sec):
    cs=max(0,int(round(sec*100))); h,cs=divmod(cs,360000); m,cs=divmod(cs,6000); s,cs=divmod(cs,100); return f'{h}:{m:02d}:{s:02d}.{cs:02d}'

def ass_escape(text):
    return str(text).replace('\\',' ').replace('{','(').replace('}',')').replace('\r',' ').replace('\n',' ')

def make_ass(scenes,durations,path,font_name,font_size):
    font_size=max(36,min(92,int(font_size))); per=6 if font_size<=44 else 5 if font_size<=58 else 4 if font_size<=72 else 3; width=32 if font_size<=44 else 27 if font_size<=58 else 23 if font_size<=72 else 19; margin_v=140
    header=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H66000000,-1,0,0,0,100,100,0,0,1,4,1,2,72,72,{margin_v},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events=[]; offset=0.0
    for scene,dur in zip(scenes,durations):
        words=str(scene.get('narration','')).split(); chunks=[words[i:i+per] for i in range(0,len(words),per)] or [['']]; cursor=offset
        for ch in chunks:
            part=dur/max(1,len(chunks)); end=min(offset+dur,cursor+part); wrapped=textwrap.wrap(' '.join(ch),width=width,break_long_words=False,break_on_hyphens=False); caption=r'\N'.join(ass_escape(x) for x in wrapped[:2]); events.append(f'Dialogue: 0,{ass_ts(cursor)},{ass_ts(end)},Default,,0,0,0,,{caption}'); cursor=end
        offset+=dur
    path.write_text(header+'\n'.join(events)+'\n',encoding='utf-8')

def music_track(total,style,path):
    if style=='off': return None
    sr=48000; n=max(1,int(total*sr)); t=np.arange(n,dtype=np.float32)/sr
    cfg={'viral-pulse':{'bpm':108,'notes':[220.0,277.18,329.63,440.0],'bass':55.0,'pad':0.10,'beat':0.16},'cinematic-rise':{'bpm':74,'notes':[110.0,164.81,220.0,329.63],'bass':55.0,'pad':0.13,'beat':0.09},'mystery-tension':{'bpm':66,'notes':[110.0,116.54,164.81,174.61],'bass':55.0,'pad':0.11,'beat':0.06},'emotional-ambient':{'bpm':62,'notes':[130.81,164.81,196.0,261.63],'bass':65.41,'pad':0.12,'beat':0.035},'epic-ancient':{'bpm':82,'notes':[110.0,146.83,164.81,220.0],'bass':55.0,'pad':0.11,'beat':0.14}}.get(style,{'bpm':72,'notes':[110.0,146.83,220.0,293.66],'bass':55.0,'pad':0.10,'beat':0.08})
    audio=np.zeros(n,dtype=np.float32); segment=max(1,int(sr*60/cfg['bpm']*2))
    for pos in range(0,n,segment):
        note=cfg['notes'][(pos//segment)%len(cfg['notes'])]; end=min(n,pos+segment); tt=t[pos:end]; audio[pos:end]+=cfg['pad']*(0.55*np.sin(2*np.pi*note*tt)+0.30*np.sin(2*np.pi*(note*1.5)*tt)+0.15*np.sin(2*np.pi*(note*.5)*tt))
    audio += 0.035*np.sin(2*np.pi*cfg['bass']*t); beat=max(1,int(sr*60/cfg['bpm']))
    for start in range(0,n,beat):
        ln=min(int(.12*sr),n-start); env=np.linspace(1,0,ln,dtype=np.float32); audio[start:start+ln]+=cfg['beat']*np.sin(2*np.pi*52*np.arange(ln)/sr)*env
    fade=max(1,min(int(sr*1.5),n//4)); audio[:fade]*=np.linspace(0,1,fade,dtype=np.float32); audio[-fade:]*=np.linspace(1,0,fade,dtype=np.float32); peak=max(.001,float(np.max(np.abs(audio)))); audio=np.clip(audio/peak*.55,-.95,.95); sf.write(path,audio.astype(np.float32),sr); return path

def main():
    plan=json.loads(os.environ['INPUT_PLAN_JSON']); scenes=plan.get('scenes') or []
    if len(scenes)<6: raise RuntimeError('plano com poucas cenas')
    style=os.getenv('INPUT_CARTOON_STYLE','classic-2d'); niche=os.getenv('INPUT_NICHE_KEY','custom'); visual=os.getenv('INPUT_VISUAL_STYLE','realistic'); media_mode=os.getenv('INPUT_MEDIA_MODE','hybrid'); captions=os.getenv('INPUT_CAPTIONS','on'); music=os.getenv('INPUT_MUSIC','off'); voice=os.getenv('INPUT_VOICE','pt-BR-AntonioNeural'); pitch_mode=os.getenv('INPUT_VOICE_PITCH','default'); speed_mode=os.getenv('INPUT_VOICE_SPEED','default'); font_name=os.getenv('INPUT_CAPTION_FONT','Montserrat'); font_size=int(os.getenv('INPUT_CAPTION_SIZE','56')); volume={'low':'0.12','medium':'0.22','high':'0.34'}.get(os.getenv('INPUT_MUSIC_VOLUME','medium'),'0.22')
    font_name=re.sub(r"[^A-Za-z0-9 _-]",'',font_name)[:50] or 'Montserrat'; font_size=max(36,min(92,font_size)); voices=[]; clips=[]; durations=[]; sources=[]; engines=[]; used_photo=set(); used_video=set()
    for i,scene in enumerate(scenes):
        text=str(scene.get('narration') or '').strip()
        if not text: raise RuntimeError(f'cena {i+1} sem narração')
        wav,engine=synthesize(text,i); dur=duration(wav); voices.append(wav); durations.append(dur); engines.append(engine); clip=WORK/f'scene_{i:02d}.mp4'; queries=safe_scene_queries(scene,niche)
        if visual=='cartoon':
            img=WORK/f'illustration_{i:02d}.jpg'; source=ai_image(scene,img,style,niche,i,False); render_image(img,clip,dur,i); sources.append({'scene':i+1,'type':'animated-illustration' if media_mode!='photos' else 'illustration','source':source})
        else:
            requested='image' if media_mode=='photos' else 'video' if media_mode=='videos' else ('video' if scene.get('recommended_media')=='video' else 'image')
            if requested=='video':
                vid,url,q=pexels_video(queries,used_video)
                if url: src=WORK/f'real_{i:02d}.mp4'; download(url,src); render_video(src,clip,dur); sources.append({'scene':i+1,'type':'video','pexels_id':vid,'query':q})
                elif media_mode=='videos': raise RuntimeError(f'Não encontrei vídeo compatível para a cena {i+1}. Ajuste o roteiro ou use Fotos + vídeos.')
                else: requested='image'
            if requested=='image':
                pid,url,q=pexels_photo(queries,used_photo); img=WORK/f'real_{i:02d}.jpg'
                if url: download(url,img); source='photo-library'; sources.append({'scene':i+1,'type':'photo','source_id':pid,'query':q})
                else: source=ai_image(scene,img,style,niche,i,True); sources.append({'scene':i+1,'type':'photo-fallback','source':source})
                render_image(img,clip,dur,i)
        clips.append(clip)
    video=WORK/'video.mp4'; narration=WORK/'narration.wav'; concat(clips,'video',video); concat(voices,'audio',narration); total=duration(narration); ass=WORK/'captions.ass'; make_ass(scenes,durations,ass,font_name,font_size); bgm=music_track(total,music,WORK/'music.wav'); final=OUT/'final.mp4'; vf=[]
    if captions=='on': vf=['-vf',f'ass={ass}']
    if bgm: run(['ffmpeg','-y','-i',str(video),'-i',str(narration),'-i',str(bgm),'-filter_complex',f'[1:a]volume=1.0[v];[2:a]volume={volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,alimiter=limit=0.95[a]',*vf,'-map','0:v','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','22','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(final)])
    else: run(['ffmpeg','-y','-i',str(video),'-i',str(narration),*vf,'-map','0:v','-map','1:a','-c:v','libx264','-preset','veryfast','-crf','22','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(final)])
    meta={'title':plan.get('title') or os.getenv('INPUT_TOPIC','Short Cloud Studio'),'summary':plan.get('summary',''),'visual_style':visual,'cartoon_style':style if visual=='cartoon' else None,'media_mode':media_mode,'scene_sources':sources,'voice':voice,'voice_pitch':pitch_mode,'voice_speed':speed_mode,'voice_engine':'edge-tts' if all(x=='edge-tts' for x in engines) else 'edge-tts-with-fallback','captions':captions=='on','caption_font':font_name,'caption_size':font_size,'caption_position':'bottom','caption_margin_bottom':140,'music':music,'music_volume':os.getenv('INPUT_MUSIC_VOLUME','medium'),'duration_seconds':round(duration(final),2),'engine':'Short Cloud Studio'}; (OUT/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    if not final.exists() or final.stat().st_size<500000: raise RuntimeError('Vídeo final inválido')
    print(json.dumps(meta,ensure_ascii=False),flush=True)

if __name__=='__main__': main()
