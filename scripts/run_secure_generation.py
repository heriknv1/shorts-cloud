#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

from secure_workflow_payload import load_secure_payload

ROOT=Path(__file__).resolve().parents[1]

FIELD_TO_ENV={
    'topic':'INPUT_TOPIC','plan_json':'INPUT_PLAN_JSON','duration':'INPUT_DURATION','tone':'INPUT_TONE',
    'niche_key':'INPUT_NICHE_KEY','visual_style':'INPUT_VISUAL_STYLE','cartoon_style':'INPUT_CARTOON_STYLE',
    'media_mode':'INPUT_MEDIA_MODE','media_source':'INPUT_MEDIA_SOURCE','reference_image_b64':'INPUT_REFERENCE_IMAGE_B64',
    'source_url':'INPUT_SOURCE_URL','source_kind':'INPUT_SOURCE_KIND','source_mime':'INPUT_SOURCE_MIME',
    'doodle_style':'INPUT_DOODLE_STYLE','voice':'INPUT_VOICE','voice_pitch':'INPUT_VOICE_PITCH',
    'voice_speed':'INPUT_VOICE_SPEED','captions':'INPUT_CAPTIONS','caption_font':'INPUT_CAPTION_FONT',
    'caption_size':'INPUT_CAPTION_SIZE','music':'INPUT_MUSIC','music_volume':'INPUT_MUSIC_VOLUME',
    'editing_pace':'INPUT_EDITING_PACE','sfx_mode':'INPUT_SFX_MODE','ambience_mode':'INPUT_AMBIENCE_MODE',
    'clean_export':'INPUT_CLEAN_EXPORT','branding_mode':'INPUT_BRANDING_MODE','brand_text':'INPUT_BRAND_TEXT',
    'request_id':'INPUT_REQUEST_ID',
}

MAX_LENGTHS={'plan_json':60000,'reference_image_b64':33000,'source_url':2200,'topic':4000,'brand_text':80}

def command(script,env):
    print(f'Executando etapa protegida: {Path(script).name}',flush=True)
    subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,env=env,check=True)

def protected_environment(payload):
    env=os.environ.copy()
    for field,target in FIELD_TO_ENV.items():
        value=payload.get(field,'')
        if isinstance(value,(dict,list)):value=json.dumps(value,ensure_ascii=False,separators=(',',':'))
        value=str(value)
        if len(value)>MAX_LENGTHS.get(field,4000):raise RuntimeError(f'Campo protegido inválido: {field}.')
        env[target]=value
    try:
        plan=json.loads(env['INPUT_PLAN_JSON'])
    except Exception as exc:
        raise RuntimeError('O plano protegido desta geração é inválido.') from exc
    if not isinstance(plan,dict) or not isinstance(plan.get('scenes'),list):raise RuntimeError('O plano protegido não contém cenas válidas.')
    return env

def generate(env):
    niche=env.get('INPUT_NICHE_KEY','custom')
    if niche=='audio-illustrated':
        command('scripts/generate_audio_illustrated.py',env)
        return
    for script in ('scripts/apply_render_policies.py','scripts/generate_entry.py','scripts/validate_religious_media.py','scripts/normalize_duration.py'):
        command(script,env)

def finish(env):
    if env.get('INPUT_NICHE_KEY')!='audio-illustrated':
        command('scripts/dynamic_finish.py',env)
        command('scripts/normalize_duration.py',env)
    command('scripts/prepare_output_name.py',env)

def validate(env):
    name_file=ROOT/'output'/'video_name.txt'
    if not name_file.is_file():raise RuntimeError('Nome do vídeo final ausente.')
    video=ROOT/'output'/name_file.read_text(encoding='utf-8').strip()
    if not video.is_file() or video.stat().st_size<1:raise RuntimeError('Vídeo final ausente.')
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)],text=True))
    streams=data.get('streams') or [];visual=next((s for s in streams if s.get('codec_type')=='video'),None);audio=next((s for s in streams if s.get('codec_type')=='audio'),None)
    duration=float(data.get('format',{}).get('duration') or 0);target=float(env['INPUT_DURATION'])
    if not visual or int(visual.get('width',0))!=1080 or int(visual.get('height',0))!=1920:raise RuntimeError('Resolução final inválida.')
    if visual.get('pix_fmt')!='yuv420p':raise RuntimeError(f"Formato de cor incompatível: {visual.get('pix_fmt')}")
    if not audio:raise RuntimeError('Áudio final ausente.')
    if abs(duration-target)>.75:raise RuntimeError(f'Duração final inválida: {duration:.2f}s')
    minimum=150000 if env.get('INPUT_NICHE_KEY')=='audio-illustrated' else 500000
    if int(data.get('format',{}).get('size') or 0)<minimum:raise RuntimeError('Arquivo final pequeno demais.')
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
    print(f'Vídeo validado: 1080x1920, {duration:.2f}s, áudio presente.',flush=True)

def main():
    phase=sys.argv[1] if len(sys.argv)>1 else ''
    if phase not in {'generate','finish','validate'}:raise RuntimeError('Fase protegida inválida.')
    env=protected_environment(load_secure_payload())
    {'generate':generate,'finish':finish,'validate':validate}[phase](env)

if __name__=='__main__':main()
