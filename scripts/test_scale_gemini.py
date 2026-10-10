#!/usr/bin/env python3
"""Validação local da análise Gemini sem consumir API ou exigir chaves."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from scale_gemini import parse_suggestion


def expect_failure(text, duration):
    try:
        parse_suggestion(text,duration)
    except (ValueError,KeyError,TypeError,OverflowError):
        return
    raise AssertionError('O Gemini enviou um intervalo inválido que foi aceito.')


def main():
    result = parse_suggestion('{"start":17.5,"end":51.5,"reason":"Fala com gancho e conclusão."}',65)
    assert result == {'start':17.5,'end':51.5,'reason':'Fala com gancho e conclusão.'}
    for bad in [
        '{"start":-1,"end":20}',
        '{"start":5,"end":65}',
        '{"start":0,"end":12}',
        '{"start":10,"end":95}',
        '{"start":null,"end":40}',
        '{"start":0,"end":"NaN"}',
        '{"start":20,"end":18}',
        'não é JSON'
    ]:
        expect_failure(bad,60)
    print('Studio Scale Gemini clip validation: PASS')


if __name__ == '__main__':
    main()
