const { gh, config, workflowRuns, saoPauloDate } = require('../lib/github');
const { requirePin } = require('../lib/auth');

const STEP_PROGRESS = [
  ['Baixar projeto', 10, 'Baixando projeto'],
  ['Python', 18, 'Preparando Python'],
  ['Instalar motor de vídeo e voz', 30, 'Instalando motor de vídeo e voz'],
  ['Cache do Kokoro', 36, 'Preparando cache da voz'],
  ['Preparar Kokoro e voz de emergência', 44, 'Preparando voz neural'],
  ['Renderizar cena por cena', 78, 'Criando voz, imagens, cenas e trilha'],
  ['Guardar artefato por 2 dias', 93, 'Salvando o vídeo'],
  ['Publicar MP4 em Release', 98, 'Publicando MP4']
];

function deriveProgress(run, jobsData) {
  if (run.status === 'completed') {
    if (run.conclusion === 'success') return { progress: 100, stage: 'Concluído' };
    if (run.conclusion === 'cancelled') return { progress: 100, stage: 'Cancelado' };
    return { progress: 100, stage: 'Falhou' };
  }
  if (run.status === 'queued' || !jobsData?.jobs?.length) return { progress: 4, stage: 'Na fila do GitHub' };
  const job = jobsData.jobs[0];
  const steps = job.steps || [];
  let progress = 7;
  let stage = job.status === 'queued' ? 'Na fila do runner' : 'Iniciando renderização';
  for (const [name, pct, label] of STEP_PROGRESS) {
    const step = steps.find(s => s.name === name);
    if (!step) continue;
    if (step.status === 'completed') {
      progress = Math.max(progress, pct);
      stage = label;
    } else if (step.status === 'in_progress') {
      const base = Math.max(7, pct - (name === 'Renderizar cena por cena' ? 28 : 8));
      progress = base;
      stage = label;
      break;
    } else if (step.status === 'queued' || step.status === 'pending') {
      stage = `Aguardando: ${label}`;
      break;
    }
  }
  return { progress, stage };
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'Use GET.' });
  if (!requirePin(req, res)) return;

  try {
    const { repo } = config();
    const data = await workflowRuns();
    const releases = await gh(`/repos/${repo}/releases?per_page=30`).catch(() => []);
    const releaseMap = new Map((releases || []).map(r => [r.tag_name, r]));
    const today = saoPauloDate();
    const all = data.workflow_runs || [];
    const usedToday = all.filter(r => saoPauloDate(r.created_at) === today).length;
    const selected = all.slice(0, 12);

    const jobsByRun = new Map();
    await Promise.all(selected.filter(r => r.status !== 'completed').slice(0, 5).map(async run => {
      const jobs = await gh(`/repos/${repo}/actions/runs/${run.id}/jobs?per_page=10`).catch(() => null);
      jobsByRun.set(run.id, jobs);
    }));

    const runs = selected.map(run => {
      const release = releaseMap.get(`short-${run.id}`);
      const mp4 = release?.assets?.find(a => a.name.toLowerCase().endsWith('.mp4'));
      const metadata = release?.assets?.find(a => a.name.toLowerCase().endsWith('.json'));
      const progress = deriveProgress(run, jobsByRun.get(run.id));
      return {
        id: run.id,
        name: run.display_title || run.name,
        status: run.status,
        conclusion: run.conclusion,
        createdAt: run.created_at,
        updatedAt: run.updated_at,
        htmlUrl: run.html_url,
        downloadUrl: mp4?.browser_download_url || null,
        metadataUrl: metadata?.browser_download_url || null,
        progress: progress.progress,
        stage: progress.stage
      };
    });

    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).json({ usedToday, remaining: Math.max(0, 3 - usedToday), runs });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message || 'Falha ao consultar status.' });
  }
};
