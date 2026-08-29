const { getSession } = require('../lib/auth');

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'Use GET.' });
  const session = getSession(req);
  res.setHeader('Cache-Control', 'no-store');
  if (!session) return res.status(401).json({ authenticated: false });
  return res.status(200).json({ authenticated: true, username: session.u });
};
