# Shorts Cloud — starter v0.1

Gerador independente de vídeos verticais de **60 a 70 segundos**, preparado para **até 3 vídeos por dia**, sem renderização no celular/PC.

## Arquitetura

- **Interface:** HTML/CSS/JS hospedado na Vercel.
- **Roteiro:** Groq API.
- **Clipes:** Pexels API.
- **Voz:** Piper TTS 1.7.0 em português do Brasil.
- **Render:** FFmpeg.
- **Computação pesada:** GitHub Actions (`ubuntu-latest`).
- **Entrega:** GitHub Release com `final.mp4` + `metadata.json`.

As dependências Python do renderizador ficam em `scripts/requirements.txt`. Elas não devem voltar para a raiz do repositório, pois a Vercel tentaria instalar modelos de voz e pacotes de GPU durante o deploy do site.

As rotas do modo Áudio Ilustrado compartilham as funções `generate`, `plan` e `status` por meio de rewrites. Os handlers correspondentes permanecem em `lib/` para que o projeto continue dentro do limite de 12 funções do plano Hobby da Vercel.

O navegador apenas dispara a tarefa e consulta o status. Você pode fechar a página depois de iniciar.

## Por que 3/dia

A API `/api/generate` conta as execuções do workflow no dia atual em `America/Sao_Paulo` e bloqueia novas solicitações quando chega a 3. Essa é uma trava do aplicativo; você pode alterar depois.

## 1. Crie um repositório NOVO no GitHub

Recomendação: **público**, por exemplo `shorts-cloud`.

Repositórios públicos usando runners padrão do GitHub Actions não consomem a cota mensal de minutos de Actions. As chaves continuam protegidas em `Settings > Secrets and variables > Actions`.

> Atenção: nesta v0.1 o MP4 final é colocado em **GitHub Releases**. Se o repositório for público, o vídeo também fica acessível publicamente pelo link da Release. Para vídeos privados, a próxima evolução indicada é trocar a entrega por Supabase Storage privado.

Faça upload de todos os arquivos deste pacote para o repositório, preservando as pastas, inclusive `.github/workflows/`.

## 2. Crie as chaves gratuitas

### Groq

Crie uma API key no console da Groq. O projeto usa por padrão:

`qwen/qwen3.8-27b`

Se esse modelo mudar no futuro, troque `GROQ_MODEL` no workflow/Vercel.

### Pexels

Crie uma API key da Pexels.

## 3. Configure Secrets do GitHub

No repositório:

`Settings > Secrets and variables > Actions > New repository secret`

Crie:

- `GROQ_API_KEY`
- `PEXELS_API_KEY`
- `CF_ACCOUNT_ID`
- `CF_API_TOKEN`

Os dois últimos ativam a criação de imagens com referência visual e são obrigatórios para manter os mesmos personagens no modo Áudio Ilustrado.

Não coloque essas chaves em arquivos do projeto.

## 4. Teste o render diretamente no GitHub

Abra:

`Actions > Generate Short > Run workflow`

Exemplo:

- Topic: `A coragem de Davi antes de enfrentar Golias`
- Duration: `65`
- Style: `cinematográfico e emocional`

Quando concluir, abra `Releases` e baixe `final.mp4`.

Faça esse teste ANTES da Vercel. Assim você confirma Groq + Pexels + Piper + FFmpeg isoladamente.

## 5. Crie um token para a Vercel disparar o GitHub Actions

Crie um **fine-grained Personal Access Token** no GitHub restrito somente ao novo repositório.

Permissões mínimas necessárias:

- Actions: Read and write
- Contents: Read
- Metadata: Read

Não coloque esse token no frontend.

## 6. Publique na Vercel

Importe o repositório como um projeto Vercel.

Em `Settings > Environment Variables`, crie:

- `GITHUB_PAT` = seu token fine-grained
- `TARGET_REPO` = `SEU_USUARIO/shorts-cloud`
- `GROQ_API_KEY` = sua chave Groq (somente para o botão “Sugerir 3”)
- `GROQ_MODEL` = `qwen/qwen3.8-27b`
- `APP_PIN` = crie um PIN forte que só você saiba
- `CRON_SECRET` = uma senha aleatória longa para autorizar a limpeza diária de arquivos temporários

