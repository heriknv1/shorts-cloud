const crypto = require('crypto');
const { gh, config, saoPauloDate } = require('./github');
const { requireAuth } = require('./auth');
const { validPrivateSourcePath, signPrivateSource } = require('./source-access');
const { sealWorkflowPayload } = require('./secure-workflow-payload');

const WORKFLOW = 'scale-studio.yml';
const MAX_VARIANTS = 12;
const MAX_DAILY_BATCHES = 20;
const VIDEO_MIMES = new Set(['video/mp4','video/webm','video/quicktime','video/x-m4v','video/mpeg','video/ogg','video/3gpp','video/x-matroska']);
const TEMPLATES = new Set(['impact','minimal','news']);
const SIZES = new Set(['small','medium','large']);
const FRAME_MODES = new Set(['fill','fit']);

function clean(value, max) {
  return String(value || '').replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, max);
}
function setNoStore(res) { res.setHeader('Cache-Control', 'no-store'); }
function cleanTitles(raw) {
  const values = Array.isArray(raw) ? raw : [];
  return [...new Set(values.map(v => clean(v, 110)).filter(Boolean))].slice(0, MAX_VARIANTS);
}
async function getRuns(repo) {
  const result = await gh('/repos/' + repo + '/actions/workflows/' + WORKFLOW + '/runs?per_page=40');
  return Array.isArray(result.workflow_runs) ? result.workflow_runs : [];
}
function validHex(value) { return /^#[0-9a-f]{6}$/i.test(String(value || '')); }

async function suggest(req, res) {
  const topic = clean(req.body?.topic, 220);
  if (topic.length < 6) return res.status(400).json({error:'Informe um assunto com pelo menos 6 caracteres para sugerir títulos.'});
  const key = process.env.GEMINI_API_KEY;
  if (!key) return res.status(503).json({error:'Configure GEMINI_API_KEY na Vercel para ativar sugestões gratuitas com Gemini.'});
  const count = Math.min(MAX_VARIANTS, Math.max(2, Number(req.body?.count) || 8));
  try {
    const model = 'gemini-3.1-flash-lite';
    const response = await fetch('https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent', {
      method:'POST',
      headers:{'x-goog-api-key':key,'Content-Type':'application/json'},
      body:JSON.stringify({
        systemInstruction:{parts:[{text:'Crie títulos curtos, distintos, naturais, atrativos e factualmente corretos para Reels, TikTok e YouTube Shorts em português brasileiro. Não invente fatos ou promessas e não faça clickbait enganoso. Responda só JSON na forma {"titles":["..."]}, com cada título de no máximo 75 caracteres.'}]},
        contents:[{role:'user',parts:[{text:'Gere ' + count + ' títulos para este assunto: ' + topic}]}],
        generationConfig:{temperature:0.75,maxOutputTokens:1024,responseMimeType:'application/json'}
      }),
      signal:AbortSignal.timeout(28000)
    });
    if (response.status === 429) return res.status(429).json({error:'A cota gratuita do Gemini foi atingida ou está temporariamente limitada. Tente mais tarde ou escreva títulos manualmente.'});
    const data = await response.json();
    if (!response.ok) throw Error(String(data?.error?.message || 'O Gemini não respondeu.').slice(0,200));
    const raw = String((data.candidates?.[0]?.content?.parts || []).map(p => p.text || '').join('') || '{}');
    const parsed = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1));
    const titles = cleanTitles(parsed.titles);
    if (!titles.length) throw Error('Gemini não retornou títulos válidos.');
    return res.status(200).json({titles,model});
  } catch (error) {
    console.error('scale-gemini-suggest', String(error?.message || error));
    return res.status(502).json({error:'Não foi possível obter títulos do Gemini. Você ainda pode escrevê-los manualmente.'});
  }
}
async function start(req, res) {
  if (req.body?.rightsConfirmed !== true || req.body?.publicReleaseAcknowledged !== true) {
    return res.status(400).json({error:'Confirme a autorização de uso do conteúdo e a visibilidade dos arquivos gerados.'});
  }
  const pathname = String(req.body?.sourcePathname || '').trim();
  const mime = clean(req.body?.sourceMime, 90);
  if (!validPrivateSourcePath(pathname) || !VIDEO_MIMES.has(mime)) {
    return res.status(400).json({error:'Envie um arquivo de vídeo válido antes de gerar.'});
  }
  const titles = cleanTitles(req.body?.titles);
  if (!titles.length) return res.status(400).json({error:'Escreva pelo menos um título para o vídeo.'});
  const template = TEMPLATES.has(req.body?.template) ? req.body.template : 'impact';
  const framing = FRAME_MODES.has(req.body?.framing) ? req.body.framing : 'fill';
  const size = SIZES.has(req.body?.textSize) ? req.body.textSize : 'medium';
  const accent = validHex(req.body?.accent) ? req.body.accent : '#916bff';
  const startAt = Number(req.body?.startAt);
  const endAt = Number(req.body?.endAt);
  if (!Number.isFinite(startAt) || !Number.isFinite(endAt) || startAt < 0 || endAt <= startAt || endAt - startAt > 120 || endAt - startAt < 2) {
    return res.status(400).json({error:'Selecione um trecho de 2 a 120 segundos com início e fim válidos.'});
  }
  const geminiAutoCut = req.body?.geminiAutoCut === true;
  if (geminiAutoCut && req.body?.geminiConsent !== true) return res.status(400).json({error:'Autorize expressamente o envio do vídeo ao Gemini para análise automática.'});
  if (geminiAutoCut && !process.env.GEMINI_API_KEY) return res.status(503).json({error:'Gemini indisponível: configure GEMINI_API_KEY na Vercel e no GitHub Actions antes de ativar o corte inteligente.'});
  const { repo } = config();
  const runs = await getRuns(repo);
  if (runs.some(r => r.status !== 'completed')) return res.status(409).json({error:'Já existe um lote sendo processado. Aguarde a finalização antes de iniciar outro.',active:true});
  const today = saoPauloDate();
  if (runs.filter(r => saoPauloDate(r.created_at) === today).length >= MAX_DAILY_BATCHES) {
    return res.status(429).json({error:'O limite de segurança de ' + MAX_DAILY_BATCHES + ' lotes diários foi atingido.'});
  }
  const requestId = 'scale-' + Date.now() + '-' + crypto.randomBytes(4).toString('hex');
  const sourceUrl = await signPrivateSource(pathname);
  const payload = sealWorkflowPayload({
    source_url:sourceUrl,source_mime:mime,source_name:clean(req.body?.sourceName,120),
    topic:clean(req.body?.topic,220),start_at:startAt,end_at:endAt,
    titles,template,framing,text_size:size,accent,gemini_auto_cut:geminiAutoCut
  }, requestId);
  await gh('/repos/' + repo + '/actions/workflows/' + WORKFLOW + '/dispatches',{
    method:'POST',body:JSON.stringify({ref:'main',inputs:{request_id:requestId,secure_payload:payload}})
  });
  return res.status(202).json({ok:true,requestId,count:titles.length,message:'Lote enviado para renderização na nuvem.'});
}
async function history(req, res) {
  const { repo } = config();
  const [runs, releases] = await Promise.all([
    getRuns(repo),gh('/repos/' + repo + '/releases?per_page=40').catch(() => [])
  ]);
  const byTag = new Map((Array.isArray(releases) ? releases : []).map(r => [r.tag_name, r]));
  const items = runs.slice(0,20).map(run => {
    const release = byTag.get('scale-' + run.id);
    const assets = (release?.assets || []).filter(a => /\.mp4$/i.test(a.name)).map(a => ({
      name:String(a.name).slice(0,130), url:a.browser_download_url, bytes:a.size
    }));
    return {
      id:run.id,title:String(run.display_title || 'Lote Studio Scale').slice(0,160),
      status:run.status,conclusion:run.conclusion,createdAt:run.created_at,
      assets,releaseUrl:release?.html_url || null,
      logsUrl:run.html_url || null
    };
  });
  return res.status(200).json({items,active:items.some(x => x.status !== 'completed')});
}
module.exports = async function scaleHandler(req,res) {
  setNoStore(res);
  if (!requireAuth(req,res)) return;
  try {
    if (req.method === 'GET') return await history(req,res);
    if (req.method !== 'POST') return res.status(405).json({error:'Use GET ou POST.'});
    if (req.body?.action === 'suggest') return await suggest(req,res);
    if (req.body?.action === 'generate') return await start(req,res);
    return res.status(400).json({error:'Ação desconhecida.'});
  } catch (error) {
    console.error('studio-scale', String(error?.message || error));
    return res.status(500).json({error:'Não foi possível realizar esta operação. Verifique a configuração ou tente novamente.'});
  }
};
