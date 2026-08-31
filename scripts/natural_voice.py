#!/usr/bin/env python3
import base64
import os
import re
import subprocess
import time
import wave
from pathlib import Path

from google import genai

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work_turbo'
WORK.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GEMINI_TTS_MODEL = os.getenv('GEMINI_TTS_MODEL', 'gemini-3.1-flash-tts-preview').strip() or 'gemini-3.1-flash-tts-preview'
PIPER_MODEL = os.getenv('PIPER_MODEL_PATH', 'models/pt_BR-faber-medium.onnx')

VOICE_PROFILES = {
    'gemini:GacruxDeep': ('Gacrux', 'pt-BR-AntonioNeural', 'deep masculine, warm, resonant, mature, cinematic and convincingly human'),
    'gemini:Gacrux': ('Gacrux', 'pt-BR-AntonioNeural', 'mature, grounded, trustworthy and warm'),
    'gemini:Sulafat': ('Sulafat', 'pt-BR-FranciscaNeural', 'warm, empathetic, expressive and natural'),
    'gemini:Achernar': ('Achernar', 'pt-BR-ThalitaNeural', 'soft, intimate, gentle and natural'),
    'gemini:Charon': ('Charon', 'pt-BR-AntonioNeural', 'informative, composed, clear and documentary-like'),
    'gemini:Kore': ('Kore', 'pt-BR-FranciscaNeural', 'firm, confident, focused and expressive'),
    'gemini:Puck': ('Puck', 'pt-BR-ThalitaNeural', 'upbeat, lively, engaging and energetic'),
    'pt-BR-AntonioNeural': ('Gacrux', 'pt-BR-AntonioNeural', 'mature, grounded, trustworthy and warm'),
    'pt-BR-FranciscaNeural': ('Sulafat', 'pt-BR-FranciscaNeural', 'warm, empathetic, expressive and natural'),
    'pt-BR-ThalitaNeural': ('Achernar', 'pt-BR-ThalitaNeural', 'soft, intimate, gentle and natural'),
}
DEFAULT_VOICE = 'gemini:Sulafat'

def run(cmd, stdin=None, quiet=False):
    if not quiet:
        print('+', ' '.join(map(str, cmd)), flush=True)
    kw = {'check': True}
    if stdin is not None: kw['input'] = stdin
    if quiet: kw.update(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.run(cmd, **kw)

def duration(path):
    p = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True,check=True)
    return float(p.stdout.strip())

def voice_settings():
    requested=os.getenv('INPUT_VOICE','')
    pitch_mode=os.getenv('INPUT_VOICE_PITCH','default')
    speed_mode=os.getenv('INPUT_VOICE_SPEED','default')
    if speed_mode not in {'default','fast','veryfast'}: speed_mode='default'
    if requested=='gemini:GacruxDeep': pitch_mode='low'
    pitch={'low':'-8Hz','default':'+0Hz','high':'+7Hz'}.get(pitch_mode,'+0Hz')
    edge_rate={'default':'+0%','fast':'+12%','veryfast':'+25%'}.get(speed_mode,'+0%')
    tempo={'default':1.0,'fast':1.12,'veryfast':1.25}.get(speed_mode,1.0)
    return pitch_mode,speed_mode,pitch,edge_rate,tempo

def naturalize_speech_text(text):
    text=str(text or '').strip().replace('—',', ').replace('–',', ')
    text=re.sub(r'\s*;\s*',', ',text); text=re.sub(r'\s*:\s*',': ',text); text=re.sub(r'\s+',' ',text)
    if text and text[-1] not in '.!?': text+='.'
    return text

def selected_profile():
    requested=os.getenv('INPUT_VOICE',DEFAULT_VOICE)
    gemini_voice,edge_voice,profile=VOICE_PROFILES.get(requested,VOICE_PROFILES[DEFAULT_VOICE])
    override=os.getenv('GEMINI_TTS_VOICE','').strip()
    if override: gemini_voice=override
    return gemini_voice,edge_voice,profile

def director_prompt(spoken):
    requested=os.getenv('INPUT_VOICE',DEFAULT_VOICE)
    pitch_mode,speed_mode,_,_,_=voice_settings(); tone=os.getenv('INPUT_TONE','cinematic').strip().lower(); niche=os.getenv('INPUT_NICHE_KEY','custom').strip().lower(); _,_,profile=selected_profile()
    pace={'default':'natural conversational pacing, fluid and human','fast':'noticeably faster than normal, energetic and fluid while keeping every word clear','veryfast':'very brisk short-form narration, approximately one quarter faster than normal, energetic but still natural and intelligible'}.get(speed_mode,'natural conversational pacing, fluid and human')
    register={'low':'lower masculine vocal register, full chest resonance and warm low-frequency presence, never artificially pitch-shifted','default':'comfortable neutral vocal register','high':'slightly brighter vocal register, still natural and relaxed'}.get(pitch_mode,'comfortable neutral vocal register')
    if requested=='gemini:GacruxDeep': register='distinctly deep adult male vocal register with rich chest resonance, calm authority, warmth and natural human texture; avoid synthetic bass, distortion or announcer-like delivery'
    mood={'cinematic':'cinematic, intimate and emotionally engaging without sounding theatrical','documentary':'credible, informative and conversational, like a premium documentary narrator','dramatic':'emotionally present and dramatic with restraint, never exaggerated','energetic':'energetic and charismatic without shouting or sounding like an advertisement'}.get(tone,'natural, engaging and conversational')
    if niche in {'biblical','devotional'}: context='For biblical or devotional content, sound reverent, sincere and warm, with respectful emphasis.'
    elif niche=='horror': context='For horror and suspense, build restrained tension with controlled pauses and subtle unease; never become cartoonish or overacted.'
    else: context='Match the emotion of the text naturally and avoid repetitive sing-song cadence.'
    return f'''Synthesize natural human speech in Brazilian Portuguese (pt-BR).
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
TRANSCRIPT END'''

