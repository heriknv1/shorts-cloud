#!/usr/bin/env python3
import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work_turbo'
OUT=ROOT/'output'
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)


def run(cmd):
    print('+',' '.join(map(str,cmd)),flush=True)
    subprocess.run(cmd,check=True)


def media_duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],text=True).strip())


def scene_durations(plan,total):
    files=sorted(WORK.glob('voice_??.wav'))
    vals=[]
    for p in files[:len(plan.get('scenes') or [])]:
        try: vals.append(media_duration(p))
        except Exception: vals=[];break
    if len(vals)==len(plan.get('scenes') or []) and sum(vals)>0:
        scale=total/sum(vals)
        return [x*scale for x in vals]
    count=max(1,len(plan.get('scenes') or []))
    return [total/count]*count


def srt_time(seconds):
    ms=max(0,int(round(seconds*1000)))
    h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def write_srt(plan,total):
    scenes=plan.get('scenes') or []
    durs=scene_durations(plan,total)
    rows=[];cursor=0.0;idx=1
    for scene,dur in zip(scenes,durs):
        words=str(scene.get('narration') or '').split()
        chunks=[];cur=[]
        for word in words:
            cur.append(word)
            if len(cur)>=7 or str(word).endswith(('.', '!', '?', '…')):
                chunks.append(' '.join(cur));cur=[]
        if cur: chunks.append(' '.join(cur))
        if not chunks: chunks=['']
        part=dur/len(chunks)
        for text in chunks:
            end=min(total,cursor+part)
            rows += [str(idx),f'{srt_time(cursor)} --> {srt_time(end)}',text,'']
            idx+=1;cursor=end
    (OUT/'captions.srt').write_text('\n'.join(rows),encoding='utf-8')


def make_extra_audio(total,scene_durs,pace,sfx_mode,ambience_mode,niche):
    if sfx_mode=='off' and ambience_mode=='off': return None
    sr=48000;n=max(1,int(total*sr));audio=np.zeros(n,dtype=np.float32)
    rng=np.random.default_rng(abs(hash((os.getenv('GITHUB_RUN_ID',''),niche)))%(2**32))
    if ambience_mode!='off':
        t=np.arange(n,dtype=np.float32)/sr
        base={'horror':43.0,'horror-real':47.0,'analog-horror':49.0,'science':82.0,'biblical':55.0,'devotional':65.0,'motivation':72.0}.get(niche,58.0)
        audio += .0045*np.sin(2*np.pi*base*t)+.0023*np.sin(2*np.pi*(base*1.51)*t)
        # Sparse random anchors interpolated over time create a soft room-like texture cheaply.
        step=2400
        xp=np.arange(0,n+step,step,dtype=np.int64)
        fp=rng.normal(0,1,len(xp)).astype(np.float32)
        smooth=np.interp(np.arange(n,dtype=np.int64),xp,fp).astype(np.float32)
        audio += .0025*smooth
        if niche=='analog-horror':
            audio += .0048*rng.normal(0,1,n).astype(np.float32)
            for when in np.arange(5.0,total,8.5):
                start=int(when*sr);ln=min(int(.11*sr),n-start)
                if ln>0: audio[start:start+ln]+=.025*rng.normal(0,1,ln).astype(np.float32)*np.exp(-np.linspace(0,5,ln,dtype=np.float32))
    if sfx_mode!='off':
        strength=.030 if sfx_mode=='subtle' else .055
        boundaries=[];c=0.0
        for d in scene_durs[:-1]: c+=d;boundaries.append(c)
        interval={'fast':1.7,'balanced':2.2,'cinematic':3.0}.get(pace,2.2)
        micro=np.arange(interval,total,interval)
        events=[(x,strength) for x in boundaries]+[(float(x),strength*.35) for x in micro]
        for when,amp in events:
            start=int(when*sr);ln=min(int(.14*sr),n-start)
            if ln<=0: continue
            env=np.exp(-np.linspace(0,6,ln,dtype=np.float32))
            noise=rng.normal(0,1,ln).astype(np.float32)
            phase=np.cumsum(np.linspace(180,70,ln,dtype=np.float32))/sr
            tone=np.sin(2*np.pi*phase)
            audio[start:start+ln]+=amp*(noise*.34+tone*.66)*env
    peak=max(.001,float(np.max(np.abs(audio))))
    if peak>.15: audio*=.15/peak
    path=WORK/'creative_extra.wav';sf.write(path,audio,sr)
    return path


