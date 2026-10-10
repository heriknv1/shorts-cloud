#!/usr/bin/env python3
"""Análise opcional de vídeo no Gemini Flash-Lite, com custo controlado pela cota gratuita."""
import json
import math
import os
import time
from pathlib import Path


FREE_MODEL = 'gemini-3.1-flash-lite'
MAX_ANALYSIS_SECONDS = 600
PROCESS_TIMEOUT_SECONDS = 240


def parse_suggestion(text, duration):
    """Ignora sugestões inválidas e nunca deixa IA emitir parâmetros arbitrários para FFmpeg."""
    raw = str(text or '')
    begin = raw.find('{')
    finish = raw.rfind('}')
    if begin < 0 or finish <= begin:
        raise ValueError('O Gemini não devolveu informações de corte em JSON.')
    payload = json.loads(raw[begin:finish + 1])
    if not isinstance(payload, dict):
        raise ValueError('Resposta não é um objeto.')
    start = float(payload['start'])
    end = float(payload['end'])
    reason = ' '.join(str(payload.get('reason') or '').split())[:260]
    if not all(map(math.isfinite, (start, end, duration))):
        raise ValueError('Tempo inválido na resposta.')
    if not (0 <= start < end <= duration + 0.5):
        raise ValueError('O intervalo não existe nesse vídeo.')
    if not (15 <= end - start <= 60):
        raise ValueError('O trecho sugerido deve ter entre 15 e 60 segundos.')
    return {'start':round(start, 2),'end':round(min(end,duration), 2),'reason':reason}


def analyze_best_clip(source: Path, duration: float, topic: str = ''):
    """Envia exclusivamente o vídeo autorizado a Gemini Files e apaga-o ao final."""
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        raise RuntimeError('GEMINI_API_KEY não está configurada no GitHub Actions.')
    if not (15 <= duration <= MAX_ANALYSIS_SECONDS):
        raise ValueError('Corte Gemini requer um vídeo entre 15 segundos e 10 minutos.')
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    video_file = None
    try:
        # O arquivo fica no serviço Gemini temporariamente enquanto é analisado.
        video_file = client.files.upload(file=str(source))
        deadline = time.monotonic() + PROCESS_TIMEOUT_SECONDS
        while str(getattr(getattr(video_file, 'state', None), 'name', '')).upper() == 'PROCESSING':
            if time.monotonic() > deadline:
                raise TimeoutError('O Gemini demorou muito a preparar o vídeo.')
            time.sleep(4)
            video_file = client.files.get(name=video_file.name)
        status = str(getattr(getattr(video_file, 'state', None), 'name', '')).upper()
        if status not in {'ACTIVE', ''}:
            raise RuntimeError('O Gemini não conseguiu processar esse formato de vídeo.')
        instruction = (
            'Analise o conteúdo REAL desse vídeo com atenção às imagens, fala e áudio. '
            'Identifique um trecho contínuo e independente de 15 a 60 segundos com melhor potencial '
            'para um Short ou Reels. O trecho deve começar com um gancho natural, entregar uma informação '
            'interessante e terminar sem interromper frase ou raciocínio. Evite silêncio, tela preta, '
            'introduções e finais irrelevantes. Não invente falas, acontecimentos ou timestamps. '
            'Responda SOMENTE um JSON no formato {"start":0.0,"end":30.0,"reason":"motivo curto em português"}. '
            'Use segundos decimais e valores que existam no vídeo. '
            'Assunto informado: ' + str(topic or 'não informado')[:220] +
            '. Duração total em segundos: ' + str(round(duration, 2))
        )
        response = client.models.generate_content(
            model=FREE_MODEL,
            contents=[video_file, instruction],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.2,
                max_output_tokens=700,
            )
        )
        result = parse_suggestion(response.text, duration)
        print('Gemini selecionou %.2f a %.2f segundos: %s' % (
            result['start'],result['end'],result['reason']), flush=True)
        return result
    finally:
        if video_file and getattr(video_file, 'name', None):
            try:
                client.files.delete(name=video_file.name)
            except Exception:
                print('O arquivo Gemini não pôde ser removido imediatamente; '
                      'o provedor aplica sua política de expiração.', flush=True)
        try:
            client.close()
        except Exception:
            pass
