const { requireAuth } = require('../lib/auth');

const NICHE_HINTS = {
  biblical: 'ancient biblical Middle East, historically plausible clothing and environment, no modern objects, no medieval European armor',
  devotional: 'biblical devotional atmosphere, peaceful natural light, symbolic but realistic scene, respectful Christian context',
  mysteries: 'mystery documentary atmosphere, investigation, suspense, coherent location and objects',
  ancient: 'ancient civilization, historically plausible architecture, clothing and environment, no modern objects',
  motivation: 'human determination, training, discipline, work, study or achievement, cinematic realistic scene',
  science: 'science documentary, astronomy, laboratory, space or natural phenomenon, scientifically plausible',
  'true-stories': 'documentary realism, authentic human scene, believable location and period details',
  'life-lessons': 'emotional human story, everyday life, reflective cinematic scene',
  animals: 'wildlife documentary, correct species, natural habitat, realistic animal behavior',
  custom: 'coherent cinematic scene matching the description exactly'
};

function compact(value, max = 14) {
  return String(value || '').trim().replace(/\s+/g, ' ').split(' ').slice(0, max).join(' ');
}

function fallback(description, narration, niche) {
  const hint = NICHE_HINTS[niche] || NICHE_HINTS.custom;
  const base = compact(description || narration || 'cinematic scene', 18);
  const context = compact(hint, 12);
  return {
    visual_query: `${base} ${context}`.trim().slice(0, 180),
    visual_query_backup: `${context} ${base}`.trim().slice(0, 180)
  };
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' });
  if (!requireAuth(req, res)) return;

  const description = String(req.body?.visualDescription || '').trim();
  const narration = String(req.body?.narration || '').trim();
  const niche = String(req.body?.presetKey || 'custom');
  const visualStyle = req.body?.visualStyle === 'cartoon' ? 'cartoon' : 'realistic';
  const mediaMode = ['photos', 'videos', 'hybrid'].includes(req.body?.mediaMode) ? req.body.mediaMode : 'hybrid';
  if (!description && !narration) return res.status(400).json({ error: 'Descreva a cena.' });

  const safeFallback = fallback(description, narration, niche);
  const key = process.env.GROQ_API_KEY;
  if (!key) return res.status(200).json({ ...safeFallback, recommended_media: mediaMode === 'videos' ? 'video' : 'image', source: 'local-fallback' });

  try {
    const hint = NICHE_HINTS[niche] || NICHE_HINTS.custom;
    const prompt = `Transforme a descrição abaixo em duas buscas VISUAIS CURTAS em inglês para encontrar mídia coerente para um Short vertical.\n\nDESCRIÇÃO EDITADA PELO USUÁRIO: ${description || narration}\nCONTEXTO DA NARRAÇÃO: ${narration}\nNICHO: ${hint}\nESTILO: ${visualStyle === 'cartoon' ? 'illustration/cartoon reference' : 'realistic stock media'}\nMÍDIA: ${mediaMode}\n\nRegras:\n- As duas buscas devem representar exatamente a mesma cena, com termos alternativos.\n- Priorize pessoas, ação, lugar, época, objetos e clima descritos pelo usuário.\n- Não invente personagens, objetos ou épocas que não estejam implícitos.\n- Evite nomes próprios isolados; traduza para elementos visuais pesquisáveis.\n- Em conteúdo bíblico/histórico, evite anacronismos.\n- Cada busca deve ter no máximo 14 palavras.\n- Se MÍDIA for hybrid, escolha recommended_media como image ou video conforme a cena; em photos use image; em videos use video.\n\nResponda SOMENTE JSON: {"visual_query":"...","visual_query_backup":"...","recommended_media":"image ou video"}`;

    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: process.env.GROQ_MODEL || 'qwen/qwen3.8-27b',
        temperature: 0.18,
        max_completion_tokens: 350,
        response_format: { type: 'json_object' },
        messages: [{ role: 'user', content: prompt }]
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.error?.message || `Groq HTTP ${response.status}`);
    const parsed = JSON.parse(String(data.choices?.[0]?.message?.content || '{}'));
    const primary = compact(parsed.visual_query, 14) || safeFallback.visual_query;
    const backup = compact(parsed.visual_query_backup, 14) || safeFallback.visual_query_backup;
    let recommended = parsed.recommended_media === 'video' ? 'video' : 'image';
    if (mediaMode === 'photos') recommended = 'image';
    if (mediaMode === 'videos') recommended = 'video';
    return res.status(200).json({ visual_query: primary, visual_query_backup: backup, recommended_media: recommended, source: 'groq' });
  } catch (error) {
    console.error('scene-query', error);
    return res.status(200).json({ ...safeFallback, recommended_media: mediaMode === 'videos' ? 'video' : 'image', source: 'local-fallback' });
  }
};