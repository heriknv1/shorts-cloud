#!/usr/bin/env python3
import json
import math
import os
import re
import subprocess
import textwrap
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import requests
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from visual_engine import BLOCKED_RX, generate_scene_image, scene_is_religious, stock_queries

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work_turbo'
OUT=ROOT/'output'
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

PIPER_MODEL=os.getenv('PIPER_MODEL_PATH','models/pt_BR-faber-medium.onnx')
PEXELS_API_KEY=os.getenv('PEXELS_API_KEY','').strip()

def run(cmd,stdin=None,quiet=False):
    if not quiet:
        print('+',' '.join(map(str,cmd)),flush=True)
    kw={'check':True}
    if stdin is not None:
        kw['input']=stdin
    if quiet:
        kw.update(stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return subprocess.run(cmd,**kw)

def duration(path):
    p=subprocess.run(
        ['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],
        capture_output=True,text=True,check=True
    )
    return float(p.stdout.strip())

def voice_settings():
    pitch_mode=os.getenv('INPUT_VOICE_PITCH','default')
    speed_mode=os.getenv('INPUT_VOICE_SPEED','default')
    pitch={'low':'-7Hz','default':'+0Hz','high':'+7Hz'}.get(pitch_mode,'+0Hz')
    rate={'slow':'-8%','default':'+0%','fast':'+7%'}.get(speed_mode,'+0%')
    return pitch_mode,speed_mode,pitch,rate

def naturalize_speech_text(text):
    text=str(text or '').strip()
    text=text.replace('—',', ').replace('–',', ')
    text=re.sub(r'\s*;\s*',', ',text)
    text=re.sub(r'\s*:\s*',': ',text)
    text=re.sub(r'\s+',' ',text)
    if text and text[-1] not in '.!?':
        text+='.'
    return text

def polish_voice(src,dst):
    filters='highpass=f=70,lowpass=f=12500,acompressor=threshold=-18dB:ratio=1.7:attack=25:release=220:makeup=1.25,alimiter=limit=0.94'
    run(['ffmpeg','-y','-i',str(src),'-af',filters,'-ar','48000','-ac','1','-c:a','pcm_s16le',str(dst)],quiet=True)

def postprocess_fallback_voice(src,dst):
    pitch_mode,speed_mode,_,_=voice_settings()
    tempo={'slow':0.93,'default':1.0,'fast':1.07}.get(speed_mode,1.0)
    ratio={'low':0.965,'default':1.0,'high':1.035}.get(pitch_mode,1.0)
    filters=[]
    if abs(ratio-1.0)>.001:
        filters += [f'asetrate=48000*{ratio:.4f}','aresample=48000',f'atempo={1/ratio:.4f}']
    if abs(tempo-1.0)>.001:
        filters.append(f'atempo={tempo:.4f}')
    filters += ['highpass=f=70','lowpass=f=12000','acompressor=threshold=-18dB:ratio=1.6:attack=25:release=220','alimiter=limit=0.94']
    run(['ffmpeg','-y','-i',str(src),'-af',','.join(filters),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(dst)],quiet=True)

def synthesize(text,idx):
    voice=os.getenv('INPUT_VOICE','pt-BR-FranciscaNeural')
    _,_,pitch,rate=voice_settings()
    spoken=naturalize_speech_text(text)
    mp3=WORK/f'voice_{idx:02d}.mp3'
    rawwav=WORK/f'voice_unpolished_{idx:02d}.wav'
    wav=WORK/f'voice_{idx:02d}.wav'
    piper_raw=WORK/f'voice_piper_{idx:02d}.wav'
    try:
        run(['edge-tts','--voice',voice,f'--rate={rate}',f'--pitch={pitch}','--text',spoken,'--write-media',str(mp3)])
        if not mp3.exists() or mp3.stat().st_size<1000:
            raise RuntimeError('voz principal inválida')
        run(['ffmpeg','-y','-i',str(mp3),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(rawwav)],quiet=True)
        polish_voice(rawwav,wav)
        if duration(wav)<.3:
            raise RuntimeError('áudio curto demais')
        return wav,'neural'
    except Exception as exc:
        print(f'Cena {idx+1}: voz principal indisponível; usando alternativa.',flush=True)
        run(['piper','--model',PIPER_MODEL,'--output_file',str(piper_raw)],stdin=spoken.encode('utf-8'))
        postprocess_fallback_voice(piper_raw,wav)
        return wav,'voice-fallback'

def download(url,path):
    with requests.get(url,stream=True,timeout=120,headers={'User-Agent':'ShortCloudStudio/4.0'}) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for chunk in r.iter_content(1024*1024):
                if chunk:
                    f.write(chunk)

def stock_result_allowed(text):
    return not BLOCKED_RX.search(str(text or ''))

def pexels_photo(queries,used):
    if not PEXELS_API_KEY:
        return None,None,''
    for q in queries:
        q=' '.join(str(q).split())[:200]
        if not q:
            continue
        try:
            r=requests.get(
                f'https://api.pexels.com/v1/search?query={quote_plus(q)}&orientation=portrait&per_page=30',
                headers={'Authorization':PEXELS_API_KEY},timeout=45
            )
            r.raise_for_status()
        except Exception:
            continue
        for p in r.json().get('photos',[]):
            if p.get('id') in used:
                continue
            if not stock_result_allowed(p.get('alt','')):
                continue
            width=int(p.get('width') or 0); height=int(p.get('height') or 0)
            if height<width or width<1080 or height<1920:
                continue
            src=p.get('src') or {}
            link=src.get('original') or src.get('large2x')
            if link:
                used.add(p.get('id'))
                return p.get('id'),link,q
    return None,None,''

def pexels_video(queries,used):
    if not PEXELS_API_KEY:
        return None,None,''
    for q in queries:
        q=' '.join(str(q).split())[:200]
        if not q:
            continue
        try:
            r=requests.get(
                f'https://api.pexels.com/videos/search?query={quote_plus(q)}&orientation=portrait&per_page=30',
                headers={'Authorization':PEXELS_API_KEY},timeout=45
            )
            r.raise_for_status()
        except Exception:
            continue
        for v in r.json().get('videos',[]):
            if v.get('id') in used:
                continue
            if not stock_result_allowed(v.get('url','')):
                continue
            files=[x for x in v.get('video_files',[]) if x.get('link') and x.get('width') and x.get('height') and int(x['height'])>=int(x['width']) and int(x['width'])>=1080 and int(x['height'])>=1920]
            files.sort(key=lambda x:(0 if x['height']>=x['width'] else 1,abs((x.get('width') or 0)-1080),-int(x.get('height') or 0)))
            if files:
                used.add(v.get('id'))
                return v.get('id'),files[0]['link'],q
    return None,None,''

def palette(style,niche):
    p={
        'classic-2d':((24,30,48),(236,170,82),(70,111,167),(244,221,175)),
        'comic':((14,18,30),(211,70,64),(230,177,67),(58,73,117)),
        'paper-cut':((36,45,67),(235,107,78),(241,193,82),(94,163,139)),
        'retro-surreal':((52,41,63),(219,126,105),(224,189,124),(80,126,137)),
        'interdimensional':((20,18,48),(162,86,225),(59,211,181),(240,177,72)),
    }
    if niche in {'biblical','devotional'}:
        return ((74,48,31),(225,161,80),(104,78,55),(245,218,166))
    if niche=='science':
        return ((7,20,42),(39,106,172),(55,203,199),(194,225,255))
    return p.get(style,p['classic-2d'])

def procedural_scene(scene,path,style,niche,idx):
    W,H=1080,1920
    c0,c1,c2,c3=palette(style,niche)
    im=Image.new('RGB',(W,H),c0)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,760),fill=c0)
    d.ellipse((720,120,990,390),fill=c1)
    d.polygon([(0,850),(300,560),(560,830),(820,510),(1080,780),(1080,1400),(0,1400)],fill=c2)
    d.rectangle((0,1390,W,H),fill=c0)
    text=(str(scene.get('visual_description',''))+' '+str(scene.get('narration',''))).lower()
    people=4 if any(k in text for k in ['army','exército','soldados','multidão']) else 2
    for n in range(people):
        x=190+n*(700//max(1,people-1))
        giant=any(k in text for k in ['golias','gigante','goliath','giant']) and n==people-1
        scale=1.45 if giant else 1
        radius=int(62*scale)
        body=int(280*scale)
        y=1380-body-radius*2
        d.ellipse((x-radius,y,x+radius,y+radius*2),fill=c3,outline=(20,20,24),width=9)
        d.polygon([(x-120,y+radius*2),(x+120,y+radius*2),(x+65,1380),(x-65,1380)],fill=c1 if n%2 else c2,outline=(20,20,24))
        d.line((x-35,1380,x-70,1530),fill=(20,20,24),width=18)
        d.line((x+35,1380,x+70,1530),fill=(20,20,24),width=18)
    im=im.filter(ImageFilter.SMOOTH_MORE)
    im.save(path,quality=94)

def render_image(img,out,seconds,idx):
    frames=max(1,int(math.ceil(seconds*30)))
    mode=idx%4
    if mode==0:
        z='min(zoom+0.00065,1.09)'; x='iw/2-(iw/zoom/2)'; y='ih/2-(ih/zoom/2)'
    elif mode==1:
        z='1.075'; x=f'(iw-iw/zoom)*on/{frames}'; y='ih/2-(ih/zoom/2)'
    elif mode==2:
        z='1.075'; x=f'(iw-iw/zoom)*(1-on/{frames})'; y='ih/2-(ih/zoom/2)'
    else:
        z='min(zoom+0.00045,1.07)'; x='iw/2-(iw/zoom/2)'; y=f'(ih-ih/zoom)*on/{frames}'
    vf=f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps=30,format=yuv420p"
    run(['ffmpeg','-y','-loop','1','-i',str(img),'-t',f'{seconds:.3f}','-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p',str(out)],quiet=True)

def render_video(src,out,seconds):
    vf='scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p'
    run(['ffmpeg','-y','-stream_loop','-1','-i',str(src),'-t',f'{seconds:.3f}','-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p',str(out)],quiet=True)

def concat(files,kind,out):
    manifest=WORK/f'concat_{kind}.txt'
    manifest.write_text('\n'.join(f"file '{p.resolve()}'" for p in files),encoding='utf-8')
    if kind=='video':
        run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(manifest),'-c','copy',str(out)],quiet=True)
    else:
        run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(manifest),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(out)],quiet=True)

