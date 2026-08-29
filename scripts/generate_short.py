#!/usr/bin/env python3
import json, os, re, subprocess, math
from pathlib import Path
from urllib.parse import quote_plus
import requests
import soundfile as sf
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from kokoro_onnx import Kokoro
from misaki.espeak import EspeakG2P

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work'
OUT = ROOT / 'output'
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
PEXELS_API_KEY = os.environ['PEXELS_API_KEY']
GROQ_API_KEY = os.environ.get('GROQ_API_KEY','')
KOKORO_MODEL = os.getenv('KOKORO_MODEL_PATH','models/kokoro/kokoro-v1.0.onnx')
KOKORO_VOICES = os.getenv('KOKORO_VOICES_PATH','models/kokoro/voices-v1.0.bin')
PIPER_MODEL = os.getenv('PIPER_MODEL_PATH','models/pt_BR-faber-medium.onnx')

NICHE_PREFIX = {
    'biblical': 'ancient biblical middle east iron age historical reenactment',
    'cinematic': 'cinematic dramatic realistic storytelling',
    'mysteries': 'mystery documentary investigation cinematic',
    'ancient': 'ancient civilization historical reenactment archaeology',
    'motivation': 'motivational human achievement cinematic',
    'science': 'science documentary space astronomy laboratory',
    'true-stories': 'true story documentary historical realistic',
    'horror': 'dark suspense eerie cinematic night',
    'life-lessons': 'emotional human story cinematic everyday life',
    'animals': 'wildlife nature documentary animal behavior',
    'custom': ''
}
MODERN_REJECT = {'modern','city','car','cars','phone','smartphone','office','business','suit','jeans','street','computer','laptop','skyscraper','motorcycle','train','airport'}


def run(cmd, *, stdin=None):
    print('+', ' '.join(map(str, cmd)), flush=True)
    return subprocess.run(cmd, input=stdin, check=True, text=not isinstance(stdin, (bytes, bytearray)))


def probe_duration(path):
    p = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)], capture_output=True, text=True, check=True)
    return float(p.stdout.strip())


def ass_time(seconds):
    cs=max(0,int(round(seconds*100))); h,rem=divmod(cs,360000); m,rem=divmod(rem,6000); s,cs=divmod(rem,100)
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def ass_escape(text):
    return str(text).replace('\\',r'\\').replace('{',r'\{').replace('}',r'\}').replace('\n',r'\N')


def write_ass(events,path):
    header='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Bottom,DejaVu Sans,38,&H00FFFFFF,&H00FFFFFF,&H00101010,&H60000000,-1,0,0,0,100,100,0,0,1,3,0,2,78,78,120,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'''
    body=[f'Dialogue: 0,{ass_time(a)},{ass_time(b)},Bottom,,0,0,0,,{ass_escape(t)}' for a,b,t in events if b>a]
    path.write_text(header+'\n'.join(body)+'\n',encoding='utf-8')


def group_words(words,max_words=5):
    grouped=[]; cur=[]
    for w in words:
        token=str(w.get('word') or '').strip()
        if not token: continue
        cur.append((float(w.get('start',0)),float(w.get('end',0)),token))
        if len(cur)>=max_words or (len(cur)>=3 and re.search(r'[.!?]$',token)):
            grouped.append((cur[0][0],cur[-1][1],' '.join(x[2] for x in cur))); cur=[]
    if cur: grouped.append((cur[0][0],cur[-1][1],' '.join(x[2] for x in cur)))
    return grouped


def fallback_subtitles(scenes,durations):
    events=[]; offset=0.0
    for scene,dur in zip(scenes,durations):
        tokens=str(scene.get('narration','')).split(); chunks=[]; cur=[]
        for token in tokens:
            cur.append(token)
            if len(cur)>=5 or (len(cur)>=3 and re.search(r'[.!?]$',token)):
                chunks.append(cur); cur=[]
        if cur: chunks.append(cur)
        total=max(1,sum(len(c) for c in chunks)); cursor=offset
        for chunk in chunks:
            part=dur*len(chunk)/total; events.append((cursor,min(offset+dur,cursor+part),' '.join(chunk))); cursor+=part
        offset+=dur
    return events


