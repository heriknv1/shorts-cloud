#!/usr/bin/env python3
"""Teste de ponta a ponta do renderizador, sem uploads nem chaves reais."""
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import scale_render

def main():
    source = ROOT / 'work_scale_test_source.mp4'
    subprocess.run([
        'ffmpeg','-hide_banner','-loglevel','error','-y',
        '-f','lavfi','-i','testsrc2=size=360x640:rate=12',
        '-f','lavfi','-i','sine=frequency=440:sample_rate=44100',
        '-t','2.5','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(source)
    ], check=True)
    payload = {
        'titles':['Um titulo bem importante para a noticia','Outro teste com simbolos: 50% e ?!'],
        'template':'news','framing':'fill','text_size':'medium','accent':'#916bff',
        'start_at':0,'end_at':2.3,'topic':'Teste de geração vertical'
    }
    with patch.object(scale_render,'load_secure_payload',return_value=payload), \
         patch.object(scale_render,'source_file',return_value=source):
        scale_render.main()
    out = ROOT / 'output' / 'scale_batch'
    assert (out / 'scale_01.mp4').is_file()
    assert (out / 'scale_02.mp4').is_file()
    metadata = scale_render.probe(out / 'scale_01.mp4')
    visual = next(s for s in metadata['streams'] if s['codec_type']=='video')
    assert (int(visual['width']),int(visual['height']))==(1080,1920)
    assert any(s['codec_type']=='audio' for s in metadata['streams'])
    print('Studio Scale render smoke: PASS')

if __name__ == '__main__':
    main()
