function requirePin(req, res) {
  const expected = process.env.APP_PIN;
  if (!expected) {
    res.status(500).json({ error: 'Configure APP_PIN na Vercel.' });
    return false;
  }
  const received = String(req.headers['x-app-pin'] || '');
  if (received !== expected) {
    res.status(401).json({ error: 'PIN incorreto.' });
    return false;
  }
  return true;
}

module.exports = { requirePin };
