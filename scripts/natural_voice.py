#!/usr/bin/env python3
import base64
import os
import re
import subprocess
import time
import wave
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work_turbo'
WORK.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GEMINI_TTS_MODEL = os.getenv('GEMINI_TTS_MODEL', 'gemini-3.1-flash-tts-preview').strip() or 'gemini-3.1-flash-tts-preview'
PIPER_MODEL = os.getenv('PIPER_MODEL_PATH', 'models/pt_BR-faber-medium.onnx')

VOICE_PROFILES = {
    'pt-BR-AntonioNeural': ('Gacrux', 'pt-BR-AntonioNeural', 'mature, grounded, trustworthy and warm'),
    'pt-BR-FranciscaNeural': ('Sulafat', 'pt-BR-FranciscaNeural', 'warm, empathetic, expressive and clear'),
    'pt-BR-ThalitaNeural': ('Achernar', 'pt-BR-ThalitaNeural', 'soft, intimate, clear and natural'),
}

def run(cmd, stdin=None, quiet=False):
    if not quiet:
        print('+', ' '.join(map(str, cmd)), flush=True)
    kw = {'check': True}
    if stdin is not None:
        kw['input'] = stdin
    if quiet:
        kw.update(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.run(cmd, **kw)

def duration(path):
    p = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
        capture_output=True, text=True, check=True
    )
    return float(p.stdout.strip())

def voice_settings():
    pitch_mode = os.getenv('INPUT_VOICE_PITCH', 'default')
    speed_mode = os.getenv('INPUT_VOICE_SPEED', 'default')
    pitch = {'low': '-7Hz', 'default': '+0Hz', 'high': '+7Hz'}.get(pitch_mode, '+0Hz')
    rate = {'slow': '-8%', 'default': '+0%', 'fast': '+7%'}.get(speed_mode, '+0%')
    return pitch_mode, speed_mode, pitch, rate

def naturalize_speech_text(text):
    text = str(text or '').strip()
    text = text.replace('—', ', ').replace('–', ', ')
    text = re.sub(r'\s*;\s*', ', ', text)
    text = re.sub(r'\s*:\s*', ': ', text)
    text = re.sub(r'\s+', ' ', text)
    if text and text[-1] not in '.!?':
        text += '.'
    return text

def selected_profile():
    requested = os.getenv('INPUT_VOICE', 'pt-BR-FranciscaNeural')
    gemini_voice, edge_voice, profile = VOICE_PROFILES.get(
        requested, VOICE_PROFILES['pt-BR-FranciscaNeural']
    )
    override = os.getenv('GEMINI_TTS_VOICE', '').strip()
    if override:
        gemini_voice = override
    return gemini_voice, edge_voice, profile

def director_prompt(spoken):
    pitch_mode, speed_mode, _, _ = voice_settings()
    tone = os.getenv('INPUT_TONE', 'cinematic').strip().lower()
    niche = os.getenv('INPUT_NICHE_KEY', 'custom').strip().lower()
    _, _, profile = selected_profile()

    pace = {
        'slow': 'measured and calm, with natural pauses but never dragging',
        'default': 'natural conversational pacing, fluid and human',
        'fast': 'brisk and engaging, while remaining perfectly clear',
    }.get(speed_mode, 'natural conversational pacing, fluid and human')

    register = {
        'low': 'slightly lower vocal register, relaxed and resonant, never artificially pitched',
        'default': 'comfortable neutral vocal register',
        'high': 'slightly brighter vocal register, still natural and relaxed',
    }.get(pitch_mode, 'comfortable neutral vocal register')

    mood = {
        'cinematic': 'cinematic, intimate and emotionally engaging without sounding theatrical',
        'documentary': 'credible, informative and conversational, like a premium documentary narrator',
        'dramatic': 'emotionally present and dramatic with restraint, never exaggerated',
        'energetic': 'energetic and charismatic without shouting or sounding like an advertisement',
    }.get(tone, 'natural, engaging and conversational')

    context = (
        'For biblical or devotional content, sound reverent, sincere and warm, with respectful emphasis.'
        if niche in {'biblical', 'devotional'}
        else 'Match the emotion of the text naturally and avoid repetitive sing-song cadence.'
    )

    return f"""Synthesize natural human speech in Brazilian Portuguese (pt-BR).
Speak ONLY the transcript between TRANSCRIPT BEGIN and TRANSCRIPT END. Never read these directions aloud.

AUDIO PROFILE:
A professional short-form narrator with a {profile} voice.

DIRECTOR'S NOTES:
- Accent: neutral Brazilian Portuguese.
- Delivery: {mood}.
- Pace: {pace}.
- Vocal register: {register}.
- Use subtle breaths and micro-pauses suggested by punctuation.
- Vary emphasis naturally. Avoid robotic cadence, announcer voice, excessive pauses and word-by-word delivery.
- Keep pronunciation crisp while preserving spontaneous human rhythm.
- {context}

TRANSCRIPT BEGIN
{spoken}
TRANSCRIPT END"""

