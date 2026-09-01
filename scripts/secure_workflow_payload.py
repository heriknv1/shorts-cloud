#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import zlib
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION='SCW1'
KEY_CONTEXT=b'short-cloud-workflow-payload-v1\0'


def _decode(value):
    value=str(value or '')
    return base64.urlsafe_b64decode(value+'='*((4-len(value)%4)%4))


def _event_inputs():
    path=Path(os.getenv('GITHUB_EVENT_PATH',''))
    if not path.is_file():
        return {}
    try:
        event=json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise RuntimeError('Não foi possível ler os dados protegidos desta execução.') from exc
    values=event.get('inputs') or {}
    return values if isinstance(values,dict) else {}


def _secret():
    value=(os.getenv('WORKFLOW_PAYLOAD_SECRET') or os.getenv('GROQ_API_KEY') or '').strip()
    if len(value)<16:
        raise RuntimeError('A proteção dos dados do processamento não está configurada.')
    return value


def load_secure_payload():
    inputs=_event_inputs()
    request_id=str(inputs.get('request_id') or os.getenv('INPUT_REQUEST_ID') or '').strip()
    token=str(inputs.get('secure_payload') or os.getenv('SECURE_WORKFLOW_PAYLOAD') or '').strip()
    if not request_id or not token:
        raise RuntimeError('Os dados protegidos desta execução estão ausentes.')
    parts=token.split('.')
    if len(parts)!=4 or parts[0]!=VERSION:
        raise RuntimeError('Os dados protegidos desta execução são inválidos.')
    try:
        nonce,ciphertext,tag=map(_decode,parts[1:])
        key=hashlib.sha256(KEY_CONTEXT+_secret().encode('utf-8')).digest()
        compressed=AESGCM(key).decrypt(nonce,ciphertext+tag,f'short-cloud:{request_id}'.encode('utf-8'))
        raw=zlib.decompress(compressed,-zlib.MAX_WBITS)
        data=json.loads(raw.decode('utf-8'))
    except Exception as exc:
        raise RuntimeError('Não foi possível abrir os dados protegidos desta execução.') from exc
    if not isinstance(data,dict) or str(data.get('request_id') or '')!=request_id:
        raise RuntimeError('Os dados protegidos não pertencem a esta execução.')
    return data