def transcribe_words(audio_path):
    if not GROQ_API_KEY: raise RuntimeError('GROQ_API_KEY ausente para sincronização')
    with open(audio_path,'rb') as f:
        r=requests.post('https://api.groq.com/openai/v1/audio/transcriptions',headers={'Authorization':f'Bearer {GROQ_API_KEY}'},files={'file':('narration.wav',f,'audio/wav')},data=[('model','whisper-large-v3-turbo'),('language','pt'),('response_format','verbose_json'),('timestamp_granularities[]','word')],timeout=120)
    r.raise_for_status(); words=r.json().get('words') or []
    if not words: raise RuntimeError('Whisper não retornou palavras com tempo')
    return group_words(words,5)


def synthesize_scene(text,voice,idx,kokoro,g2p):
    wav=WORK/f'voice_{idx:02d}.wav'
    try:
        phonemes,_=g2p(text)
        samples,sr=kokoro.create(phonemes,voice,is_phonemes=True,speed=1.0)
        sf.write(wav,samples,sr)
        if probe_duration(wav)<.4: raise RuntimeError('Kokoro produziu áudio inválido')
        return wav,'kokoro'
    except Exception as exc:
        print(f'Kokoro falhou na cena {idx+1}: {exc}; usando Piper.',flush=True)
        run(['piper','--model',PIPER_MODEL,'--output_file',str(wav)],stdin=text.encode('utf-8'))
        return wav,'piper'


def _tokens(text):
    return set(re.findall(r'[a-z]{3,}', str(text).lower()))


def _historical_reject(alt,niche_key):
    if niche_key not in {'biblical','ancient'}: return False
    a=_tokens(alt)
    return bool(a & MODERN_REJECT)


def pexels_photo(queries,used_ids,niche_key):
    best=[]
    for query in [q for q in queries if q]:
        r=requests.get(f'https://api.pexels.com/v1/search?query={quote_plus(query)}&orientation=portrait&per_page=24',headers={'Authorization':PEXELS_API_KEY},timeout=40)
        r.raise_for_status(); qtokens=_tokens(query)
        for p in r.json().get('photos',[]):
            if p.get('id') in used_ids: continue
            alt=str(p.get('alt') or '').lower()
            if _historical_reject(alt,niche_key): continue
            score=sum(2 for t in qtokens if t in alt)
            if niche_key in {'biblical','ancient'}:
                score += sum(3 for t in {'ancient','desert','warrior','armor','temple','ruins','robe','shepherd','historical'} if t in alt)
            best.append((score,p,query))
        if best and max(x[0] for x in best)>=4: break
    best.sort(key=lambda x:x[0],reverse=True)
    for _,p,q in best:
        src=p.get('src') or {}; link=src.get('portrait') or src.get('large2x') or src.get('large') or src.get('original')
        if link: used_ids.add(p.get('id')); return p.get('id'),link,p.get('alt') or '',q
    return None,None,'',''


def pexels_video(queries,used_ids,niche_key):
    candidates=[]
    for query in [q for q in queries if q]:
        r=requests.get(f'https://api.pexels.com/videos/search?query={quote_plus(query)}&orientation=portrait&per_page=18',headers={'Authorization':PEXELS_API_KEY},timeout=40)
        r.raise_for_status()
        for video in r.json().get('videos',[]):
            if video.get('id') in used_ids: continue
            files=[f for f in video.get('video_files',[]) if f.get('link') and f.get('width') and f.get('height')]
            files.sort(key=lambda f:(0 if f['height']>f['width'] else 1,abs(f.get('width',0)-1080)))
            if files: candidates.append((video,files[0],query))
        if candidates: break
    if candidates:
        video,file,q=candidates[0]; used_ids.add(video.get('id')); return video.get('id'),file['link'],q
    return None,None,''


def download(url,path):
    with requests.get(url,stream=True,timeout=120) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for chunk in r.iter_content(1024*1024):
                if chunk:f.write(chunk)


