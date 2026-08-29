const { requirePin } = require('../lib/auth');

function extractJson(text) {
  const raw = String(text || '').trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '');
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) throw new Error('A IA não retornou um plano JSON válido.');
  return JSON.parse(match[0]);
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' });
  if (!requirePin(req, res)) return;
  try {
    const key = process.env.GROQ_API_KEY;
    if (!key) return res.status(500).json({ error: 'Configure GROQ_API_KEY na Vercel.' });
    const topic = String(req.body?.topic || '').trim();
    if (!topic) return res.status(400).json({ error: 'Informe o tema.' });
    const duration = Math.min(70, Math.max(60, Number(req.body?.duration || 65)));
    const tone = String(req.body?.tone || 'cinematic');
    const visualStyle = ['realistic','cartoon'].includes(req.body?.visualStyle) ? req.body.visualStyle : 'realistic';
    let mediaMode = ['photos','videos','hybrid'].includes(req.body?.mediaMode) ? req.body.mediaMode : 'photos';
    if (visualStyle === 'cartoon') mediaMode = 'photos';
    const references = Array.isArray(req.body?.references) ? req.body.references.slice(0, 3) : [];
    const targetWords = Math.round(duration * 2.35);
    const sceneCount = duration <= 60 ? 8 : duration >= 70 ? 10 : 9;
    const toneMap = {
      cinematic: 'cinematográfico, emocional e envolvente',
      documentary: 'documental, claro e intrigante',
      dramatic: 'dramático, tenso e misterioso',
      energetic: 'rápido, energético e direto'
    };
    const styleInstruction = visualStyle === 'cartoon'
      ? 'O resultado visual será uma ilustração/desenho derivado de imagens. Descreva composições claras, personagens, roupas, época, cenário, iluminação e ação.'
      : 'O resultado visual será fotográfico. Descreva cenas filmáveis e plausíveis, com época, cenário, pessoas, ação e iluminação.';
    const mediaInstruction = mediaMode === 'photos'
      ? 'Todas as cenas usarão imagens estáticas com movimento de câmera.'
      : mediaMode === 'videos'
        ? 'Todas as cenas buscarão clipes de vídeo stock. Faça queries realistas e encontráveis.'
        : 'Escolha image ou video em recommended_media para cada cena; prefira image quando a cena for específica e video quando for atmosfera ou ação genérica.';

    const prompt = `Você é diretor, roteirista e editor de Shorts em português do Brasil. Planeje UM vídeo vertical com narrativa cronológica, coerente e publicável.\n\nTEMA: ${topic}\nDURAÇÃO: ${duration}s\nTOM: ${toneMap[tone] || toneMap.cinematic}\nESTILO VISUAL: ${visualStyle}\nMÍDIA: ${mediaMode}\n\nREGRAS DE QUALIDADE:\n- Escreva aproximadamente ${targetWords} palavras de narração no total, distribuídas em ${sceneCount} cenas.\n- A história precisa ter gancho, contexto, progressão lógica, clímax e conclusão.\n- Não repita informações e não dê saltos incoerentes entre cenas.\n- Em histórias bíblicas/históricas, preserve a sequência conhecida e não apresente invenções como fatos.\n- Cada cena deve narrar somente o que a imagem daquela cena pode representar.\n- visual_query deve estar EM INGLÊS, usar 3 a 8 termos concretos para Pexels, sem nomes próprios difíceis de encontrar. Ex.: ancient shepherd desert sunset, not David biblical hero.\n- visual_description deve ser detalhada em português e corresponder exatamente à fala.\n- ${styleInstruction}\n- ${mediaInstruction}\n- Se houver imagens de referência, use-as para manter roupa, clima, enquadramento, ambiente e identidade visual. Em reference_index use 1, 2 ou 3 quando aquela referência puder servir diretamente como base da cena; caso contrário use 0.\n- Não coloque texto dentro da imagem.\n\nRetorne SOMENTE JSON válido neste formato:\n{\n  "title":"...",\n  "summary":"resumo de 1 a 2 frases",\n  "description":"descrição para postagem",\n  "hashtags":["#..."],\n  "scenes":[\n    {\n      "beat":"nome curto da cena",\n      "narration":"fala natural desta cena",\n      "visual_description":"o que deve aparecer exatamente",\n      "visual_query":"english stock search",\n      "recommended_media":"image ou video",\n      "reference_index":0\n    }\n  ]\n}`;

    const content = [{ type: 'text', text: prompt }];
    for (const ref of references) {
      const dataUrl = String(ref?.dataUrl || '');
      if (/^data:image\/(jpeg|png|webp);base64,/i.test(dataUrl) && dataUrl.length < 1300000) {
        content.push({ type: 'image_url', image_url: { url: dataUrl } });
      }
    }

    const model = process.env.GROQ_MODEL || 'qwen/qwen3.8-27b';
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model,
        temperature: 0.45,
        max_completion_tokens: 4200,
        response_format: { type: 'json_object' },
        messages: [{ role: 'user', content }]
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.error?.message || `Groq HTTP ${response.status}`);
    const plan = extractJson(data.choices?.[0]?.message?.content || '');
    if (!Array.isArray(plan.scenes) || plan.scenes.length < 6) throw new Error('A IA retornou poucas cenas.');
    plan.scenes = plan.scenes.slice(0, 10).map((scene, i) => ({
      beat: String(scene.beat || `Cena ${i+1}`).slice(0, 80),
      narration: String(scene.narration || '').trim(),
      visual_description: String(scene.visual_description || '').trim(),
      visual_query: String(scene.visual_query || 'cinematic historical scene').trim(),
      recommended_media: scene.recommended_media === 'video' ? 'video' : 'image',
      reference_index: Math.max(0, Math.min(3, Number(scene.reference_index || 0)))
    }));
    if (visualStyle === 'cartoon' || mediaMode === 'photos') plan.scenes.forEach(s => s.recommended_media = 'image');
    if (mediaMode === 'videos') plan.scenes.forEach(s => s.recommended_media = 'video');
    return res.status(200).json({ plan, model });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message || 'Falha ao criar o plano.' });
  }
};
