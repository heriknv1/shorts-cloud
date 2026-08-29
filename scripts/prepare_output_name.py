#!/usr/bin/env python3
from pathlib import Path
import json,re,shutil,unicodedata
out=Path('output')
meta=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
title=str(meta.get('title') or 'Video').strip()
base=unicodedata.normalize('NFKD',title).encode('ascii','ignore').decode('ascii')
base=re.sub(r'[^A-Za-z0-9 _-]+','',base)
base=re.sub(r'\s+',' ',base).strip(' ._-')[:100] or 'Video'
name=f'{base}.mp4'
src=out/'final.mp4'; dst=out/name
if dst!=src:
    shutil.copy2(src,dst)
(out/'video_name.txt').write_text(name,encoding='utf-8')
meta['download_filename']=name
(out/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(name)
