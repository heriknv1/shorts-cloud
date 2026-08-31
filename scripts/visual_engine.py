#!/usr/bin/env python3
import base64
import hashlib
import io
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageOps

CF_ACCOUNT_ID=os.getenv('CF_ACCOUNT_ID','').strip()
CF_API_TOKEN=os.getenv('CF_API_TOKEN','').strip()

RELIGIOUS_RX=re.compile(r'\b(jesus|christ|cristo|messiah|messias|bible|biblical|bíblia|bíblico|bíblica|god|deus|gospel|evangelho|baptism|batismo|prayer|oração|church|igreja|apostle|apóstolo|disciple|discípulo|noah|noé|abraham|abraão|moses|moisés|david|davi|samson|sansão|elijah|elias|daniel|jonah|jonas|paul|paulo|peter|pedro|pentecost|pentecostes|tessalonic|thessalonic|salmo|psalm|gênesis|genesis|mateus|matthew|marcos|mark|lucas|luke|joão|john|atos|acts)\b',re.I)
JESUS_RX=re.compile(r'\b(jesus|christ|cristo|messiah|messias)\b',re.I)
BLOCKED_RX=re.compile(r'\b(catholic|católico|católica|catolicismo|cathedral|catedral|pope|papa|papal|rosary|terço|crucifix|crucifixo|statue|estátua|saint|santo|santa|virgin mary|virgem maria|madonna|marian|mariana|mass|missa|monstrance|ostensório|religious icon|ícone religioso|basilica|basílica|nun|freira|priest|padre|islam|islã|islão|islamic|islâmico|islâmica|muslim|muçulmano|muçulmana|mosque|mesquita|quran|corão|koran|mecca|meca|medina|ramadan|minaret|minarete|imam|candomblé|candomble|umbanda|orixá|orixa|orisha|terreiro|pombagira|pomba gira|iemanjá|iemanja|ogum|oxum|oxóssi|oxossi|xangô|xango|iansã|iansa|obaluaiê|obaluae)\b',re.I)
GENERIC_RELIGIOUS_SEARCH_RX=re.compile(r'\b(bible|biblical|bíblia|bíblico|bíblica|gospel|evangelho|church|igreja|holy|religious|religion|christian|cristão|cristã|devotional|scripture|faith|fé)\b',re.I)

CAMERAS=[
    'intimate medium close-up, 50mm lens, shallow depth of field',
    'cinematic wide establishing shot, 35mm lens, layered foreground and background',
    'dynamic medium shot, 50mm lens, natural perspective',
    'detail close-up, 85mm lens, tactile textures and expressive hands',
    'low-angle cinematic medium-wide shot, 35mm lens, strong spatial depth',
    'over-the-shoulder composition, 50mm lens, environmental storytelling',
]

def clean_text(value):
    value=BLOCKED_RX.sub(' ',str(value or ''))
    value=re.sub(r'\b(no|without|sem)\b',' ',value,flags=re.I)
    return ' '.join(value.split()).strip()

def scene_is_religious(scene,niche='custom'):
    text=' '.join(str(scene.get(k,'')) for k in ('visual_description','narration','visual_query','visual_query_backup'))
    return niche in {'biblical','devotional'} or bool(RELIGIOUS_RX.search(text))

def mentions_jesus(scene):
    text=' '.join(str(scene.get(k,'')) for k in ('visual_description','narration','visual_query','visual_query_backup'))
    return bool(JESUS_RX.search(text))

