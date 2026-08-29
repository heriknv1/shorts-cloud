#!/usr/bin/env python3
import json
import math
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from urllib.parse import quote_plus

import requests

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
OUT = ROOT / "output"
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
VOICE = os.getenv("PIPER_VOICE", "pt_BR-faber-medium")
VOICE_MODEL = os.getenv("PIPER_MODEL_PATH", VOICE)


def run(cmd, *, stdin=None):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, input=stdin, check=True)


def probe_duration(path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("IA não retornou JSON.")
    return json.loads(match.group(0))


def create_plan(topic, duration, style):
    prompt = f"""
Você é roteirista de vídeos verticais em português do Brasil. Crie um Short original, com narrativa humana e forte retenção.
Tema: {topic}
Duração alvo: {duration} segundos
Estilo: {style}

REGRAS IMPORTANTES:
- Escreva uma narração natural em PT-BR com aproximadamente {max(125, int(duration * 2.25))} a {int(duration * 2.55)} palavras.
- Comece com um gancho que desperte curiosidade sem clickbait enganoso.
- Tenha começo, desenvolvimento e conclusão. Não produza texto genérico ou repetitivo.
- Para fatos religiosos/históricos, não invente citações, datas ou detalhes específicos quando não tiver certeza.
- Crie entre 8 e 10 cenas.
- Em cada cena, "query" deve ser uma busca VISUAL em INGLÊS adequada para encontrar vídeo stock no Pexels; use termos genéricos e filmáveis, nunca nomes bíblicos/personagens que provavelmente não existam no acervo.
- "caption" deve ter no máximo 7 palavras em PT-BR e resumir visualmente aquele momento.
- Título deve ser original e curto.
- Descrição com 1-2 frases.
- Hashtags: 4 a 7.

Retorne SOMENTE JSON válido:
{{
  "title": "...",
  "description": "...",
  "hashtags": ["#..."],
  "narration": "...",
  "scenes": [
    {{"query":"desert night cinematic","caption":"..."}}
  ]
}}
""".strip()

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "temperature": 0.85, "messages": [{"role": "user", "content": prompt}]},
        timeout=90,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    plan = extract_json(content)
    if not plan.get("narration") or not plan.get("scenes"):
        raise ValueError("Plano incompleto retornado pela IA.")
    plan["scenes"] = plan["scenes"][:10]
    if len(plan["scenes"]) < 6:
        raise ValueError("Poucas cenas retornadas pela IA.")
    return plan


def synthesize_voice(text):
    wav = WORK / "narration_raw.wav"
    run(["piper", "--model", VOICE_MODEL, "--output_file", str(wav)], stdin=text.encode("utf-8"))
    return wav


def fit_audio(raw_wav, target):
    actual = probe_duration(raw_wav)
    tempo = actual / target
    # atempo aceita 0.5..2.0; esse clamp evita um roteiro anormal destruir o render.
    tempo = max(0.72, min(1.35, tempo))
    fitted = WORK / "narration.wav"
    run(["ffmpeg", "-y", "-i", str(raw_wav), "-filter:a", f"atempo={tempo:.5f}", "-t", f"{target:.3f}", str(fitted)])
    return fitted


def pexels_video(query, used_ids):
    url = f"https://api.pexels.com/videos/search?query={quote_plus(query)}&orientation=portrait&per_page=12"
    r = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=40)
    r.raise_for_status()
    videos = r.json().get("videos", [])
    for video in videos:
        if video.get("id") in used_ids:
            continue
        files = video.get("video_files", [])
        candidates = [f for f in files if f.get("link") and f.get("width") and f.get("height")]
        candidates.sort(key=lambda f: (abs((f.get("height", 0) / max(f.get("width", 1), 1)) - (16/9)), abs(f.get("width", 0) - 1080)))
        if candidates:
            used_ids.add(video.get("id"))
            return video.get("id"), candidates[0]["link"]
    return None, None


def download(url, path):
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def create_fallback_clip(path, duration, index):
    # Fundo abstrato simples, usado somente se o Pexels não retornar material.
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"color=c=0x10131a:s=1080x1920:r=30:d={duration}",
        "-vf", f"drawtext=text='Cena {index+1}':fontcolor=white:fontsize=58:x=(w-text_w)/2:y=(h-text_h)/2",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", str(path)
    ])


