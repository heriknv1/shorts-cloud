const crypto = require('crypto');

const COOKIE_NAME = 'shorts_cloud_session';
const SESSION_SECONDS = 24 * 60 * 60;

function authConfig() {
  const username = String(process.env.APP_USERNAME || '').trim();
  const password = String(process.env.APP_PASSWORD || '');
  const secret = String(process.env.AUTH_SECRET || '');
  if (!username || !password || secret.length < 32) {
    throw new Error('Configure APP_USERNAME, APP_PASSWORD e AUTH_SECRET (mínimo 32 caracteres) na Vercel.');
  }
  return { username, password, secret };
}

function safeEqual(a, b) {
  const left = crypto.createHash('sha256').update(String(a)).digest();
  const right = crypto.createHash('sha256').update(String(b)).digest();
  return crypto.timingSafeEqual(left, right);
}

function b64url(value) {
  return Buffer.from(value).toString('base64url');
}

function sign(value, secret) {
  return crypto.createHmac('sha256', secret).update(value).digest('base64url');
}

function createSessionToken(username) {
  const { secret } = authConfig();
  const payload = b64url(JSON.stringify({ u: username, exp: Date.now() + SESSION_SECONDS * 1000, v: 1 }));
  return `${payload}.${sign(payload, secret)}`;
}

function parseCookies(req) {
  const raw = String(req.headers.cookie || '');
  return Object.fromEntries(raw.split(';').map(v => v.trim()).filter(Boolean).map(pair => {
    const idx = pair.indexOf('=');
    return idx < 0 ? [pair, ''] : [pair.slice(0, idx), decodeURIComponent(pair.slice(idx + 1))];
  }));
}

function verifySessionToken(token) {
  try {
    const { username, secret } = authConfig();
    const [payload, signature] = String(token || '').split('.');
    if (!payload || !signature || !safeEqual(signature, sign(payload, secret))) return null;
    const data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
    if (data?.v !== 1 || data?.u !== username || !Number.isFinite(data?.exp) || Date.now() >= data.exp) return null;
    return data;
  } catch {
    return null;
  }
}

function getSession(req) {
  const cookies = parseCookies(req);
  return verifySessionToken(cookies[COOKIE_NAME]);
}

function requireAuth(req, res) {
  try {
    const session = getSession(req);
    if (!session) {
      res.status(401).json({ error: 'Sessão expirada ou acesso não autorizado.' });
      return false;
    }
    return true;
  } catch (error) {
    res.status(500).json({ error: error.message || 'Autenticação não configurada.' });
    return false;
  }
}

function verifyCredentials(username, password) {
  const config = authConfig();
  return safeEqual(String(username || ''), config.username) && safeEqual(String(password || ''), config.password);
}

function setSessionCookie(res, token) {
  const secure = process.env.NODE_ENV === 'production' ? '; Secure' : '';
  res.setHeader('Set-Cookie', `${COOKIE_NAME}=${encodeURIComponent(token)}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${SESSION_SECONDS}${secure}`);
}

function clearSessionCookie(res) {
  const secure = process.env.NODE_ENV === 'production' ? '; Secure' : '';
  res.setHeader('Set-Cookie', `${COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0${secure}`);
}

module.exports = {
  authConfig,
  createSessionToken,
  getSession,
  requireAuth,
  verifyCredentials,
  setSessionCookie,
  clearSessionCookie
};