def ass_ts(sec):
    cs=max(0,int(round(sec*100)))
    h,cs=divmod(cs,360000)
    m,cs=divmod(cs,6000)
    s,cs=divmod(cs,100)
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'

def ass_escape(text):
    return str(text).replace('\\',' ').replace('{','(').replace('}',')').replace('\r',' ').replace('\n',' ')

def make_ass(scenes,durations,path,font_name,font_size):
    font_size=max(36,min(92,int(font_size)))
    per=6 if font_size<=44 else 5 if font_size<=58 else 4 if font_size<=72 else 3
    width=32 if font_size<=44 else 27 if font_size<=58 else 23 if font_size<=72 else 19
    margin_v=140
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
    events=[]
    offset=0.0
    for scene,dur in zip(scenes,durations):
        words=str(scene.get('narration','')).split()
        chunks=[words[i:i+per] for i in range(0,len(words),per)] or [['']]
        cursor=offset
        for ch in chunks:
            part=dur/max(1,len(chunks))
            end=min(offset+dur,cursor+part)
            wrapped=textwrap.wrap(' '.join(ch),width=width,break_long_words=False,break_on_hyphens=False)
            caption=r'\N'.join(ass_escape(x) for x in wrapped[:2])
            events.append(f'Dialogue: 0,{ass_ts(cursor)},{ass_ts(end)},Default,,0,0,0,,{caption}')
            cursor=end
        offset+=dur
    path.write_text(header+'\n'.join(events)+'\n',encoding='utf-8')

