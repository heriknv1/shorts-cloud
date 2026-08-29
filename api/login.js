const { createSessionToken, verifyCredentials, setSessionCookie } = require('../lib/auth');

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' });
  try {
    const username = String(req.body?.username || '').trim();
    const password = String(req.body?.password || '');
    if (!username || !password) return res.status(400).json({ error: 'Informe usuário e senha.' });
    if (!verifyCredentials(username, password)) return res.status(401).json({ error: 'Usuário ou senha incorretos.' });
    setSessionCookie(res, createSessionToken(username));
    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).json({ ok: true, username });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message || 'Falha no login.' });
  }
};
