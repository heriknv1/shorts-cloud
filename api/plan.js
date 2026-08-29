const { requirePin } = require('../lib/auth');

const PRESETS = {
  biblical: {
    label: 'Histórias bíblicas',
    subject: 'histórias bíblicas conhecidas e visualmente fortes',
    context: 'Oriente Médio antigo em contexto bíblico, roupas de linho e lã, túnicas, mantos, sandálias, pastores, acampamentos, desertos, vales, armas e armaduras plausíveis da Idade do Ferro. Nunca use objetos modernos, roupas modernas, castelos medievais europeus ou armaduras de cavaleiro medieval.',
    queryAnchor: 'ancient biblical middle east iron age historical reenactment'
  },
  cinematic: {
    label: 'Histórias cinematográficas',
    subject: 'histórias humanas curtas com conflito, virada e conclusão emocional',
    context: 'cinematografia realista, iluminação dramática, personagens coerentes entre cenas, ambiente definido e continuidade visual.',
    queryAnchor: 'cinematic dramatic realistic storytelling'
  },
  mysteries: {
    label: 'Mistérios e curiosidades',
    subject: 'mistérios históricos, fenômenos curiosos ou perguntas intrigantes que possam ser explicadas sem inventar fatos',
    context: 'ambiente misterioso, documental, objetos e locais relacionados ao caso, sombras e detalhes investigativos; evite imagens aleatórias apenas por serem escuras.',
    queryAnchor: 'mystery documentary investigation cinematic'
  },
  ancient: {
    label: 'História antiga',
    subject: 'eventos, personagens e curiosidades de civilizações antigas',
    context: 'reconstituição histórica da Antiguidade, arquitetura, vestimentas, armas e paisagens compatíveis com a civilização e período narrados. Proibido misturar elementos modernos ou medievais quando não pertencem ao período.',
    queryAnchor: 'ancient civilization historical reenactment archaeology'
  },
  motivation: {
    label: 'Motivacional',
    subject: 'histórias de superação, disciplina, foco e mudança de vida',
    context: 'pessoas reais em situações de esforço, treino, estudo, trabalho e conquista; imagens devem acompanhar exatamente a ação narrada.',
    queryAnchor: 'motivational human achievement cinematic'
  },
  science: {
    label: 'Ciência e espaço',
    subject: 'curiosidades científicas e do universo explicadas de forma simples e correta',
    context: 'laboratórios, fenômenos naturais, astronomia, espaço, planetas, telescópios e visual documental científico; não use ficção científica quando o assunto for ciência real.',
    queryAnchor: 'science documentary space astronomy laboratory'
  },
  'true-stories': {
    label: 'Histórias reais surpreendentes',
    subject: 'histórias reais bem documentadas que tenham começo, conflito e desfecho',
    context: 'mini-documentário realista, época e local compatíveis com a história, objetos e ambientes específicos do caso; nunca invente imagens anacrônicas.',
    queryAnchor: 'true story documentary historical realistic'
  },
  horror: {
    label: 'Terror e suspense',
    subject: 'contos de suspense originais ou lendas claramente apresentadas como lendas',
    context: 'atmosfera noturna, ambientes vazios, tensão, silhuetas e detalhes inquietantes; mantenha continuidade de local e personagem em vez de imagens de terror aleatórias.',
    queryAnchor: 'dark suspense eerie cinematic night'
  },
  'life-lessons': {
    label: 'Reflexões e lições de vida',
    subject: 'histórias curtas com escolhas, consequências e uma reflexão final',
    context: 'cenas humanas íntimas, cotidiano, emoções legíveis e continuidade entre personagens e ambientes.',
    queryAnchor: 'emotional human story cinematic everyday life'
  },
  animals: {
    label: 'Natureza e animais',
    subject: 'comportamentos, curiosidades e estratégias de sobrevivência de animais',
    context: 'animal correto, habitat natural correto e comportamento compatível com a narração; nunca trocar por outra espécie apenas por ser visualmente bonita.',
    queryAnchor: 'wildlife nature documentary animal behavior'
  }
};