def render_scene(src, dst, duration, index):
    fade_out = max(0.0, duration - 0.22)
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,fps=30,"
        f"fade=t=in:st=0:d=0.18,fade=t=out:st={fade_out:.3f}:d=0.18"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src), "-t", f"{duration:.3f}",
        "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-pix_fmt", "yuv420p", str(dst)
    ])


def srt_time(seconds):
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def make_srt(text, total_duration, path):
    words = text.split()
    chunks, current = [], []
    for word in words:
        current.append(word)
        if len(current) >= 6 or (len(current) >= 4 and re.search(r"[.!?]$", word)):
            chunks.append(current); current = []
    if current: chunks.append(current)
    total_words = max(1, sum(len(c) for c in chunks))
    cursor = 0.0
    lines = []
    for i, chunk in enumerate(chunks, 1):
        dur = total_duration * len(chunk) / total_words
        start, end = cursor, min(total_duration, cursor + dur)
        lines.extend([str(i), f"{srt_time(start)} --> {srt_time(end)}", " ".join(chunk), ""])
        cursor = end
    path.write_text("\n".join(lines), encoding="utf-8")


def concat_scenes(scene_files):
    manifest = WORK / "concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in scene_files), encoding="utf-8")
    merged = WORK / "video_no_audio.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(manifest), "-c", "copy", str(merged)])
    return merged


def final_render(video, audio, srt, target):
    out = OUT / "final.mp4"
    srt_escaped = str(srt.resolve()).replace("'", "'\\''").replace(":", "\\:")
    subtitle_filter = (
        f"subtitles='{srt_escaped}':force_style='FontName=DejaVu Sans,FontSize=21,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=3,Shadow=1,"
        "Alignment=2,MarginV=170,Bold=1'"
    )
    run([
        "ffmpeg", "-y", "-i", str(video), "-i", str(audio), "-t", f"{target:.3f}",
        "-vf", subtitle_filter, "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-c:a", "aac", "-b:a", "160k", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)
    ])
    return out


def main():
    if len(sys.argv) < 4:
        print("Uso: generate_short.py <tema> <duracao> <estilo>", file=sys.stderr)
        return 2
    topic = sys.argv[1].strip()
    target = min(70.0, max(60.0, float(sys.argv[2])))
    style = sys.argv[3].strip()

    print(f"Gerando roteiro: {topic}", flush=True)
    plan = create_plan(topic, int(target), style)
    raw = synthesize_voice(plan["narration"])
    audio = fit_audio(raw, target)

    scenes = plan["scenes"]
    scene_duration = target / len(scenes)
    used_ids = set()
    scene_files = []
    pexels_credits = []

    for idx, scene in enumerate(scenes):
        query = str(scene.get("query") or "cinematic nature").strip()
        print(f"Cena {idx+1}/{len(scenes)}: {query}", flush=True)
        vid, url = pexels_video(query, used_ids)
        rendered = WORK / f"scene_{idx:02d}.mp4"
        if url:
            src = WORK / f"source_{idx:02d}.mp4"
            download(url, src)
            render_scene(src, rendered, scene_duration, idx)
            pexels_credits.append({"id": vid, "query": query})
        else:
            create_fallback_clip(rendered, scene_duration, idx)
        scene_files.append(rendered)

    merged = concat_scenes(scene_files)
    srt = WORK / "subtitles.srt"
    make_srt(plan["narration"], target, srt)
    final = final_render(merged, audio, srt, target)

    metadata = {
        "topic": topic,
        "duration_target": target,
        "duration_final": round(probe_duration(final), 3),
        "style": style,
        "title": plan.get("title", topic),
        "description": plan.get("description", ""),
        "hashtags": plan.get("hashtags", []),
        "narration": plan.get("narration", ""),
        "scenes": scenes,
        "pexels": pexels_credits,
        "model": GROQ_MODEL,
        "voice": VOICE,
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "file": str(final), "title": metadata["title"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