def cartoonize(src,dst,style):
    im=Image.open(src).convert('RGB'); im.thumbnail((1600,2200),Image.Resampling.LANCZOS)
    if style=='paper-cut':
        base=ImageEnhance.Color(im.filter(ImageFilter.MedianFilter(7))).enhance(1.5); base=ImageOps.posterize(base,3); base=ImageEnhance.Contrast(base).enhance(1.15)
    elif style=='interdimensional':
        base=ImageEnhance.Color(im.filter(ImageFilter.MedianFilter(5))).enhance(1.75); base=ImageOps.posterize(base,5); base=ImageEnhance.Contrast(base).enhance(1.2)
    elif style=='retro-surreal':
        base=ImageEnhance.Color(im.filter(ImageFilter.GaussianBlur(.55))).enhance(.9); base=ImageEnhance.Contrast(base).enhance(1.08); base=ImageOps.posterize(base,5)
    elif style=='comic':
        base=ImageEnhance.Contrast(im).enhance(1.55); base=ImageEnhance.Color(base).enhance(1.3); base=ImageOps.posterize(base,4)
    else:
        base=ImageEnhance.Color(im.filter(ImageFilter.MedianFilter(5))).enhance(1.3); base=ImageOps.posterize(base,5)
    edges=im.convert('L').filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(.7)); edges=ImageOps.invert(edges).point(lambda p:255 if p>205 else max(65,p)); edge_rgb=Image.merge('RGB',(edges,edges,edges))
    strength=.24 if style in {'comic','interdimensional'} else .16
    Image.blend(base,Image.blend(base,edge_rgb,strength),.58).save(dst,quality=93)


def fallback_image(path,niche_key):
    palettes={
        'biblical':((90,61,35),(217,165,92)), 'ancient':((68,54,43),(180,141,93)),
        'horror':((10,12,20),(45,40,58)), 'science':((8,20,40),(45,88,135)),
        'animals':((26,49,35),(96,135,83))
    }
    c1,c2=palettes.get(niche_key,((18,22,31),(71,62,105)))
    h,w=1920,1080; arr=np.zeros((h,w,3),dtype=np.uint8)
    for y in range(h):
        t=y/(h-1); arr[y,:,0]=int(c1[0]*(1-t)+c2[0]*t); arr[y,:,1]=int(c1[1]*(1-t)+c2[1]*t); arr[y,:,2]=int(c1[2]*(1-t)+c2[2]*t)
    Image.fromarray(arr).filter(ImageFilter.GaussianBlur(18)).save(path,quality=92)


def render_photo(src,dst,duration,idx):
    frames=max(1,int(math.ceil(duration*30)))
    if idx%3==0: zoom="min(zoom+0.0009,1.10)"; x="iw/2-(iw/zoom/2)"; y="ih/2-(ih/zoom/2)"
    elif idx%3==1: zoom="1.08"; x=f"(iw-iw/zoom)*on/{frames}"; y="ih/2-(ih/zoom/2)"
    else: zoom="min(zoom+0.0007,1.08)"; x="iw/2-(iw/zoom/2)"; y=f"(ih-ih/zoom)*(1-on/{frames})"
    vf=f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps=30,format=yuv420p"
    run(['ffmpeg','-y','-loop','1','-i',str(src),'-t',f'{duration:.3f}','-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p',str(dst)])


def render_video(src,dst,duration):
    vf='scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p'
    run(['ffmpeg','-y','-stream_loop','-1','-i',str(src),'-t',f'{duration:.3f}','-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p',str(dst)])


def concat_media(files,kind):
    manifest=WORK/f'{kind}_concat.txt'; manifest.write_text('\n'.join(f"file '{p.resolve()}'" for p in files),encoding='utf-8'); out=WORK/('video.mp4' if kind=='video' else 'audio.wav')
    if kind=='video': run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(manifest),'-c','copy',str(out)])
    else: run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(manifest),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(out)])
    return out


def _adsr(n, attack=.08, release=.18):
    env=np.ones(n,dtype=np.float32); a=max(1,int(n*attack)); r=max(1,int(n*release)); env[:a]=np.linspace(0,1,a,dtype=np.float32); env[-r:]=np.linspace(1,0,r,dtype=np.float32); return env


