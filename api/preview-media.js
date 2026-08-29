const { requireAuth } = require('../lib/auth');

const QUERIES = {
  biblical: 'ancient desert shepherd robe middle east biblical landscape',
  devotional: 'open bible prayer warm light peaceful christian',
  mysteries: 'fog forest dark mystery investigation cinematic',
  ancient: 'ancient ruins temple archaeology historical civilization',
  'life-lessons': 'person sunset reflection solitude emotional life',
  motivation: 'runner training sunrise athlete determination',
  science: 'space telescope galaxy astronomy science',
  'true-stories': 'documentary portrait real person street photography',
  animals: 'wildlife animal nature portrait documentary',
  custom: 'cinematic vertical storytelling landscape'
};

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'Use GET.' });
  if (!requireAuth(req, res)) return;
  const preset = String(req.query?.preset || 'custom');
  const query = QUERIES[preset] || QUERIES.custom;
  const key = process.env.PEXELS_API_KEY;
  if (!key) return res.status(503).json({ error: 'PEXELS_API_KEY não configurada para a prévia.' });
  try {
    const response = await fetch(`https://api.pexels.com/v1/search?query=${encodeURIComponent(query)}&orientation=portrait&size=medium&per_page=12`, {
      headers: { Authorization: key }
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.error || `Pexels HTTP ${response.status}`);
    const photos = Array.isArray(data.photos) ? data.photos : [];
    if (!photos.length) throw new Error('Nenhuma foto encontrada para esta prévia.');
    const photo = photos[0];
    const src = photo.src || {};
    const url = src.portrait || src.large2x || src.large || src.original;
    if (!url) throw new Error('Pexels não retornou uma imagem utilizável.');
    res.setHeader('Cache-Control', 'private, max-age=3600');
    return res.status(200).json({ url, alt: photo.alt || query, photographer: photo.photographer || '', preset, query });
  } catch (error) {
    console.error('preview-media', error);
    return res.status(502).json({ error: error.message || 'Falha ao carregar foto de prévia.' });
  }
};