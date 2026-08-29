#!/usr/bin/env python3
import json, math, os, subprocess, textwrap, hashlib
from pathlib import Path
from urllib.parse import quote

import numpy as np
import requests
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work_turbo"
OUT = ROOT / "output"
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
PIPER_MODEL = os.getenv("PIPER_MODEL_PATH", "models/pt_BR-faber-medium.onnx")


def run(cmd, stdin=None):
    print("+", " ".join(map(str, cmd)), flush=True)
    kwargs = {"check": True}
    if stdin is not None:
        kwargs["input"] = stdin
    return subprocess.run(cmd, **kwargs)


def duration(path):
    p = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)], capture_output=True, text=True, check=True)
    return float(p.stdout.strip())


def palette(style, niche):
    palettes = {
        "classic-2d": ((24,30,48),(236,170,82),(70,111,167),(244,221,175)),
        "comic": ((14,18,30),(211,70,64),(230,177,67),(58,73,117)),
        "paper-cut": ((36,45,67),(235,107,78),(241,193,82),(94,163,139)),
        "retro-surreal": ((52,41,63),(219,126,105),(224,189,124),(80,126,137)),
        "interdimensional": ((20,18,48),(162,86,225),(59,211,181),(240,177,72)),
    }
    base = palettes.get(style, palettes["classic-2d"])
    if niche == "biblical": return ((74,48,31),(225,161,80),(104,78,55),(245,218,166))
    if niche == "horror": return ((12,15,24),(74,43,76),(128,54,60),(190,173,146))
    if niche == "science": return ((7,20,42),(39,106,172),(55,203,199),(194,225,255))
    return base