def generate_music(duration,style):
    if style=='off': return None
    sr=48000; n=int(duration*sr); audio=np.zeros(n,dtype=np.float32)
    configs={
        'viral-pulse': {'bpm':104,'chords':[(220,277,330),(196,247,294),(174,220,261),(196,247,294)],'bass':.16,'pad':.12,'beat':.12},
        'cinematic-rise': {'bpm':76,'chords':[(146,220,293),(130,196,261),(164,246,329),(110,164,220)],'bass':.11,'pad':.19,'beat':.035},
        'mystery-tension': {'bpm':82,'chords':[(110,164,233),(116,174,246),(103,155,220),(98,146,207)],'bass':.14,'pad':.13,'beat':.06},
        'emotional-ambient': {'bpm':68,'chords':[(196,246,293),(174,220,261),(220,277,329),(164,207,246)],'bass':.07,'pad':.16,'beat':.018},
        'epic-ancient': {'bpm':88,'chords':[(110,164,220),(123,184,246),(98,146,196),(110,164,220)],'bass':.17,'pad':.15,'beat':.09}
    }
    c=configs.get(style,configs['emotional-ambient']); bar=60/c['bpm']*4; bars=max(1,int(math.ceil(duration/bar)))
    for b in range(bars):
        start=int(b*bar*sr); end=min(n,int((b+1)*bar*sr)); ln=end-start
        if ln<=0: continue
        tt=np.arange(ln,dtype=np.float32)/sr; chord=c['chords'][b%len(c['chords'])]; env=_adsr(ln,.08,.14)
        pad=sum(np.sin(2*np.pi*f*tt) + .28*np.sin(2*np.pi*(f*2)*tt) for f in chord)/len(chord)
        bass=np.sin(2*np.pi*(chord[0]/2)*tt)
        audio[start:end]+=env*(pad*c['pad']+bass*c['bass'])
    beat=60/c['bpm']; beat_len=int(.16*sr)
    for k in range(int(duration/beat)+1):
        st=int(k*beat*sr)
        if st>=n: break
        ln=min(beat_len,n-st); tt=np.arange(ln,dtype=np.float32)/sr; denom=max(.001,float(tt[-1]) if len(tt)>1 else .16); kick=np.sin(2*np.pi*(58-28*(tt/denom))*tt)*np.exp(-tt*20)
        audio[st:st+ln]+=kick*c['beat']
        if style in {'viral-pulse','epic-ancient'} and k%2==1:
            hiss=(np.random.default_rng(k+7).normal(0,1,ln).astype(np.float32))*np.exp(-tt*30)*c['beat']*.20; audio[st:st+ln]+=hiss
    fade=int(min(1.5,duration/8)*sr)
    if fade>1: audio[:fade]*=np.linspace(0,1,fade,dtype=np.float32); audio[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)
    peak=float(np.max(np.abs(audio))) or 1.; audio=np.clip(audio/(peak*1.35),-1,1); out=WORK/'music.wav'; sf.write(out,audio,sr); return out


def mix_audio(narration,music,volume):
    if not music: return narration
    levels={'low':.075,'medium':.11,'high':.16}; vol=levels.get(volume,.11); out=WORK/'audio_mix.wav'
    run(['ffmpeg','-y','-i',str(narration),'-i',str(music),'-filter_complex',f'[1:a]volume={vol}[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2,alimiter=limit=0.95[a]','-map','[a]','-ar','48000','-ac','1','-c:a','pcm_s16le',str(out)])
    return out