def polish_voice(src,dst,apply_speed=True):
    _,speed_mode,_,_,tempo=voice_settings()
    filters=['highpass=f=65','lowpass=f=13500','acompressor=threshold=-20dB:ratio=1.45:attack=30:release=260:makeup=1.12']
    if apply_speed and speed_mode!='default': filters.append(f'atempo={tempo:.4f}')
    filters.append('alimiter=limit=0.95')
    run(['ffmpeg','-y','-i',str(src),'-af',','.join(filters),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(dst)],quiet=True)

def postprocess_fallback_voice(src,dst):
    requested=os.getenv('INPUT_VOICE','')
    pitch_mode,speed_mode,_,_,tempo=voice_settings(); ratio={'low':0.965,'default':1.0,'high':1.03}.get(pitch_mode,1.0); filters=[]
    if requested=='gemini:GacruxDeep': ratio=0.955
    if abs(ratio-1.0)>.001: filters += [f'asetrate=48000*{ratio:.4f}','aresample=48000',f'atempo={1/ratio:.4f}']
    if speed_mode!='default': filters.append(f'atempo={tempo:.4f}')
    filters += ['highpass=f=60','lowpass=f=12500','acompressor=threshold=-19dB:ratio=1.5:attack=28:release=240','alimiter=limit=0.95']
    run(['ffmpeg','-y','-i',str(src),'-af',','.join(filters),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(dst)],quiet=True)

def gemini_voice(spoken,idx,wav):
    if not GEMINI_API_KEY: return False
    gemini_voice_name,_,_=selected_profile(); rawwav=WORK/f'voice_natural_raw_{idx:02d}.wav'; client=genai.Client(api_key=GEMINI_API_KEY)
    for attempt in range(3):
        try:
            interaction=client.interactions.create(model=GEMINI_TTS_MODEL,input=director_prompt(spoken),response_format={'type':'audio'},generation_config={'speech_config':[{'voice':gemini_voice_name}]})
            audio=getattr(interaction,'output_audio',None); encoded=getattr(audio,'data',None) if audio else None
            if not encoded: raise RuntimeError('audio ausente')
            pcm=base64.b64decode(encoded)
            if len(pcm)<4000: raise RuntimeError('audio curto')
            with wave.open(str(rawwav),'wb') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000); wf.writeframes(pcm)
            # Gemini receives pacing direction and we also enforce the selected speed in post-processing.
            polish_voice(rawwav,wav,apply_speed=True)
            if not wav.exists() or wav.stat().st_size<8000 or duration(wav)<.3: raise RuntimeError('audio inválido')
            return True
        except Exception:
            print(f'Cena {idx+1}: tentativa de narração natural {attempt+1} indisponível.',flush=True)
            if attempt<2: time.sleep(2+attempt*3)
    return False

def edge_voice(spoken,idx,wav):
    _,edge_voice_name,_=selected_profile(); _,_,pitch,rate,_=voice_settings(); mp3=WORK/f'voice_edge_{idx:02d}.mp3'; rawwav=WORK/f'voice_edge_raw_{idx:02d}.wav'
    run(['edge-tts','--voice',edge_voice_name,f'--rate={rate}',f'--pitch={pitch}','--text',spoken,'--write-media',str(mp3)])
    if not mp3.exists() or mp3.stat().st_size<1000: raise RuntimeError('voz neural inválida')
    run(['ffmpeg','-y','-i',str(mp3),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(rawwav)],quiet=True)
    # Edge already applies the speed above; polish without applying tempo a second time.
    polish_voice(rawwav,wav,apply_speed=False)
    if duration(wav)<.3: raise RuntimeError('áudio curto demais')

def piper_voice(spoken,idx,wav):
    piper_raw=WORK/f'voice_piper_{idx:02d}.wav'; run(['piper','--model',PIPER_MODEL,'--output_file',str(piper_raw)],stdin=spoken.encode('utf-8')); postprocess_fallback_voice(piper_raw,wav)

def synthesize(text,idx):
    spoken=naturalize_speech_text(text); wav=WORK/f'voice_{idx:02d}.wav'
    if gemini_voice(spoken,idx,wav):
        print(f'Cena {idx+1}: narração natural gerada.',flush=True); return wav,'neural'
    try:
        print(f'Cena {idx+1}: usando narração neural alternativa.',flush=True); edge_voice(spoken,idx,wav); return wav,'neural-fallback'
    except Exception:
        print(f'Cena {idx+1}: usando voz de segurança.',flush=True); piper_voice(spoken,idx,wav); return wav,'voice-fallback'
