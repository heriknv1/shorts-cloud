#!/usr/bin/env python3
from pathlib import Path
import os, subprocess, json

src=Path('output/final.mp4')
if not src.exists(): raise SystemExit('Vídeo final ausente')
target=float(os.getenv('INPUT_DURATION','65'))
probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(src)],text=True).strip()
current=float(probe)
if current<=0: raise SystemExit('Duração inválida')
if abs(current-target)<=0.35:
    print(f'duration ok: {current:.2f}s')
    raise SystemExit(0)
ratio=current/target
if ratio<0.5 or ratio>2.0: raise SystemExit(f'Duração fora de faixa segura: {current:.2f}s para alvo {target:.2f}s')
# atempo accepts 0.5..2.0; video PTS factor is target/current.
tmp=src.with_name('final_duration_fixed.mp4')
cmd=['ffmpeg','-y','-i',str(src),'-filter_complex',f'[0:v]setpts={target/current:.8f}*PTS[v];[0:a]atempo={ratio:.8f}[a]','-map','[v]','-map','[a]','-t',f'{target:.3f}','-c:v','libx264','-preset','veryfast','-crf','22','-c:a','aac','-b:a','192k','-movflags','+faststart',str(tmp)]
subprocess.run(cmd,check=True)
tmp.replace(src)
print(json.dumps({'before':current,'target':target},ensure_ascii=False))