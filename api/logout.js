const { clearSessionCookie } = require('../lib/auth');

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' });
  clearSessionCookie(res);
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({ ok: true });
};