def stock_queries(scene,niche='custom'):
    religious=scene_is_religious(scene,niche)
    jesus=mentions_jesus(scene) and religious
    raw=[scene.get('visual_query',''),scene.get('visual_query_backup','')]
    out=[]
    for value in raw:
        q=clean_text(value)
        q=re.sub(r'\b(illustration|cartoon|drawing|animated|animation|photorealistic|cinematic)\b',' ',q,flags=re.I)
        if religious:
            q=GENERIC_RELIGIOUS_SEARCH_RX.sub(' ',q)
            if jesus:
                q=JESUS_RX.sub(' ',q)
            q=' '.join(q.split())
            if q:
                q=f'{q} historical reenactment simple ancient clothing'
        q=' '.join(q.split())[:200]
        if q and q.lower() not in [x.lower() for x in out]:
            out.append(q)
    if not out:
        desc=clean_text(scene.get('visual_description') or scene.get('narration') or 'documentary scene')
        if jesus:
            desc=JESUS_RX.sub(' ',desc)
        desc=GENERIC_RELIGIOUS_SEARCH_RX.sub(' ',desc) if religious else desc
        desc=' '.join(desc.split())
        if religious:
            desc=f'{desc} ancient middle east historical reenactment simple clothing'
        out.append(desc[:200] or 'historical reenactment people natural environment')
    if len(out)==1:
        out.append((out[0]+' alternate angle natural environment')[:200])
    return out[:2]

def _style_text(style,realistic):
    if realistic:
        return 'premium photorealistic cinematic documentary frame, physically believable materials and skin, natural imperfections, subtle film grain, realistic depth, sophisticated color grading'
    styles={
        'classic-2d':'premium hand-crafted 2D animated film illustration, expressive natural poses, detailed environment, polished cinematic lighting',
        'comic':'premium cinematic graphic novel illustration, refined ink detail, dramatic lighting, sophisticated composition',
        'paper-cut':'premium layered paper-cut illustration, tactile handmade texture, rich depth and elegant shapes',
        'retro-surreal':'polished retro-surreal editorial animation artwork, cinematic composition, refined texture',
        'interdimensional':'premium surreal sci-fi animation artwork, dimensional lighting, detailed original environment'
    }
    return styles.get(style,styles['classic-2d'])

def build_prompt(scene,visual_context='',style='classic-2d',niche='custom',idx=0,realistic=True,has_reference=False):
    religious=scene_is_religious(scene,niche)
    jesus=mentions_jesus(scene) and religious and realistic
    desc=clean_text(scene.get('visual_description') or scene.get('visual_query') or scene.get('narration') or 'cinematic scene')
    if jesus:
        desc=JESUS_RX.sub(' ',desc)
        desc+=' show the biblical environment and other people indirectly, without portraying an identifiable central divine figure'
    context=clean_text(visual_context)
    camera=CAMERAS[idx%len(CAMERAS)]
    if niche=='analog-horror':
        prompt=[
            desc,
            'single coherent frame from the same fictional analog archive tape, polished retro-surreal institutional broadcast illustration',
            'central 4:3 broadcast-safe composition inside a vertical canvas, CRT scanlines, VHS tracking damage, red black and gray palette, simple readable shapes',
            f'locked tape continuity: {context[:1100]}',
            'show only the named location, recurring subject, threat and action required by this scene; no unrelated people, objects, buildings, symbols or generic horror imagery',
            'no generic spooky hallway unless explicitly required, no gore, no watermark, no logo, no illegible decorative text',
        ]
        if has_reference:
            prompt.append('the reference is the immediately previous frame of this exact tape; preserve the same subject identity, institution, location, props, palette and threat design, changing only the current action and camera framing')
        return '. '.join(x.strip(' .') for x in prompt if x).strip()+'.'
    prompt=[
        desc,
        _style_text(style,realistic),
        camera,
        'vertical 9:16 composition, strong foreground subject separation, purposeful visual storytelling, natural body language, no text, no watermark, no logo',
    ]
    if context:
        prompt.append(f'global continuity: {context[:500]}')
    if religious:
        prompt.append('historically plausible first-century or ancient Middle Eastern/Mediterranean environment when appropriate, simple unadorned clothing and architecture, scripture-centered evangelical visual direction, avoid ornate devotional iconography and ritual objects')
    if has_reference and not jesus:
        prompt.append('use the reference only to preserve recurring character identity, clothing palette, lighting language and production design; create a new composition that follows this scene exactly')
    return '. '.join(x.strip(' .') for x in prompt if x).strip()+'.'

