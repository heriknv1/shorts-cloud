#!/usr/bin/env python3
from pathlib import Path

path=Path('scripts/generate_turbo.py')
s=path.read_text(encoding='utf-8')

required={
    'legendas ASS 1080x1920':['def make_ass(','PlayResX: 1080','PlayResY: 1920',"vf=['-vf',f'ass={ass}']"],
    'tamanho e posição da legenda':['font_size=max(36,min(92','margin_v=140','caption_margin_bottom'],
    'busca religiosa segura':['def safe_scene_queries(','CATHOLIC_RX','GENERIC_RELIGIOUS_STOCK_RX'],
    'proteção visual religiosa':['def scene_is_religious(','unadorned setting']
}
missing=[]
for label,needles in required.items():
    if not all(needle in s for needle in needles):
        missing.append(label)
if missing:
    raise SystemExit('Políticas obrigatórias ausentes: '+', '.join(missing))
print('Políticas de renderização verificadas com sucesso')
