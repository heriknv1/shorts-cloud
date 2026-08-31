#!/usr/bin/env python3
from pathlib import Path

required_files=[
    Path('scripts/generate_turbo_v2.py'),
    Path('scripts/visual_engine.py'),
    Path('scripts/validate_religious_media.py'),
]
missing=[str(p) for p in required_files if not p.exists()]
if missing:
    raise SystemExit('Arquivos obrigatórios ausentes: '+', '.join(missing))

generator=Path('scripts/generate_turbo_v2.py').read_text(encoding='utf-8')
visual=Path('scripts/visual_engine.py').read_text(encoding='utf-8')
checks={
    'legendas 1080x1920':['PlayResX: 1080','PlayResY: 1920','margin_v=140'],
    'voz natural':['pt-BR-FranciscaNeural',"'default':'+0%'",'polish_voice'],
    'motor visual':['generate_scene_image','generated-primary','stock_queries'],
    'política religiosa':['BLOCKED_RX','scene_is_religious'],
}
missing_rules=[]
for label,needles in checks.items():
    haystack=generator+'\n'+visual
    if not all(n in haystack for n in needles):
        missing_rules.append(label)
if missing_rules:
    raise SystemExit('Políticas obrigatórias ausentes: '+', '.join(missing_rules))
print('Motor visual, voz e políticas validados com sucesso.',flush=True)