def music_track(total,style,path):
    if style=='off':
        return None
    sr=48000
    n=max(1,int(total*sr))
    t=np.arange(n,dtype=np.float32)/sr
    cfg={
        'viral-pulse':{'bpm':108,'notes':[220.0,277.18,329.63,440.0],'bass':55.0,'pad':0.10,'beat':0.16},
        'cinematic-rise':{'bpm':74,'notes':[110.0,164.81,220.0,329.63],'bass':55.0,'pad':0.13,'beat':0.09},
        'mystery-tension':{'bpm':66,'notes':[110.0,116.54,164.81,174.61],'bass':55.0,'pad':0.11,'beat':0.06},
        'emotional-ambient':{'bpm':62,'notes':[130.81,164.81,196.0,261.63],'bass':65.41,'pad':0.12,'beat':0.035},
        'epic-ancient':{'bpm':82,'notes':[110.0,146.83,164.81,220.0],'bass':55.0,'pad':0.11,'beat':0.14},
    }.get(style,{'bpm':72,'notes':[110.0,146.83,220.0,293.66],'bass':55.0,'pad':0.10,'beat':0.08})
    audio=np.zeros(n,dtype=np.float32)
    segment=max(1,int(sr*60/cfg['bpm']*2))
    for pos in range(0,n,segment):
        note=cfg['notes'][(pos//segment)%len(cfg['notes'])]
        end=min(n,pos+segment)
        tt=t[pos:end]
        audio[pos:end]+=cfg['pad']*(0.55*np.sin(2*np.pi*note*tt)+0.30*np.sin(2*np.pi*(note*1.5)*tt)+0.15*np.sin(2*np.pi*(note*.5)*tt))
    audio += 0.035*np.sin(2*np.pi*cfg['bass']*t)
    beat=max(1,int(sr*60/cfg['bpm']))
    for start in range(0,n,beat):
        ln=min(int(.12*sr),n-start)
        env=np.linspace(1,0,ln,dtype=np.float32)
        audio[start:start+ln]+=cfg['beat']*np.sin(2*np.pi*52*np.arange(ln)/sr)*env
    fade=max(1,min(int(sr*1.5),n//4))
    audio[:fade]*=np.linspace(0,1,fade,dtype=np.float32)
    audio[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)
    peak=max(.001,float(np.max(np.abs(audio))))
    audio=np.clip(audio/peak*.55,-.95,.95)
    sf.write(path,audio.astype(np.float32),sr)
    return path

def choose_image(scene,idx,style,niche,visual_context,realistic,reference,used_photo):
    img=WORK/f'generated_{idx:02d}.jpg'
    source=generate_scene_image(scene,img,visual_context,style,niche,idx,realistic,reference)
    if source and img.exists() and img.stat().st_size>20000:
        return img,source
    if niche=='analog-horror':
        procedural_scene(scene,img,'retro-surreal',niche,idx)
        return img,'analog-procedural-fallback'
    queries=stock_queries(scene,niche)
    pid,url,q=pexels_photo(queries,used_photo)
    if url:
        try:
            download(url,img)
            with Image.open(img) as im:
                im.convert('RGB').save(img,quality=94)
            return img,'library-photo-fallback'
        except Exception:
            pass
    procedural_scene(scene,img,style,niche,idx)
    return img,'procedural-fallback'

def main():
    plan=json.loads(os.environ['INPUT_PLAN_JSON'])
    scenes=plan.get('scenes') or []
    if len(scenes)<6:
        raise RuntimeError('plano com poucas cenas')
    style=os.getenv('INPUT_CARTOON_STYLE','classic-2d')
    niche=str(plan.get('niche_key') or os.getenv('INPUT_NICHE_KEY','custom'))
    visual=os.getenv('INPUT_VISUAL_STYLE','realistic')
    media_mode=os.getenv('INPUT_MEDIA_MODE','hybrid')
    if niche=='analog-horror':
        style='retro-surreal'
        visual='cartoon'
        media_mode='photos'
    captions=os.getenv('INPUT_CAPTIONS','on')
    music=os.getenv('INPUT_MUSIC','off')
    voice=os.getenv('INPUT_VOICE','pt-BR-FranciscaNeural')
    pitch_mode=os.getenv('INPUT_VOICE_PITCH','default')
    speed_mode=os.getenv('INPUT_VOICE_SPEED','default')
    font_name=re.sub(r"[^A-Za-z0-9 _-]",'',os.getenv('INPUT_CAPTION_FONT','Montserrat'))[:50] or 'Montserrat'
    font_size=max(36,min(92,int(os.getenv('INPUT_CAPTION_SIZE','56'))))
    volume={'low':'0.12','medium':'0.22','high':'0.34'}.get(os.getenv('INPUT_MUSIC_VOLUME','medium'),'0.22')
    visual_context=str(plan.get('visual_context','')).strip()

    voices=[]
    clips=[]
    durations=[]
    sources=[]
    engines=[]
    used_photo=set()
    used_video=set()
    last_generated=None

    for i,scene in enumerate(scenes):
        text=str(scene.get('narration') or '').strip()
        if not text:
            raise RuntimeError(f'cena {i+1} sem narração')
        wav,engine=synthesize(text,i)
        dur=duration(wav)
        voices.append(wav)
        durations.append(dur)
        engines.append(engine)
        clip=WORK/f'scene_{i:02d}.mp4'
        religious=scene_is_religious(scene,niche)
        recommended='video' if scene.get('recommended_media')=='video' else 'image'

        if visual=='cartoon':
            img,source=choose_image(scene,i,style,niche,visual_context,False,last_generated,used_photo)
            render_image(img,clip,dur,i)
            if source.startswith(('generated','analog-')):
                last_generated=img
            sources.append({'scene':i+1,'type':'generated-illustration','source':source})
        else:
            want_video=media_mode=='videos' or (media_mode=='hybrid' and recommended=='video' and not religious)
            if want_video:
                queries=stock_queries(scene,niche)
                vid,url,q=pexels_video(queries,used_video)
                if url:
                    try:
                        src=WORK/f'real_{i:02d}.mp4'
                        download(url,src)
                        render_video(src,clip,dur)
                        sources.append({'scene':i+1,'type':'motion-library','source_id':vid,'query':q})
                    except Exception:
                        url=None
                if not url:
                    img,source=choose_image(scene,i,style,niche,visual_context,True,last_generated,used_photo)
                    render_image(img,clip,dur,i)
                    if source.startswith(('generated','analog-')):
                        last_generated=img
                    sources.append({'scene':i+1,'type':'generated-motion','source':source})
            else:
                img,source=choose_image(scene,i,style,niche,visual_context,True,last_generated,used_photo)
                render_image(img,clip,dur,i)
                if source.startswith(('generated','analog-')):
                    last_generated=img
                sources.append({'scene':i+1,'type':'generated-image','source':source})
        clips.append(clip)

    video=WORK/'video.mp4'
    narration=WORK/'narration.wav'
    concat(clips,'video',video)
    concat(voices,'audio',narration)
    total=duration(narration)
    ass=WORK/'captions.ass'
    make_ass(scenes,durations,ass,font_name,font_size)
    bgm=music_track(total,music,WORK/'music.wav')
    final=OUT/'final.mp4'
    vf=[]
    if captions=='on':
        vf=['-vf',f'ass={ass}']
    if bgm:
        run([
            'ffmpeg','-y','-i',str(video),'-i',str(narration),'-i',str(bgm),
            '-filter_complex',f'[1:a]volume=1.0[v];[2:a]volume={volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,alimiter=limit=0.95[a]',
            *vf,'-map','0:v','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','21','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(final)
        ],quiet=True)
    else:
        run([
            'ffmpeg','-y','-i',str(video),'-i',str(narration),*vf,
            '-map','0:v','-map','1:a','-c:v','libx264','-preset','veryfast','-crf','21','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(final)
        ],quiet=True)

    meta={
        'title':plan.get('title') or os.getenv('INPUT_TOPIC','Short Cloud Studio'),
        'summary':plan.get('summary',''),
        'visual_style':visual,
        'cartoon_style':style if visual=='cartoon' else None,
        'media_mode':media_mode,
        'scene_sources':sources,
        'voice':voice,
        'voice_pitch':pitch_mode,
        'voice_speed':speed_mode,
        'voice_engine':'neural' if all(x=='neural' for x in engines) else 'neural-with-fallback',
        'captions':captions=='on',
        'caption_font':font_name,
        'caption_size':font_size,
        'caption_position':'bottom',
        'caption_margin_bottom':140,
        'music':music,
        'music_volume':os.getenv('INPUT_MUSIC_VOLUME','medium'),
        'duration_seconds':round(duration(final),2),
        'engine':'Short Cloud Studio'
    }
    (OUT/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    if not final.exists() or final.stat().st_size<500000:
        raise RuntimeError('Vídeo final inválido')
    print(json.dumps({'ok':True,'duration_seconds':meta['duration_seconds'],'scenes':len(scenes)},ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
