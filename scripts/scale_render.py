#!/usr/bin/env python3
"""Shorts Cloud Studio Scale: renderiza lotes verticais usando FFmpeg e fonte privada."""
import json
import math
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests

from secure_workflow_payload import load_secure_payload

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work_scale'
OUT = ROOT / 'output' / 'scale_batch'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
ALLOWED_HOST_SUFFIX = '.blob.vercel-storage.com'
MAX_BYTES = 200 * 1024 * 1024

def run(*args):
    subprocess.run(list(args), check=True, cwd=ROOT, stdout=subprocess.DEVNULL)

def probe(path):
    result = subprocess.check_output([
        'ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)
    ], text=True, cwd=ROOT)
    return json.loads(result)

def source_file(url, mime):
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or not (host.endswith(ALLOWED_HOST_SUFFIX) or host == 'blob.vercel-storage.com'):
        raise RuntimeError('A origem privada do vídeo não é permitida.')
    extension = {
        'video/mp4':'.mp4','video/webm':'.webm','video/quicktime':'.mov',
        'video/x-m4v':'.m4v','video/mpeg':'.mpeg','video/ogg':'.ogv',
        'video/3gpp':'.3gp','video/x-matroska':'.mkv'
    }.get(mime, '.mp4')
    target = WORK / ('source' + extension)
    total = 0
    with requests.get(url, stream=True, timeout=(15,120), allow_redirects=False) as response:
        response.raise_for_status()
        if response.is_redirect:
            raise RuntimeError('Redirecionamento inesperado no download privado.')
        with target.open('wb') as output:
            for chunk in response.iter_content(1024 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    raise RuntimeError('O vídeo ultrapassa o limite de 200 MB.')
                output.write(chunk)
    if total < 1024:
        raise RuntimeError('Arquivo enviado está vazio ou inválido.')
    return target

def wrap(text, width=19, max_lines=5):
    # quebra por palavras, sem inserir comandos FFmpeg ou filtros.
    words = re.sub(r'\s+', ' ', str(text)).strip().split(' ')
    lines = []
    active = ''
    for word in words:
        if len(word) > width:
            word = word[:width]
        if active and len(active) + 1 + len(word) > width:
            lines.append(active)
            active = word
        else:
            active = (active + ' ' + word).strip()
    if active:
        lines.append(active)
    return '\n'.join(lines[:max_lines])

def draw_filters(template, framing, accent, font_size, text_path):
    geometry = (
        'scale=1080:1920:force_original_aspect_ratio=decrease,'
        'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x080C18'
        if framing == 'fit' else
        'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920'
    )
    color = '0x' + accent.lstrip('#')
    size = {'small':53,'medium':66,'large':78}[font_size]
    common = 'drawtext=fontfile=' + FONT + ':textfile=' + text_path.as_posix() + ':expansion=none' + \
        ':fontcolor=white:fontsize=' + str(size) + ':borderw=3:bordercolor=black@0.85' + \
        ':line_spacing=15:x=(w-text_w)/2'
    if template == 'minimal':
        decorations = [
            'drawbox=x=0:y=1420:w=1080:h=500:color=black@0.70:t=fill',
            common + ':y=1480'
        ]
    elif template == 'news':
        decorations = [
            'drawbox=x=0:y=72:w=1080:h=125:color=' + color + '@0.95:t=fill',
            'drawtext=fontfile=' + FONT + ':text=EM DESTAQUE:expansion=none:fontcolor=black' +
                ':fontsize=48:x=(w-text_w)/2:y=105',
            'drawbox=x=0:y=206:w=1080:h=420:color=black@0.75:t=fill',
            common + ':y=265'
        ]
    else:
        decorations = [
            'drawbox=x=0:y=0:w=1080:h=480:color=black@0.72:t=fill',
            'drawbox=x=0:y=0:w=1080:h=15:color=' + color + ':t=fill',
            common + ':y=95'
        ]
    return ','.join([geometry, 'setsar=1'] + decorations + ['format=yuv420p'])

def main():
    payload = load_secure_payload()
    titles = payload.get('titles')
    if not isinstance(titles, list) or not 1 <= len(titles) <= 12:
        raise RuntimeError('O lote precisa ter entre 1 e 12 títulos.')
    template = str(payload.get('template', 'impact'))
    framing = str(payload.get('framing', 'fill'))
    font_size = str(payload.get('text_size', 'medium'))
    accent = str(payload.get('accent', '#916bff'))
    if template not in {'impact','minimal','news'} or framing not in {'fill','fit'} or font_size not in {'small','medium','large'} or not re.fullmatch(r'#[0-9a-fA-F]{6}', accent):
        raise RuntimeError('Configuração de edição inválida.')
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    source = source_file(str(payload.get('source_url') or ''), str(payload.get('source_mime') or ''))
    info = probe(source)
    streams = info.get('streams') or []
    if not any(s.get('codec_type') == 'video' for s in streams):
        raise RuntimeError('Arquivo original não contém vídeo.')
    duration = float(info.get('format', {}).get('duration') or 0)
    start = float(payload.get('start_at') or 0)
    end = float(payload.get('end_at') or 0)
    if not all(map(math.isfinite, (duration,start,end))) or start < 0 or end > duration + 0.4 or end <= start or end - start < 2 or end - start > 120:
        raise RuntimeError('Início e fim não combinam com a duração real do vídeo.')
    # O intervalo informado no painel continua sendo o fallback seguro.
    selected_by_gemini = None
    gemini_status = 'desativado'
    if payload.get('gemini_auto_cut') is True:
        try:
            from scale_gemini import analyze_best_clip
            selected_by_gemini = analyze_best_clip(
                source, duration, str(payload.get('topic') or '')
            )
            start = selected_by_gemini['start']
            end = selected_by_gemini['end']
            gemini_status = 'corte escolhido por Gemini'
        except Exception as exc:
            # Sem consumir chamadas pagas extras: preserva o corte manual.
            gemini_status = 'falha na análise: intervalo manual utilizado'
            print('Análise Gemini indisponível: %s. Usando trecho manual.' % str(exc)[:200],flush=True)
    actual_length = min(duration, end) - start
    results = []
    for index, value in enumerate(titles, 1):
        title = str(value).strip()[:110]
        if not title:
            raise RuntimeError('Título vazio não pode ser renderizado.')
        text_path = WORK / ('headline_%02d.txt' % index)
        text_path.write_text(wrap(title), encoding='utf-8')
        output = OUT / ('scale_%02d.mp4' % index)
        vf = draw_filters(template, framing, accent, font_size, text_path.relative_to(ROOT))
        print('Renderizando variação %d de %d...' % (index, len(titles)), flush=True)
        run('ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(start),
            '-i',str(source),'-t',str(actual_length),
            '-map','0:v:0','-map','0:a:0?',
            '-vf',vf,'-r','30','-c:v','libx264','-preset','veryfast','-crf','24',
            '-pix_fmt','yuv420p','-threads','2','-c:a','aac','-b:a','128k',
            '-movflags','+faststart',str(output))
        check = probe(output)
        video = next((s for s in check.get('streams', []) if s.get('codec_type') == 'video'), None)
        if not video or int(video.get('width',0)) != 1080 or int(video.get('height',0)) != 1920 or output.stat().st_size < 20000:
            raise RuntimeError('A variação %d não passou na validação.' % index)
        results.append({'file':output.name,'title':title,'seconds':round(actual_length,2)})
    (OUT / 'manifest.json').write_text(json.dumps({
        'topic':str(payload.get('topic',''))[:220],
        'template':template,'framing':framing,'files':results,
        'original_duration':round(duration,2),'selected_start':start,'selected_end':end,
        'gemini_status':gemini_status,'gemini_reason':selected_by_gemini.get('reason') if selected_by_gemini else ''
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Lote finalizado: %d MP4s.' % len(results), flush=True)

if __name__ == '__main__':
    main()
