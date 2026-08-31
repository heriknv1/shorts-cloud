#!/usr/bin/env python3
import base64
import hashlib
import os
from pathlib import Path

from PIL import Image

import generate_turbo_v2 as turbo
import flux_runtime
import media_history
import natural_voice
import visual_engine
import voice_speed_runtime

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work_turbo'
WORK.mkdir(exist_ok=True)


def prepare_reference():
    encoded=os.getenv('INPUT_REFERENCE_IMAGE_B64','').strip()
    if not encoded:
        raise RuntimeError('Foto de referência ausente.')
    if len(encoded)>32000:
        raise RuntimeError('A foto de referência ficou grande demais.')
    try:
        raw=base64.b64decode(encoded,validate=True)
    except Exception as exc:
        raise RuntimeError('Foto de referência inválida.') from exc
    if len(raw)<1000 or len(raw)>26000:
        raise RuntimeError('Foto de referência inválida ou grande demais.')
    source=WORK/'reference_input.jpg'
    tmp=WORK/'reference_raw.bin'
    tmp.write_bytes(raw)
    try:
        with Image.open(tmp) as im:
            im=im.convert('RGB')
            im.thumbnail((768,768),Image.Resampling.LANCZOS)
            im.save(source,format='JPEG',quality=88,optimize=True)
    except Exception as exc:
        raise RuntimeError('Não consegui abrir a foto de referência.') from exc
    finally:
        tmp.unlink(missing_ok=True)
    return source


def strict_reference_image(reference_path):
    def choose_image(scene,idx,style,niche,visual_context,realistic,_previous,used_photo):
        del used_photo
        out=WORK/f'reference_generated_{idx:02d}.jpg'
        base=' '.join(str(scene.get(k,'')) for k in ('visual_description','visual_query','narration'))
        run_salt=os.getenv('GITHUB_RUN_ID') or os.getenv('INPUT_REQUEST_ID') or os.urandom(8).hex()
        seed=int(hashlib.sha256((base+str(idx)+str(visual_context)+'reference'+run_salt).encode('utf-8')).hexdigest()[:8],16)
        prompt=visual_engine.build_prompt(scene,visual_context,style,niche,idx,realistic,True)
        prompt+=' Use the supplied reference image as the actual visual source for identity, subject appearance, product/object design, colors and distinguishing features whenever applicable. Create a fresh composition for this exact narration scene.'
        ok=visual_engine.cf_klein(prompt,out,seed,reference_path)
        if not ok or not out.exists() or out.stat().st_size<20000:
            raise RuntimeError('Não foi possível gerar esta cena diretamente a partir da foto de referência. Tente novamente quando o motor visual estiver disponível.')
        return out,'generated-reference-primary'
    return choose_image


def install_runtime():
    flux_runtime.install()
    voice_speed_runtime.install(natural_voice)
    turbo.synthesize=natural_voice.synthesize
    media_history.install(turbo)
    original_generate=turbo.generate_scene_image
    run_salt=os.getenv('GITHUB_RUN_ID') or os.getenv('INPUT_REQUEST_ID') or os.urandom(8).hex()
    def fresh_generate(scene,path,visual_context='',style='classic-2d',niche='custom',idx=0,realistic=True,reference=None):
        fresh=dict(scene)
        fresh['visual_query']=f"{scene.get('visual_query','')} fresh-take-{run_salt}-{idx}"
        return original_generate(fresh,path,visual_context,style,niche,idx,realistic,reference)
    turbo.generate_scene_image=fresh_generate
    print('Motores de imagem e narração preparados.',flush=True)


def main():
    install_runtime()
    mode=os.getenv('INPUT_MEDIA_SOURCE','auto').strip().lower()
    if mode!='reference':
        turbo.main()
        media_history.save()
        return
    reference=prepare_reference()
    if not (visual_engine.CF_ACCOUNT_ID and visual_engine.CF_API_TOKEN):
        raise RuntimeError('O motor de geração por foto de referência ainda não está configurado.')
    turbo.choose_image=strict_reference_image(reference)
    turbo.pexels_video=lambda queries,used:(None,None,'')
    turbo.pexels_photo=lambda queries,used:(None,None,'')
    turbo.main()
    media_history.save()


if __name__=='__main__':
    main()
