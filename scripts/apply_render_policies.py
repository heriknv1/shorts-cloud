#!/usr/bin/env python3
from pathlib import Path

required_files=[
    Path('scripts/generate_turbo_v2.py'),
    Path('scripts/generate_entry.py'),
    Path('scripts/visual_engine.py'),
    Path('scripts/flux_runtime.py'),
    Path('scripts/natural_voice.py'),
    Path('scripts/voice_speed_runtime.py'),
    Path('scripts/media_history.py'),
    Path('scripts/dynamic_finish.py'),
    Path('scripts/validate_religious_media.py'),
]
missing=[str(p) for p in required_files if not p.exists()]
if missing:
    raise SystemExit('Arquivos obrigatórios ausentes: '+', '.join(missing))

generator=Path('scripts/generate_turbo_v2.py').read_text(encoding='utf-8')
entry=Path('scripts/generate_entry.py').read_text(encoding='utf-8')
visual=Path('scripts/visual_engine.py').read_text(encoding='utf-8')
flux=Path('scripts/flux_runtime.py').read_text(encoding='utf-8')
voice=Path('scripts/natural_voice.py').read_text(encoding='utf-8')
voice_speed=Path('scripts/voice_speed_runtime.py').read_text(encoding='utf-8')
media=Path('scripts/media_history.py').read_text(encoding='utf-8')
finish=Path('scripts/dynamic_finish.py').read_text(encoding='utf-8')
haystack='\n'.join([generator,entry,visual,flux,voice,voice_speed,media,finish])
checks={
    'legendas 1080x1920':['PlayResX: 1080','PlayResY: 1920','margin_v=140'],
    'narração natural':['GEMINI_API_KEY','gemini-3.1-flash-tts-preview','edge_voice','piper_voice','director_prompt','1.05','1.10'],
    'motor visual':['flux-2-klein-4b','flux-1-schnell','generate_scene_image','stock_queries'],
    'referência visual':['INPUT_REFERENCE_IMAGE_B64','strict_reference_image','input_image_0'],
    'mídia inédita':['MEDIA_USAGE_B64','PHOTO_IDS','VIDEO_IDS','media_history.install','fresh-take-'],
    'edição dinâmica':['INPUT_EDITING_PACE','INPUT_SFX_MODE','INPUT_AMBIENCE_MODE','captions.srt','final_sem_legenda.mp4'],
    'política religiosa':['BLOCKED_RX','scene_is_religious'],
}
missing_rules=[]
for label,needles in checks.items():
    if not all(n in haystack for n in needles):
        missing_rules.append(label)
if missing_rules:
    raise SystemExit('Políticas obrigatórias ausentes: '+', '.join(missing_rules))
print('Motores visuais, narração, originalidade e acabamento dinâmico validados com sucesso.',flush=True)