def polish_voice(src, dst):
    filters = (
        'highpass=f=65,lowpass=f=13500,'
        'acompressor=threshold=-20dB:ratio=1.45:attack=30:release=260:makeup=1.12,'
        'alimiter=limit=0.95'
    )
    run([
        'ffmpeg', '-y', '-i', str(src), '-af', filters,
        '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(dst)
    ], quiet=True)

def postprocess_fallback_voice(src, dst):
    pitch_mode, speed_mode, _, _ = voice_settings()
    tempo = {'slow': 0.94, 'default': 1.0, 'fast': 1.06}.get(speed_mode, 1.0)
    ratio = {'low': 0.97, 'default': 1.0, 'high': 1.03}.get(pitch_mode, 1.0)
    filters = []
    if abs(ratio - 1.0) > .001:
        filters += [f'asetrate=48000*{ratio:.4f}', 'aresample=48000', f'atempo={1/ratio:.4f}']
    if abs(tempo - 1.0) > .001:
        filters.append(f'atempo={tempo:.4f}')
    filters += [
        'highpass=f=65', 'lowpass=f=12500',
        'acompressor=threshold=-19dB:ratio=1.5:attack=28:release=240',
        'alimiter=limit=0.95'
    ]
    run([
        'ffmpeg', '-y', '-i', str(src), '-af', ','.join(filters),
        '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(dst)
    ], quiet=True)

def _extract_audio_b64(data):
    try:
        parts = data['candidates'][0]['content']['parts']
    except (KeyError, IndexError, TypeError):
        return None
    for part in parts:
        inline = part.get('inlineData') or part.get('inline_data') or {}
        encoded = inline.get('data')
        if encoded:
            return encoded
    return None

def gemini_voice(spoken, idx, wav):
    if not GEMINI_API_KEY:
        return False

    gemini_voice_name, _, _ = selected_profile()
    url = (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{GEMINI_TTS_MODEL}:generateContent'
    )
    payload = {
        'contents': [{'parts': [{'text': director_prompt(spoken)}]}],
        'generationConfig': {
            'responseModalities': ['AUDIO'],
            'speechConfig': {
                'languageCode': 'pt-BR',
                'voiceConfig': {
                    'prebuiltVoiceConfig': {'voiceName': gemini_voice_name}
                }
            }
        }
    }
    headers = {
        'x-goog-api-key': GEMINI_API_KEY,
        'Content-Type': 'application/json',
    }
    rawwav = WORK / f'voice_natural_raw_{idx:02d}.wav'

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.RequestException:
            response = None

        if response is None or response.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 + attempt * 3)
            continue
        if not response.ok:
            return False
        try:
            encoded = _extract_audio_b64(response.json())
            if not encoded:
                raise ValueError('audio ausente')
            pcm = base64.b64decode(encoded)
            if len(pcm) < 4000:
                raise ValueError('audio curto')
            with wave.open(str(rawwav), 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(pcm)
            polish_voice(rawwav, wav)
            if not wav.exists() or wav.stat().st_size < 8000 or duration(wav) < .3:
                raise ValueError('audio inválido')
            return True
        except Exception:
            time.sleep(1 + attempt)
    return False

def edge_voice(spoken, idx, wav):
    _, edge_voice_name, _ = selected_profile()
    _, _, pitch, rate = voice_settings()
    mp3 = WORK / f'voice_edge_{idx:02d}.mp3'
    rawwav = WORK / f'voice_edge_raw_{idx:02d}.wav'
    run([
        'edge-tts', '--voice', edge_voice_name, f'--rate={rate}', f'--pitch={pitch}',
        '--text', spoken, '--write-media', str(mp3)
    ])
    if not mp3.exists() or mp3.stat().st_size < 1000:
        raise RuntimeError('voz neural inválida')
    run([
        'ffmpeg', '-y', '-i', str(mp3), '-ar', '48000', '-ac', '1',
        '-c:a', 'pcm_s16le', str(rawwav)
    ], quiet=True)
    polish_voice(rawwav, wav)
    if duration(wav) < .3:
        raise RuntimeError('áudio curto demais')

def piper_voice(spoken, idx, wav):
    piper_raw = WORK / f'voice_piper_{idx:02d}.wav'
    run(['piper', '--model', PIPER_MODEL, '--output_file', str(piper_raw)],
        stdin=spoken.encode('utf-8'))
    postprocess_fallback_voice(piper_raw, wav)

def synthesize(text, idx):
    spoken = naturalize_speech_text(text)
    wav = WORK / f'voice_{idx:02d}.wav'

    if gemini_voice(spoken, idx, wav):
        print(f'Cena {idx+1}: narração natural gerada.', flush=True)
        return wav, 'neural'

    try:
        print(f'Cena {idx+1}: usando narração neural alternativa.', flush=True)
        edge_voice(spoken, idx, wav)
        return wav, 'neural-fallback'
    except Exception:
        print(f'Cena {idx+1}: usando voz de segurança.', flush=True)
        piper_voice(spoken, idx, wav)
        return wav, 'voice-fallback'