def font(size):
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in paths:
        if Path(p).exists(): return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def procedural_scene(scene, path, style, niche, idx):
    W,H = 1080,1920
    c0,c1,c2,c3 = palette(style,niche)
    im = Image.new("RGB", (W,H), c0)
    d = ImageDraw.Draw(im)
    # sky bands / graphic layers
    d.rectangle((0,0,W,760), fill=c0)
    d.ellipse((710,120,980,390), fill=c1)
    d.polygon([(0,760),(260,520),(510,760),(760,440),(1080,760),(1080,1260),(0,1260)], fill=c2)
    d.polygon([(0,1120),(260,880),(520,1110),(780,850),(1080,1080),(1080,H),(0,H)], fill=c1)
    d.rectangle((0,1370,W,H), fill=c0)

    text = (str(scene.get("visual_description", "")) + " " + str(scene.get("narration", ""))).lower()
    # simple cartoon figures; sizes adapt to keywords
    giant = any(k in text for k in ["golias","gigante","giant"])
    people = 2 if any(k in text for k in ["davi","golias","homem","mulher","rei","soldado","personagem","warrior"]) else 1
    if any(k in text for k in ["exército","army","multidão","soldados"]): people = 5
    ground = 1370
    for n in range(people):
        x = 180 + n * (700 // max(1,people-1)) if people > 1 else 530
        big = giant and n == people-1
        scale = 1.55 if big else 1.0
        head_r = int(68*scale); body_h=int(300*scale); body_w=int(145*scale)
        y = ground - body_h - head_r*2
        d.ellipse((x-head_r,y,x+head_r,y+head_r*2), fill=c3, outline=(20,20,24), width=10)
        d.polygon([(x-body_w,y+head_r*2),(x+body_w,y+head_r*2),(x+body_w//2,ground),(x-body_w//2,ground)], fill=c2 if n%2==0 else c1, outline=(20,20,24))
        d.line((x-body_w,y+head_r*3,x-220,ground-120), fill=(20,20,24), width=18)
        d.line((x+body_w,y+head_r*3,x+220,ground-120), fill=(20,20,24), width=18)
        d.line((x-45,ground,x-85,ground+160), fill=(20,20,24), width=22)
        d.line((x+45,ground,x+85,ground+160), fill=(20,20,24), width=22)
    if any(k in text for k in ["funda","sling"]):
        d.arc((130,880,460,1210),20,250,fill=(24,20,18),width=18)
    if any(k in text for k in ["espada","sword"]):
        d.line((830,930,980,620), fill=(230,230,235), width=22)
    if any(k in text for k in ["estrela","space","espaço","planet","planeta"]):
        for s in range(35):
            x=(s*97+idx*53)%W; y=(s*151+idx*79)%720
            d.ellipse((x,y,x+6,y+6), fill=(245,245,230))
    # caption-like scene label embedded subtly in illustration, not the narration
    beat = str(scene.get("beat") or f"Cena {idx+1}")[:36]
    d.rounded_rectangle((70,85,760,190), radius=34, fill=(0,0,0,120) if im.mode=="RGBA" else (20,20,24))
    d.text((105,112), beat, font=font(42), fill=(255,255,255))
    im = im.filter(ImageFilter.SMOOTH_MORE)
    im.save(path, quality=94)


def ai_cartoon_scene(scene, path, style, niche, idx):
    desc = str(scene.get("visual_description") or scene.get("visual_query") or "cinematic cartoon scene")
    style_text = {
        "classic-2d":"clean 2D animated film illustration, expressive characters, crisp outlines",
        "comic":"cinematic comic book illustration, bold ink outlines, dramatic shadows",
        "paper-cut":"paper cutout 2D animation, flat geometric shapes, handmade texture",
        "retro-surreal":"retro surreal 2D animation, nostalgic palette, strange dreamlike composition",
        "interdimensional":"original sci-fi surreal 2D animation, vibrant alien palette, expressive cartoon characters",
    }.get(style, "clean 2D animation")
    safety = "no photo, no photorealism, no text, no watermark, vertical composition, consistent animated illustration"
    if niche == "biblical": safety += ", ancient biblical Middle East, Iron Age plausible clothing, tunics, sandals, no modern objects, no medieval European armor"
    prompt = f"{desc}. {style_text}. {safety}"
    seed = int(hashlib.sha256((prompt+str(idx)).encode()).hexdigest()[:8],16)
    url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=768&height=1344&nologo=true&seed={seed}&enhance=true"
    try:
        r = requests.get(url, timeout=95, headers={"User-Agent":"ShortsCloudStudio/2.0"})
        r.raise_for_status()
        if len(r.content) < 20000: raise RuntimeError("imagem remota pequena demais")
        tmp = path.with_suffix(".download")
        tmp.write_bytes(r.content)
        with Image.open(tmp) as im:
            im.convert("RGB").resize((1080,1920),Image.Resampling.LANCZOS).save(path, quality=94)
        tmp.unlink(missing_ok=True)
        print(f"Cena {idx+1}: ilustração IA obtida.", flush=True)
        return "ai-cartoon"
    except Exception as exc:
        print(f"Cena {idx+1}: gerador de ilustração indisponível ({exc}); usando desenho vetorial local.", flush=True)
        procedural_scene(scene,path,style,niche,idx)
        return "vector-cartoon"


def synthesize(text, idx):
    wav = WORK / f"voice_{idx:02d}.wav"
    run(["piper","--model",PIPER_MODEL,"--output_file",str(wav)], stdin=text.encode("utf-8"))
    if not wav.exists() or duration(wav) < .3: raise RuntimeError("Piper não gerou áudio válido")
    return wav


def render_image(img, out, seconds, idx):
    frames=max(1,int(math.ceil(seconds*30)))
    if idx%2:
        z="min(zoom+0.0008,1.10)"; x="iw/2-(iw/zoom/2)"; y="ih/2-(ih/zoom/2)"
    else:
        z="1.08"; x=f"(iw-iw/zoom)*on/{frames}"; y="ih/2-(ih/zoom/2)"
    vf=f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps=30,format=yuv420p"
    run(["ffmpeg","-y","-loop","1","-i",str(img),"-t",f"{seconds:.3f}","-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p",str(out)])


def concat(files, kind, output):
    manifest=WORK/f"concat_{kind}.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in files),encoding="utf-8")
    if kind=="video": run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(manifest),"-c","copy",str(output)])
    else: run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(manifest),"-ar","48000","-ac","1","-c:a","pcm_s16le",str(output)])


