#!/usr/bin/env python3
import hashlib
import json
import math
import os
import re

import visual_engine

_STOPWORDS = {
    'a','o','as','os','um','uma','uns','umas','de','da','do','das','dos','e','em','no','na','nos','nas',
    'para','por','com','sem','que','se','ao','aos','à','às','mais','menos','como','quando','onde','essa',
    'esse','esta','este','isso','isto','ele','ela','eles','elas','seu','sua','seus','suas','the','and',
    'with','from','into','this','that','scene','cena','cinematic','realistic','realista','vertical',
    'historia','história','video','vídeo','imagem','image','shot','frame','camera','câmera'
}


def _plan():
    try:
        data = json.loads(os.getenv('INPUT_PLAN_JSON', '{}'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _active():
    tone = os.getenv('INPUT_TONE', 'cinematic').strip().lower()
    visual = os.getenv('INPUT_VISUAL_STYLE', 'realistic').strip().lower()
    niche = os.getenv('INPUT_NICHE_KEY', '').strip().lower()
    return visual == 'realistic' and tone == 'cinematic' and niche != 'audio-illustrated'


def _clean(value, limit=700):
    return ' '.join(str(value or '').replace('\n', ' ').split())[:limit]


def _tokens(value):
    text = str(value or '').lower()
    text = re.sub(r'[^a-záàâãéêíóôõúüç0-9 ]+', ' ', text)
    return {
        token for token in text.split()
        if len(token) >= 4 and token not in _STOPWORDS and not token.isdigit()
    }


def _scene_text(scene):
    return ' '.join(str(scene.get(k, '') or '') for k in (
        'beat', 'narration', 'visual_description', 'visual_query'
    ))


def _should_reuse_reference(scenes, idx):
    if idx <= 0 or idx >= len(scenes):
        return False
    prev_tokens = _tokens(_scene_text(scenes[idx - 1]))
    curr_tokens = _tokens(_scene_text(scenes[idx]))
    overlap = prev_tokens & curr_tokens
    if len(overlap) >= 2:
        return True
    identity_words = {
        'homem','mulher','menino','menina','garoto','garota','criança','crianca','idoso','idosa',
        'soldado','soldados','rei','rainha','profeta','apóstolo','apostolo','discípulo','discipulo',
        'davi','daniel','paulo','pedro','moisés','moises','josé','jose','abraão','abraao','ester',
        'jesus','samson','sansão','sansao','jonas','elias','goliath','golias'
    }
    return bool((prev_tokens & curr_tokens) & identity_words)


def _continuity_note(plan, scenes, idx):
    current = scenes[idx] if 0 <= idx < len(scenes) else {}
    previous = scenes[idx - 1] if idx > 0 else {}
    next_scene = scenes[idx + 1] if idx + 1 < len(scenes) else {}
    global_context = _clean(plan.get('visual_context', ''), 820)
    pieces = [
        'This frame belongs to one continuous premium short film, not a disconnected slideshow.',
        'Lock recurring character identity exactly: same face structure, age, skin tone, hair, beard, body type, wardrobe colors, accessories and distinguishing details unless the narration explicitly changes them.',
        'Lock recurring locations and props: preserve architecture, geography, weather, practical light sources and period details unless the story explicitly moves somewhere else.',
        'Show the exact visible action of this beat. Do not add unrelated people, objects, symbols, text, logos or decorative fantasy elements.',
        'Keep natural human anatomy, believable hands, restrained facial emotion, cinematic realism, subtle film texture and documentary-grade production design.',
    ]
    if global_context:
        pieces.append(f'Original visual bible: {global_context}')
    if previous:
        pieces.append(f'Previous beat for continuity only: {_clean(previous.get("visual_description") or previous.get("beat"), 260)}')
    pieces.append(f'Current beat must dominate: {_clean(current.get("visual_description") or current.get("narration"), 420)}')
    if next_scene:
        pieces.append(f'Next beat direction only: {_clean(next_scene.get("visual_description") or next_scene.get("beat"), 220)}')
    return ' '.join(pieces)


def _generate_cinematic(original_generate, plan, scenes):
    def generate(scene, path, visual_context='', style='classic-2d', niche='custom',
                 idx=0, realistic=True, reference=None):
        if not _active() or not realistic:
            return original_generate(
                scene, path, visual_context, style, niche, idx, realistic, reference
            )

        enriched = dict(scene)
        note = _continuity_note(plan, scenes, idx)
        base_desc = _clean(
            scene.get('visual_description') or scene.get('visual_query') or scene.get('narration'),
            980
        )
        enriched['visual_description'] = f'{base_desc}. {note}'[:3000]

        use_reference = reference if _should_reuse_reference(scenes, idx) else None
        prompt = visual_engine.build_prompt(
            enriched,
            visual_context or str(plan.get('visual_context', '')),
            style,
            niche,
            idx,
            True,
            bool(use_reference),
        )
        prompt += (
            ' Premium cinematic story frame, visually specific to the narration, '
            'natural lens behavior, grounded lighting, realistic skin and fabric detail, '
            'coherent production design across the whole sequence. Avoid generic AI imagery.'
        )

        seed_base = ' '.join(str(enriched.get(k, '')) for k in (
            'visual_description', 'visual_query', 'narration'
        ))
        run_salt = (
            os.getenv('GITHUB_RUN_ID')
            or os.getenv('INPUT_REQUEST_ID')
            or 'cinematic'
        )
        seed = int(
            hashlib.sha256(
                (seed_base + str(idx) + str(visual_context) + run_salt).encode('utf-8')
            ).hexdigest()[:8],
            16,
        )

        if visual_engine.cf_klein(prompt, path, seed, use_reference):
            return 'generated-primary-cinematic'
        if visual_engine.cf_schnell(prompt, path, seed):
            return 'generated-fast-fallback'
        return None

    return generate


def _cinematic_render(turbo, original_render):
    def render(img, out, seconds, idx):
        if not _active():
            return original_render(img, out, seconds, idx)

        frames = max(1, int(math.ceil(float(seconds) * 30)))
        mode = idx % 6
        if mode == 0:
            z = 'min(zoom+0.00028,1.045)'
            x = 'iw/2-(iw/zoom/2)'
            y = 'ih/2-(ih/zoom/2)'
        elif mode == 1:
            z = '1.045'
            x = f'(iw-iw/zoom)*on/{frames}'
            y = 'ih/2-(ih/zoom/2)'
        elif mode == 2:
            z = '1.045'
            x = f'(iw-iw/zoom)*(1-on/{frames})'
            y = 'ih/2-(ih/zoom/2)'
        elif mode == 3:
            z = 'min(zoom+0.00022,1.035)'
            x = 'iw/2-(iw/zoom/2)'
            y = f'(ih-ih/zoom)*on/{frames}'
        elif mode == 4:
            z = '1.038'
            x = 'iw/2-(iw/zoom/2)'
            y = f'(ih-ih/zoom)*(1-on/{frames})'
        else:
            z = 'min(zoom+0.00018,1.03)'
            x = 'iw/2-(iw/zoom/2)'
            y = 'ih/2-(ih/zoom/2)'

        vf = (
            "scale=1200:2134:force_original_aspect_ratio=increase,"
            "crop=1200:2134,"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )
        turbo.run([
            'ffmpeg', '-y', '-loop', '1', '-i', str(img),
            '-t', f'{float(seconds):.3f}',
            '-vf', vf, '-an', '-c:v', 'libx264',
            '-preset', 'veryfast', '-crf', '21',
            '-pix_fmt', 'yuv420p', str(out)
        ], quiet=True)
    return render


def _voice_director(original_director):
    def director(spoken):
        base = original_director(spoken)
        if not _active():
            return base
        return base + '''
CONTINUITY FOR THIS CINEMATIC SHORT:
- Perform this as one continuous mini-documentary/story, even though the audio is synthesized scene by scene.
- Keep the same narrator identity, vocal weight, distance from the microphone and emotional baseline across every scene.
- Sound like a real person telling an absorbing story to one listener, not a TikTok announcer, commercial, trailer voice or AI assistant.
- Use restrained emotion, small natural changes in intensity and short micro-pauses at meaningful punctuation.
- Let important words receive subtle emphasis, then return to a relaxed conversational flow.
- Do not add, remove or paraphrase any words from the transcript.
'''
    return director


def install(turbo, natural_voice):
    plan = _plan()
    scenes = plan.get('scenes') if isinstance(plan.get('scenes'), list) else []

    original_generate = turbo.generate_scene_image
    turbo.generate_scene_image = _generate_cinematic(
        original_generate, plan, scenes
    )

    original_video = turbo.pexels_video

    def cinematic_video_fallback(queries, used):
        if _active() and os.getenv('INPUT_MEDIA_MODE', 'hybrid').strip().lower() == 'hybrid':
            return None, None, ''
        return original_video(queries, used)

    turbo.pexels_video = cinematic_video_fallback

    original_render = turbo.render_image
    turbo.render_image = _cinematic_render(turbo, original_render)

    original_director = natural_voice.director_prompt
    natural_voice.director_prompt = _voice_director(original_director)

    if _active():
        print(
            'Modo cinematográfico: FLUX priorizado, continuidade visual reforçada '
            'e narração documental natural ativada.',
            flush=True,
        )