def main():
    topic=os.environ.get('INPUT_TOPIC','').strip(); target=min(70.,max(60.,float(os.environ.get('INPUT_DURATION','65'))))
    visual_style=os.environ.get('INPUT_VISUAL_STYLE','realistic'); cartoon_style=os.environ.get('INPUT_CARTOON_STYLE','classic-2d'); media_mode=os.environ.get('INPUT_MEDIA_MODE','photos'); niche_key=os.environ.get('INPUT_NICHE_KEY','custom')
    voice=os.environ.get('INPUT_VOICE','pm_alex'); captions_on=os.environ.get('INPUT_CAPTIONS','on')!='off'; music_style=os.environ.get('INPUT_MUSIC','off'); music_volume=os.environ.get('INPUT_MUSIC_VOLUME','medium'); raw_plan=os.environ.get('INPUT_PLAN_JSON','')
    if not raw_plan: raise SystemExit('INPUT_PLAN_JSON ausente')
    plan=json.loads(raw_plan); scenes=plan.get('scenes') or []; niche_key=plan.get('niche_key') or niche_key
    if len(scenes)<6: raise SystemExit('Plano com poucas cenas')
    print(f'Plano aprovado: {plan.get("title") or topic}',flush=True)

    kokoro=Kokoro(KOKORO_MODEL,KOKORO_VOICES); g2p=EspeakG2P(language='pt-br'); natural=[]; engines=[]
    for i,scene in enumerate(scenes):
        audio,engine=synthesize_scene(scene.get('narration',''),voice,i,kokoro,g2p); natural.append({'audio':audio,'duration':probe_duration(audio)}); engines.append(engine)
    total_natural=sum(x['duration'] for x in natural); tempo=max(.82,min(1.22,total_natural/target)); adjusted_audio=[]; scene_durations=[]
    for i,item in enumerate(natural):
        out=WORK/f'audio_{i:02d}.wav'; run(['ffmpeg','-y','-i',str(item['audio']),'-filter:a',f'atempo={tempo:.6f}','-ar','48000','-ac','1','-c:a','pcm_s16le',str(out)]); adjusted_audio.append(out); scene_durations.append(probe_duration(out))
    narration=concat_media(adjusted_audio,'audio')
    try: subtitle_events=transcribe_words(narration)
    except Exception as exc: print(f'Whisper falhou: {exc}; usando sincronização por cena.',flush=True); subtitle_events=fallback_subtitles(scenes,scene_durations)

    prefix=NICHE_PREFIX.get(niche_key,''); used_photo,used_video=set(),set(); rendered=[]; credits=[]
    for i,(scene,dur) in enumerate(zip(scenes,scene_durations)):
        primary=' '.join(f'{prefix} {scene.get("visual_query") or "cinematic scene"}'.split())[:220]
        backup=' '.join(f'{prefix} {scene.get("visual_query_backup") or scene.get("visual_query") or "cinematic scene"}'.split())[:220]
        queries=[primary,backup]
        requested=scene.get('recommended_media','image'); media='image' if media_mode=='photos' or visual_style=='cartoon' else ('video' if media_mode=='videos' else requested)
        print(f'Cena {i+1}/{len(scenes)} — {media}: {primary}',flush=True); dst=WORK/f'scene_{i:02d}.mp4'
        if media=='video':
            vid,url,used_query=pexels_video(queries,used_video,niche_key)
            if url:
                src=WORK/f'source_{i:02d}.mp4'; download(url,src); render_video(src,dst,dur); credits.append({'scene':i+1,'type':'video','pexels_id':vid,'query':used_query})
            else: media='image'
        if media=='image':
            pid,url,alt,used_query=pexels_photo(queries,used_photo,niche_key); src=WORK/f'source_{i:02d}.jpg'
            if url:
                download(url,src); credits.append({'scene':i+1,'type':'photo','pexels_id':pid,'query':used_query,'alt':alt})
            else:
                print(f'Cena {i+1}: nenhuma mídia suficientemente coerente; usando fundo temático em vez de imagem aleatória.',flush=True); fallback_image(src,niche_key)
            if visual_style=='cartoon':
                stylized=WORK/f'cartoon_{i:02d}.jpg'; cartoonize(src,stylized,cartoon_style); src=stylized
            render_photo(src,dst,dur,i)
        rendered.append(dst)

    video=concat_media(rendered,'video'); ass=WORK/'subtitles.ass'; write_ass(subtitle_events,ass)
    music=generate_music(probe_duration(narration),music_style); final_audio=mix_audio(narration,music,music_volume)
    final=OUT/'final.mp4'; cmd=['ffmpeg','-y','-i',str(video),'-i',str(final_audio)]
    if captions_on:
        ass_path=str(ass.resolve()).replace('\\','/').replace(':','\\:').replace("'","\\'"); cmd+=['-vf',f"ass='{ass_path}'"]
    cmd+=['-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac','-b:a','160k','-pix_fmt','yuv420p','-movflags','+faststart','-shortest',str(final)]; run(cmd)
    metadata={'topic':topic,'title':plan.get('title',topic),'summary':plan.get('summary',''),'description':plan.get('description',''),'hashtags':plan.get('hashtags',[]),'duration_target':target,'duration_final':round(probe_duration(final),3),'niche_key':niche_key,'visual_context':plan.get('visual_context',''),'visual_style':visual_style,'cartoon_style':cartoon_style,'media_mode':media_mode,'voice':voice,'tts_engines':engines,'captions':captions_on,'music':music_style,'music_volume':music_volume,'scenes':scenes,'pexels':credits}
    (OUT/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({'ok':True,'file':str(final),'duration':metadata['duration_final'],'title':metadata['title']},ensure_ascii=False))

if __name__=='__main__': main()
