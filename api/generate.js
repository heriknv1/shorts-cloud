const { gh, config, usedToday } = require('../lib/github');
const { requirePin } = require('../lib/auth');

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' });
  if (!requirePin(req, res)) return;

  try {
    const { repo } = config();
    const topics = Array.isArray(req.body?.topics)
      ? req.body.topics.map(v => String(v || '').trim()).filter(Boolean).slice(0, 3)
      : [String(req.body?.topic || '').trim()].filter(Boolean);

    if (!topics.length) return res.status(400).json({ error: 'Informe pelo menos um tema.' });

    const duration = Math.min(70, Math.max(60, Number(req.body?.duration || 65)));
    const style = String(req.body?.style || 'cinematográfico e emocional').slice(0, 120);

    const used = await usedToday();
    const remaining = Math.max(0, 3 - used);
    if (remaining <= 0) {
      return res.status(429).json({ error: 'O limite configurado de 3 vídeos de hoje já foi usado.', usedToday: used, remaining: 0 });
    }
    if (topics.length > remaining) {
      return res.status(429).json({ error: `Hoje ainda cabem ${remaining} vídeo(s).`, usedToday: used, remaining });
    }

    const accepted = [];
    for (let i = 0; i < topics.length; i++) {
      const requestId = `${Date.now()}-${i + 1}`;
      await gh(`/repos/${repo}/actions/workflows/generate-short.yml/dispatches`, {
        method: 'POST',
        body: JSON.stringify({
          ref: 'main',
          inputs: {
            topic: topics[i],
            duration: String(duration),
            style,
            request_id: requestId
          }
        })
      });
      accepted.push({ topic: topics[i], requestId });
    }

    return res.status(202).json({ ok: true, accepted, usedToday: used + accepted.length, remaining: 3 - used - accepted.length });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message || 'Falha ao iniciar geração.' });
  }
};
