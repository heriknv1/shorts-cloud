#!/usr/bin/env python3
import base64
import json
import os
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'
OUT.mkdir(exist_ok=True)
NOTES=Path(os.getenv('MEDIA_HISTORY_NOTES_PATH','work_turbo/media_history_notes.txt'))

PHOTO_IDS=set()
VIDEO_IDS=set()
THIS_PHOTOS=set()
THIS_VIDEOS=set()
INSTALLED=False


def _decode_history(text):
    for token in re.findall(r'MEDIA_USAGE_B64:([A-Za-z0-9+/=]+)',str(text or '')):
        try:
            data=json.loads(base64.b64decode(token).decode('utf-8'))
            PHOTO_IDS.update(str(x) for x in (data.get('photos') or []))
            VIDEO_IDS.update(str(x) for x in (data.get('videos') or []))
        except Exception:
            continue


def load():
    if NOTES.exists():
        try:_decode_history(NOTES.read_text(encoding='utf-8',errors='ignore'))
        except Exception:pass
    local=ROOT/'data'/'media-history.json'
    if local.exists():
        try:
            data=json.loads(local.read_text(encoding='utf-8'))
            PHOTO_IDS.update(str(x) for x in (data.get('photos') or []))
            VIDEO_IDS.update(str(x) for x in (data.get('videos') or []))
        except Exception:pass
    print(f'Memória visual carregada: {len(PHOTO_IDS)} fotos e {len(VIDEO_IDS)} vídeos bloqueados.',flush=True)


def install(turbo):
    global INSTALLED
    if INSTALLED:return
    INSTALLED=True
    load()
    original_photo=turbo.pexels_photo
    original_video=turbo.pexels_video

    def photo(queries,used):
        blocked={str(x) for x in PHOTO_IDS}|{str(x) for x in THIS_PHOTOS}|{str(x) for x in used}
        proxy=set(blocked)
        pid,url,q=original_photo(queries,proxy)
        if pid is not None:
            sid=str(pid);THIS_PHOTOS.add(sid);used.add(pid)
        return pid,url,q

    def video(queries,used):
        blocked={str(x) for x in VIDEO_IDS}|{str(x) for x in THIS_VIDEOS}|{str(x) for x in used}
        proxy=set(blocked)
        vid,url,q=original_video(queries,proxy)
        if vid is not None:
            sid=str(vid);THIS_VIDEOS.add(sid);used.add(vid)
        return vid,url,q

    turbo.pexels_photo=photo
    turbo.pexels_video=video


def save():
    data={
        'photos':sorted(THIS_PHOTOS),
        'videos':sorted(THIS_VIDEOS),
        'run_id':os.getenv('GITHUB_RUN_ID',''),
    }
    (OUT/'media_usage.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f'Memória desta criação: {len(THIS_PHOTOS)} fotos e {len(THIS_VIDEOS)} vídeos registrados.',flush=True)
