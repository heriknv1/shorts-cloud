const { gh, config, usedToday } = require('../lib/github');
const { requireAuth } = require('../lib/auth');
const DAILY_LIMIT = 10;

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' });
  if (!requireAuth(req, res)) return;
  try {
    const { repo } = config();
    const topic = String(req.body?.topic || '').trim();
    const plan = req.body?.plan;
    if (!topic) return res.status(400).json({ error: 'Informe o tema.' });
    if (!plan || !Array.isArray(plan.scenes) || plan.scenes.length < 6) return res.status(400).json({ error: 'Crie e aprove um plano válido antes de renderizar.' });
    const duration = Math.min(70, Math.max(60, Number(req.body?.duration || 65)));
    const tone = String(req.body?.tone || 'cinematic').slice(0, 40);
    const presetKey = ['biblical','cinematic','mysteries','ancient','motivation','science','true-stories','horror','life-lessons','animals'].includes(req.body?.presetKey) ? req.body.presetKey : 'custom';
    // Turbo preview is cartoon-first by design. Real stock media cannot silently enter this render.
    const visualStyle = 'cartoon';
    const cartoonStyle = ['interdimensional','paper-cut','retro-surreal','classic-2d','comic'].includes(req.body?.cartoonStyle) ? req.body.cartoonStyle : 'classic-2d';
    const mediaMode = 'photos';
    const captions = req.body?.captions === 'off' ? 'off' : 'on';
    const allowedMusic = new Set(['off','viral-pulse','cinematic-rise','mystery-tension','emotional-ambient','epic-ancient']);
    const music = allowedMusic.has(req.body?.music) ? req.body.music : 'off';
    const musicVolume = ['low','medium','high'].includes(req.body?.musicVolume) ? req.body.musicVolume : 'medium';
    const cleanPlan = {
      title: String(plan.title || topic).slice(0,180), summary: String(plan.summary || '').slice(0,700),
      description: String(plan.description || '').slice(0,1000), niche_key: String(plan.niche_key || presetKey).slice(0,40),
      visual_context: String(plan.visual_context || '').slice(0,700),
      scenes: plan.scenes.slice(0,10).map((s,i)=>({ beat:String(s.beat||`Cena ${i+1}`).slice(0,100), narration:String(s.narration||'').trim().slice(0,900), visual_description:String(s.visual_description||'').trim().slice(0,900), visual_query:String(s.visual_query||'cartoon scene').trim().slice(0,180), recommended_media:'image' }))
    };
    if (cleanPlan.scenes.some(s=>!s.narration)) return res.status(400).json({error:'Uma ou mais cenas estão sem narração.'});
    const planJson=JSON.stringify(cleanPlan);
    if(planJson.length>52000) return res.status(400).json({error:'O plano ficou grande demais.'});
    const used=await usedToday();
    if(used>=DAILY_LIMIT) return res.status(429).json({error:`O limite configurado de ${DAILY_LIMIT} renders de hoje já foi usado.`,usedToday:used,remaining:0});
    const requestId=`turbo-${Date.now()}`;
    await gh(`/repos/${repo}/actions/workflows/generate-short.yml/dispatches`,{method:'POST',body:JSON.stringify({ref:'turbo-v2',inputs:{topic,plan_json:planJson,duration:String(duration),tone,niche_key:presetKey,visual_style:visualStyle,cartoon_style:cartoonStyle,media_mode:mediaMode,voice:'piper-pt-br',captions,music,music_volume:musicVolume,request_id:requestId}})});
    return res.status(202).json({ok:true,requestId,engine:'turbo-v2',usedToday:used+1,dailyLimit:DAILY_LIMIT,remaining:DAILY_LIMIT-used-1});
  } catch(error){ console.error(error); return res.status(500).json({error:error.message||'Falha ao iniciar geração Turbo.'}); }
};
