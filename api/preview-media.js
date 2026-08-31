const { requireAuth } = require('../lib/auth');

const PREVIEWS = {
  biblical: {
    url: 'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Paisagem desértica de aparência antiga para histórias bíblicas'
  },
  devotional: {
    url: 'https://images.unsplash.com/photo-1777421389422-519764272b2f?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Bíblia aberta iluminada pela luz do sol para devocional'
  },
  mysteries: {
    url: 'https://images.unsplash.com/photo-1748418647784-e016efb1acd1?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Floresta coberta por neblina para histórias de mistério'
  },
  horror: {
    url: 'https://images.unsplash.com/photo-1509248961158-e54f6934749c?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Corredor escuro com iluminação dramática para terror e suspense'
  },
  ancient: {
    url: 'https://images.unsplash.com/photo-1755071158506-00fda2beabfa?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Ruínas de templo antigo ao pôr do sol'
  },
  'life-lessons': {
    url: 'https://images.unsplash.com/photo-1781988838537-a641ded373e1?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Pessoa contemplando o pôr do sol para reflexão e lições de vida'
  },
  motivation: {
    url: 'https://images.unsplash.com/photo-1758922769578-68c5ba000d87?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Atleta correndo ao nascer do sol para conteúdo motivacional'
  },
  science: {
    url: 'https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Imagem relacionada a exploração espacial e ciência'
  },
  'true-stories': {
    url: 'https://images.unsplash.com/photo-1769803836405-eab099288cc9?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Retrato documental de uma pessoa real em ambiente urbano'
  },
  animals: {
    url: 'https://images.unsplash.com/photo-1474511320723-9a56873867b5?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Animal selvagem em ambiente natural'
  },
  custom: {
    url: 'https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=700&h=1244&q=85',
    alt: 'Paisagem cinematográfica para pré-visualização'
  }
};

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'Use GET.' });
  if (!requireAuth(req, res)) return;
  const preset = String(req.query?.preset || 'custom');
  const item = PREVIEWS[preset] || PREVIEWS.custom;
  res.setHeader('Cache-Control', 'private, max-age=86400');
  return res.status(200).json({ ...item, preset });
};