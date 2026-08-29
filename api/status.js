const { gh, config, workflowRuns, saoPauloDate } = require('../lib/github');
const { requirePin } = require('../lib/auth');

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

    const runs = all.slice(0, 12).map(run => {
      const release = releaseMap.get(`short-${run.id}`);
      const mp4 = release?.assets?.find(a => a.name.toLowerCase().endsWith('.mp4'));
      const metadata = release?.assets?.find(a => a.name.toLowerCase().endsWith('.json'));
      return {
        id: run.id,
        name: run.display_title || run.name,
        status: run.status,
        conclusion: run.conclusion,
        createdAt: run.created_at,
        updatedAt: run.updated_at,
        htmlUrl: run.html_url,
        downloadUrl: mp4?.browser_download_url || null,
        metadataUrl: metadata?.browser_download_url || null
      };
    });

    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).json({ usedToday, remaining: Math.max(0, 3 - usedToday), runs });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message || 'Falha ao consultar status.' });
  }
};