def ts(sec):
    ms=int(round(sec*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def make_srt(scenes,durations,path):
    lines=[]; offset=0.0; n=1
    for scene,dur in zip(scenes,durations):
        words=str(scene.get("narration","")).split()
        chunks=[words[i:i+6] for i in range(0,len(words),6)] or [[""]]
        cursor=offset
        for ch in chunks:
            part=dur/max(1,len(chunks)); end=min(offset+dur,cursor+part)
            lines += [str(n),f"{ts(cursor)} --> {ts(end)}"," ".join(ch),""]
            n+=1; cursor=end
        offset += dur
    path.write_text("\n".join(lines),encoding="utf-8")


def music_track(total, style, path):
    if style == "off": return None
    sr=48000; n=int(total*sr); t=np.arange(n,dtype=np.float32)/sr
    configs={"viral-pulse":(104,220.0),"cinematic-rise":(76,146.8),"mystery-tension":(68,110.0),"emotional-ambient":(64,174.6),"epic-ancient":(82,130.8)}
    bpm,freq=configs.get(style,(72,146.8)); audio=np.zeros(n,dtype=np.float32)
    audio += .08*np.sin(2*np.pi*freq*t) + .035*np.sin(2*np.pi*freq*1.5*t)
    beat=max(1,int(sr*60/bpm))
    for start in range(0,n,beat):
        length=min(int(.11*sr),n-start); env=np.linspace(1,0,length,dtype=np.float32)
        audio[start:start+length] += .13*np.sin(2*np.pi*55*np.arange(length)/sr)*env
    audio=np.tanh(audio*1.4).astype(np.float32)
    sf.write(path,audio,sr)
    return path


def main():
    plan=json.loads(os.environ["INPUT_PLAN_JSON"])
    scenes=plan.get("scenes") or []
    if len(scenes)<6: raise RuntimeError("plano com poucas cenas")
    style=os.getenv("INPUT_CARTOON_STYLE","classic-2d")
    niche=os.getenv("INPUT_NICHE_KEY","custom")
    captions=os.getenv("INPUT_CAPTIONS","on")
    music=os.getenv("INPUT_MUSIC","off")
    volume={"low":"0.08","medium":"0.13","high":"0.18"}.get(os.getenv("INPUT_MUSIC_VOLUME","medium"),"0.13")

    voices=[]; clips=[]; durations=[]; visual_sources=[]
    for i,scene in enumerate(scenes):
        text=str(scene.get("narration") or "").strip()
        if not text: raise RuntimeError(f"cena {i+1} sem narração")
        wav=synthesize(text,i); dur=duration(wav); voices.append(wav); durations.append(dur)
        img=WORK/f"cartoon_{i:02d}.jpg"
        source=ai_cartoon_scene(scene,img,style,niche,i); visual_sources.append(source)
        clip=WORK/f"scene_{i:02d}.mp4"; render_image(img,clip,dur,i); clips.append(clip)

    video=WORK/"video.mp4"; narration=WORK/"narration.wav"
    concat(clips,"video",video); concat(voices,"audio",narration)
    total=duration(narration)
    srt=WORK/"captions.srt"; make_srt(scenes,durations,srt)
    bgm=music_track(total,music,WORK/"music.wav")

    final=OUT/"final.mp4"
    vf=[]
    if captions=="on": vf=["-vf",f"subtitles={srt}:force_style='FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=110'"]
    if bgm:
        run(["ffmpeg","-y","-i",str(video),"-i",str(narration),"-i",str(bgm),"-filter_complex",f"[1:a]volume=1.0[v];[2:a]volume={volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]",*vf,"-map","0:v","-map","[a]","-c:v","libx264","-preset","veryfast","-crf","22","-c:a","aac","-b:a","192k","-shortest",str(final)])
    else:
        run(["ffmpeg","-y","-i",str(video),"-i",str(narration),*vf,"-map","0:v","-map","1:a","-c:v","libx264","-preset","veryfast","-crf","22","-c:a","aac","-b:a","192k","-shortest",str(final)])

    meta={"title":plan.get("title") or os.getenv("INPUT_TOPIC","Short Turbo"),"summary":plan.get("summary","") ,"visual_mode":"100% cartoon","cartoon_style":style,"scene_sources":visual_sources,"duration_seconds":round(duration(final),2),"engine":"Shorts Cloud Studio Turbo v2 / MPT-inspired pipeline"}
    (OUT/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    if not final.exists() or final.stat().st_size<500000: raise RuntimeError("MP4 final inválido")
    print(json.dumps(meta,ensure_ascii=False),flush=True)

if __name__=="__main__": main()