def _save_image_bytes(raw,path):
    with Image.open(io.BytesIO(raw)) as im:
        im=im.convert('RGB')
        im=ImageOps.fit(im,(1080,1920),method=Image.Resampling.LANCZOS,centering=(0.5,0.5))
        im.save(path,quality=94,optimize=True)

def _extract_cf_image(response,path):
    ctype=(response.headers.get('content-type') or '').lower()
    if ctype.startswith('image/'):
        _save_image_bytes(response.content,path)
        return True
    data=response.json()
    result=data.get('result',data)
    image=result.get('image') if isinstance(result,dict) else None
    if not image:
        return False
    _save_image_bytes(base64.b64decode(image),path)
    return True

def _reference_file(reference):
    if not reference or not Path(reference).exists():
        return None
    with Image.open(reference) as im:
        im=im.convert('RGB')
        im.thumbnail((448,448),Image.Resampling.LANCZOS)
        buf=io.BytesIO()
        im.save(buf,format='JPEG',quality=86)
    buf.seek(0)
    return buf

def cf_klein(prompt,path,seed,reference=None):
    if not (CF_ACCOUNT_ID and CF_API_TOKEN):
        return False
    url=f'https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-2-klein-4b'
    headers={'Authorization':f'Bearer {CF_API_TOKEN}'}
    ref=_reference_file(reference)
    files={
        'prompt':(None,prompt[:3500]),
        'width':(None,'768'),
        'height':(None,'1344'),
        'seed':(None,str(seed)),
    }
    if ref:
        files['input_image_0']=('reference.jpg',ref,'image/jpeg')
    try:
        for attempt in range(2):
            r=requests.post(url,headers=headers,files=files,timeout=150)
            if r.status_code in (429,503):
                time.sleep(2+attempt*3)
                continue
            if not r.ok:
                return False
            return _extract_cf_image(r,path)
    finally:
        if ref:
            ref.close()
    return False

def cf_schnell(prompt,path,seed):
    if not (CF_ACCOUNT_ID and CF_API_TOKEN):
        return False
    url=f'https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell'
    headers={'Authorization':f'Bearer {CF_API_TOKEN}','Content-Type':'application/json'}
    payload={'prompt':prompt[:2048],'seed':int(seed),'steps':4,'width':768,'height':1344}
    for attempt in range(2):
        r=requests.post(url,headers=headers,json=payload,timeout=120)
        if r.status_code in (429,503):
            time.sleep(2+attempt*3)
            continue
        if not r.ok:
            return False
        return _extract_cf_image(r,path)
    return False

def pollinations(prompt,path,seed):
    url=f'https://image.pollinations.ai/prompt/{quote(prompt[:3500])}?width=768&height=1344&nologo=true&seed={seed}&enhance=true'
    try:
        r=requests.get(url,timeout=120,headers={'User-Agent':'ShortCloudStudio/4.0'})
        r.raise_for_status()
        if len(r.content)<20000:
            return False
        _save_image_bytes(r.content,path)
        return True
    except Exception:
        return False

def generate_scene_image(scene,path,visual_context='',style='classic-2d',niche='custom',idx=0,realistic=True,reference=None):
    base=' '.join(str(scene.get(k,'')) for k in ('visual_description','visual_query','narration'))
    seed=int(hashlib.sha256((base+str(idx)+str(visual_context)).encode('utf-8')).hexdigest()[:8],16)
    prompt=build_prompt(scene,visual_context,style,niche,idx,realistic,bool(reference))
    if cf_klein(prompt,path,seed,reference):
        return 'generated-primary'
    if cf_schnell(prompt,path,seed):
        return 'generated-fast-fallback'
    if pollinations(prompt,path,seed):
        return 'generated-community-fallback'
    return None