const CARTOON_STYLES = {
  interdimensional: 'animação 2D sci-fi surreal, proporções caricatas, olhos expressivos, cores vibrantes e cenários alienígenas simples; identidade própria, sem copiar personagens ou cenários de obras existentes',
  'paper-cut': 'animação 2D de recortes, formas geométricas simples, silhuetas chapadas, movimento visual satírico e composição minimalista; identidade própria',
  'retro-surreal': 'animação 2D retro surreal, personagens simples, objetos cotidianos estranhos, paleta nostálgica e humor visual absurdo; identidade própria',
  'classic-2d': 'animação 2D clássica, contornos limpos, formas legíveis, cores equilibradas e enquadramentos de desenho animado tradicional',
  comic: 'ilustração de HQ cinematográfica, contornos fortes, sombras marcadas, composição dramática e cores intensas'
};

function extractJson(text) {
  const raw = String(text || '').trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '');
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error('A IA não retornou um plano JSON válido.');
  return JSON.parse(match[0]);
}
function compactWords(value, max = 10) {
  return String(value || '').trim().split(/\s+/).filter(Boolean).slice(0, max).join(' ');
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' });
  if (!requirePin(req, res)) return;
  try {
    const key = process.env.GROQ_API_KEY;
    if (!key) return res.status(500).json({ error: 'Configure GROQ_API_KEY na Vercel.' });

    const presetKey = String(req.body?.presetKey || '');
    const preset = PRESETS[presetKey] || null;
    const topic = String(req.body?.topic || '').trim();
    if (!topic && !preset) return res.status(400).json({ error: 'Informe o tema ou escolha um nicho pronto.' });

    const duration = Math.min(70, Math.max(60, Number(req.body?.duration || 65)));
    const tone = String(req.body?.tone || 'cinematic');
    const visualStyle = ['realistic','cartoon'].includes(req.body?.visualStyle) ? req.body.visualStyle : 'realistic';
    const cartoonStyle = CARTOON_STYLES[req.body?.cartoonStyle] ? String(req.body.cartoonStyle) : 'classic-2d';
    let mediaMode = ['photos','videos','hybrid'].includes(req.body?.mediaMode) ? req.body.mediaMode : 'photos';
    if (visualStyle === 'cartoon') mediaMode = 'photos';
    const references = Array.isArray(req.body?.references) ? req.body.references.slice(0, 3) : [];
    const targetWords = Math.round(duration * 2.30);
    const sceneCount = duration <= 60 ? 8 : duration >= 70 ? 10 : 9;

    const toneMap = {
      cinematic: 'cinematográfico, emocional e envolvente',
      documentary: 'documental, claro e intrigante',
      dramatic: 'dramático, tenso e misterioso',
      energetic: 'rápido, energético e direto'
    };
    const nicheContext = preset ? `${preset.label}. ${preset.context}` : 'Siga rigorosamente a época, o lugar, os personagens, objetos e ambiente descritos no tema.';
    const subjectInstruction = topic
      ? `TEMA DEFINIDO PELO USUÁRIO: ${topic}`
      : `ESCOLHA VOCÊ MESMO um tema específico e forte dentro de: ${preset.subject}. O título escolhido deve identificar claramente o assunto.`;
    const visualInstruction = visualStyle === 'cartoon'
      ? `A saída será estilizada como desenho. Estética desejada: ${CARTOON_STYLES[cartoonStyle]}. Mesmo assim, a busca stock deve procurar uma BASE visual correta em época, roupa, cenário e ação; a estilização será aplicada depois.`
      : 'A saída será fotográfica. Descreva cenas plausíveis e coerentes com a época, cenário, pessoas, ação e iluminação.';
    const mediaInstruction = mediaMode === 'photos'
      ? 'Todas as cenas usarão imagens estáticas com movimento de câmera.'
      : mediaMode === 'videos'
        ? 'Todas as cenas buscarão clipes de vídeo stock. As queries precisam ser realistas e encontráveis.'
        : 'Escolha image ou video em recommended_media para cada cena. Prefira image em cenas históricas/específicas e video em atmosfera ou ação genérica.';

    const prompt = `Você é diretor, roteirista e pesquisador visual de Shorts em português do Brasil. Planeje UM vídeo vertical coerente e publicável.\n\n${subjectInstruction}\nDURAÇÃO: ${duration}s\nTOM: ${toneMap[tone] || toneMap.cinematic}\nESTILO VISUAL: ${visualStyle}\nMÍDIA: ${mediaMode}\nNICHO/CONTEXTO OBRIGATÓRIO: ${nicheContext}\n\nREGRAS DE ROTEIRO:\n- Aproximadamente ${targetWords} palavras no total, distribuídas em ${sceneCount} cenas.\n- Gancho, contexto, progressão lógica, clímax e conclusão.\n- Não repita informações nem dê saltos incoerentes.\n- Para fatos religiosos/históricos/científicos, não invente detalhes específicos quando não tiver segurança.\n- Cada cena deve narrar somente o que o visual daquela cena consegue representar.\n\nREGRAS VISUAIS CRÍTICAS:\n- A imagem deve ser CONDIZENTE COM O NICHO, ÉPOCA, LOCAL E AÇÃO. Não escolha uma imagem apenas porque é bonita.\n- ${visualInstruction}\n- ${mediaInstruction}\n- visual_query e visual_query_backup devem estar EM INGLÊS e ser buscas concretas para Pexels.\n- Cada query deve incluir pistas de época/contexto quando isso for relevante.\n- Não use nomes próprios como única pista. Traduza a cena em elementos visuais pesquisáveis.\n- Evite anacronismos. Em tema bíblico antigo, por exemplo, não use cavaleiros medievais, roupas modernas, cidades modernas ou armaduras europeias medievais.\n- visual_query_backup deve representar a MESMA cena com termos alternativos, não uma cena diferente.\n- visual_description deve explicar exatamente o que precisa aparecer.\n- Se houver referências, use-as para manter roupa, clima, enquadramento, ambiente e identidade visual.\n- Não coloque texto dentro da imagem.\n\nRetorne SOMENTE JSON válido:\n{\n  "title":"...",\n  "summary":"resumo de 1 a 2 frases",\n  "description":"descrição para postagem",\n  "hashtags":["#..."],\n  "niche_key":"${presetKey || 'custom'}",\n  "visual_context":"resumo visual do período/ambiente que deve permanecer consistente",\n  "scenes":[\n    {\n      "beat":"nome curto da cena",\n      "narration":"fala natural desta cena",\n      "visual_description":"o que deve aparecer exatamente",\n      "visual_query":"english stock search with era/context",\n      "visual_query_backup":"alternative english search for same scene",\n      "recommended_media":"image ou video",\n      "reference_index":0\n    }\n  ]\n}`;

    const content = [{ type: 'text', text: prompt }];
    for (const ref of references) {
      const dataUrl = String(ref?.dataUrl || '');
      if (/^data:image\/(jpeg|png|webp);base64,/i.test(dataUrl) && dataUrl.length < 1300000) content.push({ type: 'image_url', image_url: { url: dataUrl } });
    }

    const model = process.env.GROQ_MODEL || 'qwen/qwen3.8-27b';
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model,
        temperature: preset ? 0.38 : 0.43,
        max_completion_tokens: 4600,
        response_format: { type: 'json_object' },
        messages: [{ role: 'user', content }]
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.error?.message || `Groq HTTP ${response.status}`);
    const plan = extractJson(data.choices?.[0]?.message?.content || '');
    if (!Array.isArray(plan.scenes) || plan.scenes.length < 6) throw new Error('A IA retornou poucas cenas.');

    const anchor = preset?.queryAnchor || '';
    plan.niche_key = presetKey || 'custom';
    plan.visual_context = String(plan.visual_context || nicheContext).slice(0, 700);
    plan.scenes = plan.scenes.slice(0, 10).map((scene, i) => {
      const primary = compactWords(scene.visual_query || 'cinematic historical scene', 11);
      const backup = compactWords(scene.visual_query_backup || scene.visual_query || 'cinematic historical scene', 11);
      return {
        beat: String(scene.beat || `Cena ${i+1}`).slice(0, 80),
        narration: String(scene.narration || '').trim(),
        visual_description: String(scene.visual_description || '').trim(),
        visual_query: `${anchor} ${primary}`.trim().slice(0, 180),
        visual_query_backup: `${anchor} ${backup}`.trim().slice(0, 180),
        recommended_media: scene.recommended_media === 'video' ? 'video' : 'image',
        reference_index: Math.max(0, Math.min(3, Number(scene.reference_index || 0)))
      };
    });
    if (visualStyle === 'cartoon' || mediaMode === 'photos') plan.scenes.forEach(s => s.recommended_media = 'image');
    if (mediaMode === 'videos') plan.scenes.forEach(s => s.recommended_media = 'video');

    return res.status(200).json({ plan, model, preset: preset ? preset.label : null });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message || 'Falha ao criar o plano.' });
  }
};