Para aceitar arquivos no modo **Áudio Ilustrado**, conecte também um **Blob Store privado** ao projeto. A plataforma adicionará automaticamente `BLOB_READ_WRITE_TOKEN`. Os uploads recebem nomes aleatórios, só são liberados ao processamento por endereços assinados temporários e o processo diário remove arquivos com mais de 24 horas. O storyboard intermediário fica criptografado em um artefato temporário de um dia, não em uma publicação pública do repositório.

Faça um novo deploy.

## Modo Áudio Ilustrado

Esse modo aceita áudio, vídeo ou link público e preserva o áudio original. O fluxo:

1. Baixa o conteúdo em processamento isolado.
2. Transcreve a fala com marcações de tempo.
3. Extrai doze momentos do vídeo e os analisa em três painéis.
4. Cria personagens originais e uma ficha visual fixa.
5. Recusa storyboards vagos e exige ação, reação ou piada visual em cada beat.
6. Gera todos os desenhos usando a mesma referência de personagens.
7. Faz uma revisão visual conjunta e recria cenas incoerentes.
8. Mantém desenhos estáveis, cortes sincronizados, palavras no alto e legendas opcionais embaixo.
9. Entrega em 1080×1920, 30 fps, H.264/AAC e sem movimento artificial de câmera.

Links dependem de acesso público pela plataforma de origem. Quando um site bloquear a leitura automatizada, envie o arquivo diretamente.

## 7. Uso diário

Você tem duas opções:

1. Escrever manualmente até três temas.
2. Informar um nicho e clicar em **Sugerir 3**.

Depois clique em **Gerar vídeos preenchidos**.

O site dispara até três workflows separados. A página pode ser fechada; o GitHub continua trabalhando.

## Monetização e originalidade

Este projeto tenta reduzir o risco de conteúdo repetitivo criando roteiro original, gancho, desenvolvimento e conclusão para cada tema. Mesmo assim, **nenhum código garante monetização**. Revise cada vídeo antes de publicar, confirme fatos e evite publicar variações quase idênticas em massa.

Também é recomendável acrescentar progressivamente elementos autorais: identidade visual, opinião/reflexão, seleção manual dos melhores clipes, introduções próprias e estilos distintos por série.

## O que a v0.1 já faz

- Até 3 vídeos/dia.
- Duração 60, 65 ou 70 segundos.
- Sugere 3 temas com IA.
- Gera roteiro + título + descrição + hashtags.
- Busca clipes verticais no Pexels.
- Evita repetir o mesmo ID de clipe dentro do vídeo.
- Narração pt-BR via Piper, com o modelo `pt_BR-faber-medium` baixado no runner.
- Ajusta a duração do áudio para a duração escolhida.
- Legendas automáticas aproximadas a partir da narração.
- Render 1080x1920 H.264/AAC.
- Status pelo celular.
- Download MP4 por GitHub Release.

## Limitações desta primeira versão

- As legendas são temporizadas por proporção de palavras, não por reconhecimento palavra-a-palavra.
- A voz Piper é gratuita e funcional, mas não tem a naturalidade de serviços premium.
- O Pexels não terá cenas bíblicas literais; o roteiro solicita buscas visuais genéricas e cinematográficas.
- Não há música automática nesta versão para evitar introduzir uma fonte adicional de licença/copyright.
- GitHub Releases públicas expõem os arquivos quando o repositório é público.

## Próximas melhorias recomendadas

1. Armazenamento privado com expiração automática.
2. Música com biblioteca explicitamente licenciada para uso comercial.
3. Legenda palavra-a-palavra com Whisper.
4. Templates visuais de canal.
5. Seleção de voz.
6. Geração automática de thumbnail/capa.
7. Publicação assistida em YouTube/TikTok quando as APIs/permissões forem apropriadas.
8. Fallback entre modelos Groq gratuitos.

## Segurança

- Nunca exponha `GITHUB_PAT`, `GROQ_API_KEY` ou `PEXELS_API_KEY` no JavaScript do navegador.
- O site exige `APP_PIN` antes de acessar status, ideias ou geração. O PIN não substitui autenticação profissional, mas evita deixar o painel aberto para qualquer visitante casual.
- Mantenha as chaves apenas em Secrets do GitHub e Environment Variables da Vercel.
- Restrinja o PAT a um único repositório.
