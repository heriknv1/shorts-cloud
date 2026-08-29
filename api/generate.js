const { gh, config, usedToday } = require('../lib/github');
const { requirePin } = require('../lib/auth');

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' });
  if (!requirePin(req, res)) return;
  try {
    const { repo } = config();
    const topic = String(req.body?.topic || '').trim();
    const plan = req.body?.plan;
    if (!topic) return res.status(400).json({ error: 'Informe o tema.' });
    if (!plan || !Array.isArray(plan.scenes) || plan.scenes.length < 6) return res.status(400).json({ error: 'Crie e aprove um plano válido antes de renderizar.' });

    const duration = Math.min(70, Math.max(60, Number(req.body?.duration || 65)));
    const tone = String(req.body?.tone || 'cinematic').slice(0, 40);
    const visualStyle = ['realistic','cartoon'].includes(req.body?.visualStyle) ? req.body.visualStyle : 'realistic';
    let mediaMode = ['photos','videos','hybrid'].includes(req.body?.mediaMode) ? req.body.mediaMode : 'photos';
    if (visualStyle === 'cartoon') mediaMode = 'photos';
    const voice = String(req.body?.voice || 'pt-BR-AntonioNeural').slice(0, 80);
    const captions = req.body?.captions === 'off' ? 'off' : 'on';

    const cleanPlan = {
      title: String(plan.title || topic).slice(0, 180),
      summary: String(plan.summary || '').slice(0, 700),
      description: String(plan.description || '').slice(0, 1000),
      hashtags: Array.isArray(plan.hashtags) ? plan.hashtags.slice(0, 8).map(v => String(v).slice(0, 60)) : [],
      scenes: plan.scenes.slice(0, 10).map((scene, i) => ({
        beat: String(scene.beat || `Cena ${i+1}`).slice(0, 100),
        narration: String(scene.narration || '').trim().slice(0, 900),
        visual_description: String(scene.visual_description || '').trim().slice(0, 900),
        visual_query: String(scene.visual_query || '').trim().slice(0, 160),
        recommended_media: scene.recommended_media === 'video' ? 'video' : 'image'
      }))
    };
    if (cleanPlan.scenes.some(s => !s.narration || !s.visual_query)) return res.status(400).json({ error: 'Uma ou mais cenas estão incompletas.' });
    const planJson = JSON.stringify(cleanPlan);
    if (planJson.length > 48000) return res.status(400).json({ error: 'O plano ficou grande demais. Reduza os textos das cenas.' });

    const used = await usedToday();
    if (used >= 3) return res.status(429).json({ error: 'O limite configurado de 3 renders de hoje já foi usado.', usedToday: used, remaining: 0 });

    const requestId = `${Date.now()}-1`;
    await gh(`/repos/${repo}/actions/workflows/generate-short.yml/dispatches`, {
      method: 'POST',
      body: JSON.stringify({
        ref: 'main',
        inputs: {
          topic,
          plan_json: planJson,
          duration: String(duration),
          tone,
          visual_style: visualStyle,
          media_mode: mediaMode,
          voice,
          captions,
          request_id: requestId
        }
      })
    });
    return res.status(202).json({ ok: true, requestId, usedToday: used + 1, remaining: 2 - used });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message || 'Falha ao iniciar geração.' });
  }
};
