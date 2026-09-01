#!/usr/bin/env python3
import time

import requests

import visual_engine

RETRYABLE = {408, 425, 429, 500, 502, 503, 504}

def _wait(attempt):
    time.sleep(2 + attempt * 3)

def cf_klein(prompt, path, seed, reference=None):
    account_id = visual_engine.CF_ACCOUNT_ID
    api_token = visual_engine.CF_API_TOKEN
    if not (account_id and api_token):
        return False

    url = (
        f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/'
        '@cf/black-forest-labs/flux-2-klein-4b'
    )
    headers = {'Authorization': f'Bearer {api_token}'}
    ref = visual_engine._reference_file(reference)

    try:
        for attempt in range(3):
            if ref:
                ref.seek(0)
            files = {
                'prompt': (None, prompt[:3500]),
                'width': (None, '1080'),
                'height': (None, '1920'),
                'seed': (None, str(int(seed))),
                'guidance': (None, '3.5'),
            }
            if ref:
                files['input_image_0'] = ('reference.jpg', ref, 'image/jpeg')

            try:
                response = requests.post(
                    url, headers=headers, files=files, timeout=150
                )
            except requests.RequestException:
                _wait(attempt)
                continue

            if response.status_code in RETRYABLE:
                _wait(attempt)
                continue
            if not response.ok:
                print(
                    f'Motor visual principal indisponível nesta tentativa '
                    f'(HTTP {response.status_code}); usando alternativa.',
                    flush=True
                )
                return False

            try:
                ok = visual_engine._extract_cf_image(response, path)
            except Exception:
                ok = False
            if ok and path.exists() and path.stat().st_size > 20000:
                print('Cena visual criada pelo motor principal.', flush=True)
                return True
            _wait(attempt)
    finally:
        if ref:
            ref.close()

    return False

def cf_schnell(prompt, path, seed):
    account_id = visual_engine.CF_ACCOUNT_ID
    api_token = visual_engine.CF_API_TOKEN
    if not (account_id and api_token):
        return False

    url = (
        f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/'
        '@cf/black-forest-labs/flux-1-schnell'
    )
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'prompt': prompt[:2048],
        'seed': int(seed),
        'steps': 4,
        'width': 768,
        'height': 1344,
    }

    for attempt in range(3):
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=120
            )
        except requests.RequestException:
            _wait(attempt)
            continue

        if response.status_code in RETRYABLE:
            _wait(attempt)
            continue
        if not response.ok:
            return False

        try:
            ok = visual_engine._extract_cf_image(response, path)
        except Exception:
            ok = False
        if ok and path.exists() and path.stat().st_size > 20000:
            print('Cena visual criada pelo motor alternativo.', flush=True)
            return True
        _wait(attempt)

    return False

def install():
    visual_engine.cf_klein = cf_klein
    visual_engine.cf_schnell = cf_schnell
