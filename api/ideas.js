const { requirePin } = require('../lib/auth');
module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' });
  if (!requirePin(req, res)) return;

  try {
    const key = process.env.GROQ_API_KEY;
    if (!key) return res.status(500).json({ error: 'Configure GROQ_API_KEY na Vercel para usar sugestões automáticas.' });
    const niche = String(req.body?.niche || '').trim();
    if (!niche) return res.status(400).json({ error: 'Informe um nicho.' });

    const model = process.env.GROQ_MODEL || 'qwen/qwen3.8-27b';
    const prompt = `Crie exatamente 3 ideias MUITO diferentes entre si para vídeos verticais de 60 a 70 segundos no nicho: ${niche}.\n` +
      `Cada ideia precisa ter potencial de retenção, ser original, não depender de notícia atual e não repetir a mesma estrutura.\n` +
      `Retorne SOMENTE JSON válido no formato {"ideas":["tema 1","tema 2","tema 3"]}.`;

    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, temperature: 0.9, messages: [{ role: 'user', content: prompt }] })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.error?.message || `Groq HTTP ${response.status}`);
    const raw = data.choices?.[0]?.message?.content || '';
    const jsonText = raw.match(/\{[\s\S]*\}/)?.[0];
    if (!jsonText) throw new Error('A IA não retornou JSON válido.');
    const parsed = JSON.parse(jsonText);
    const ideas = Array.isArray(parsed.ideas) ? parsed.ideas.slice(0, 3) : [];
    if (ideas.length !== 3) throw new Error('Não foi possível gerar 3 ideias.');
    return res.status(200).json({ ideas });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message || 'Falha ao sugerir ideias.' });
  }
};