def video_filter(pace,brand_text,niche='custom',include_captions=True):
    # Scene clips already contain smooth camera motion. Keep the finishing crop fixed;
    # discontinuous crop coordinates caused visible jumps throughout the final video.
    filters=["scale=1188:2112,crop=1080:1920:x=54:y=96"]
    if niche=='analog-horror':
        filters += ["crop=1080:810:0:555","scale=960:720","pad=1080:1920:60:600:black","eq=contrast=1.22:brightness=-0.075:saturation=0.38:gamma=0.92","colorbalance=rs=.14:gs=-.05:bs=-.09","noise=alls=9:allf=t+u","drawgrid=width=iw:height=4:thickness=1:color=black@0.16","drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf:text='PLAY  ARCHIVE':fontcolor=white@0.62:fontsize=23:x=42:y=560:box=1:boxcolor=black@0.18"]
        if include_captions and os.getenv('INPUT_CAPTIONS','on')=='on':
            font=''.join(c for c in os.getenv('INPUT_CAPTION_FONT','Montserrat') if c.isalnum() or c in ' _-')[:50] or 'Montserrat'
            size=max(36,min(92,int(os.getenv('INPUT_CAPTION_SIZE','56'))))
            filters.append(f"subtitles=output/captions.srt:force_style='FontName={font},FontSize={size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BackColour=&H99000000,BorderStyle=3,Outline=2,Shadow=0,Alignment=2,MarginL=72,MarginR=72,MarginV=120'")
    if brand_text:
        textfile=WORK/'brand.txt';textfile.write_text(brand_text,encoding='utf-8')
        filters.append("drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:textfile=work_turbo/brand.txt:fontcolor=white@0.55:fontsize=24:borderw=1:bordercolor=black@0.25:x=w-tw-38:y=42")
    filters += ["fps=30","format=yuv420p"]
    return ','.join(filters)


def finish_video(source,dest,total,extra,pace,brand_text,niche='custom',include_captions=True):
    vf=video_filter(pace,brand_text,niche,include_captions)
    if extra:
        run(['ffmpeg','-y','-i',str(source),'-i',str(extra),'-filter_complex','[0:a][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]','-vf',vf,'-map','0:v','-map','[a]','-t',f'{total:.3f}','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-profile:v','high','-level','4.1','-c:a','aac','-b:a','192k','-movflags','+faststart',str(dest)])
    else:
        run(['ffmpeg','-y','-i',str(source),'-vf',vf,'-t',f'{total:.3f}','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-profile:v','high','-level','4.1','-c:a','copy','-movflags','+faststart',str(dest)])


def build_clean_base(total):
    video=WORK/'video.mp4';narr=WORK/'narration.wav';music=WORK/'music.wav';out=WORK/'clean_base.mp4'
    if not video.exists() or not narr.exists(): return None
    if music.exists():
        vol={'low':'0.12','medium':'0.22','high':'0.34'}.get(os.getenv('INPUT_MUSIC_VOLUME','medium'),'0.22')
        run(['ffmpeg','-y','-i',str(video),'-i',str(narr),'-i',str(music),'-filter_complex',f'[1:a]volume=1.0[v];[2:a]volume={vol}[m];[v][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]','-map','0:v','-map','[a]','-t',f'{total:.3f}','-c:v','copy','-c:a','aac','-b:a','192k',str(out)])
    else:
        run(['ffmpeg','-y','-i',str(video),'-i',str(narr),'-map','0:v','-map','1:a','-t',f'{total:.3f}','-c:v','copy','-c:a','aac','-b:a','192k',str(out)])
    return out


def main():
    final=OUT/'final.mp4'
    if not final.exists(): raise SystemExit('Vídeo final ausente para acabamento.')
    total=float(os.getenv('INPUT_DURATION','65'))
    plan=json.loads(os.getenv('INPUT_PLAN_JSON','{}'))
    niche=plan.get('niche_key') or os.getenv('INPUT_NICHE_KEY','custom')
    pace=os.getenv('INPUT_EDITING_PACE','balanced')
    sfx=os.getenv('INPUT_SFX_MODE','subtle')
    ambience=os.getenv('INPUT_AMBIENCE_MODE','subtle')
    brand=os.getenv('INPUT_BRANDING_MODE','off')=='on'
    brand_text=os.getenv('INPUT_BRAND_TEXT','').strip()[:48] if brand else ''
    clean=os.getenv('INPUT_CLEAN_EXPORT','on')=='on'
    durs=scene_durations(plan,total)
    extra=make_extra_audio(total,durs,pace,sfx,ambience,niche)
    write_srt(plan,total)
    source=WORK/'final_before_dynamic.mp4';final.replace(source)
    if niche=='analog-horror':
        clean_source=build_clean_base(total)
        if clean_source: source=clean_source
    finish_video(source,final,total,extra,pace,brand_text,niche)
    if clean and os.getenv('INPUT_CAPTIONS','on')=='on':
        base=build_clean_base(total)
        if base: finish_video(base,OUT/'final_sem_legenda.mp4',total,extra,pace,brand_text,niche,include_captions=False)
    meta_path=OUT/'metadata.json'
    try: meta=json.loads(meta_path.read_text(encoding='utf-8'))
    except Exception: meta={}
    meta['creative_edit']={'pace':pace,'sfx':sfx,'ambience':ambience,'branding':bool(brand_text),'clean_export':clean,'srt_export':True}
    meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Acabamento dinâmico aplicado.',flush=True)

if __name__=='__main__': main()
