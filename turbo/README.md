# Shorts Cloud Studio — Turbo v2

Esta pasta inicia a nova geração do Shorts Cloud Studio sem alterar a versão atual em `main`.

## Base técnica

- Pipeline inspirado e compatível conceitualmente com MoneyPrinterTurbo v1.3.5 (MIT).
- Render em nuvem via GitHub Actions.
- Interface simples via Vercel.
- Roteiro e storyboard via Groq.
- Voz pt-BR via Edge TTS.
- Modo Cartoon sem Pexels/fotos reais: ilustrações 2D vetoriais geradas por código a partir do storyboard e animadas por FFmpeg/MoviePy.
- Modo Realista pode continuar usando bancos de mídia posteriormente.

## Regra de migração

A branch `turbo-v2` permanece isolada. A versão atual só será substituída depois que a Turbo v2 produzir e validar pelo menos um MP4 completo.

MoneyPrinterTurbo copyright e licença MIT devem ser preservados para qualquer código upstream que venha a ser incorporado diretamente.
