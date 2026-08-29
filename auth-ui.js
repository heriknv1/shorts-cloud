(() => {
  const SESSION_MARKER = 'shortsCloudLoggedIn';

  function ensureOverlay() {
    let overlay = document.getElementById('loginOverlay');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'loginOverlay';
    overlay.className = 'login-overlay';
    overlay.innerHTML = `
      <div class="login-panel">
        <span class="pill">Acesso protegido</span>
        <h1>Shorts Cloud Studio</h1>
        <p>Entre com seu usuário e senha para acessar as funções do painel.</p>
        <form id="loginForm" autocomplete="on">
          <label for="loginUsername">Usuário</label>
          <input id="loginUsername" name="username" autocomplete="username" required />
          <label for="loginPassword">Senha</label>
          <input id="loginPassword" name="password" type="password" autocomplete="current-password" required />
          <button id="loginButton" class="primary" type="submit">Entrar</button>
          <div id="loginMessage" class="message" hidden></div>
        </form>
      </div>`;
    document.body.appendChild(overlay);
    return overlay;
  }

  function showLoginMessage(text) {
    const el = document.getElementById('loginMessage');
    if (!el) return;
    el.hidden = !text;
    el.textContent = text;
  }

  async function login(event) {
    event.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    const button = document.getElementById('loginButton');
    button.disabled = true;
    showLoginMessage('Entrando…');
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Falha no login.');
      sessionStorage.setItem(SESSION_MARKER, '1');
      sessionStorage.setItem('shortsCloudPin', 'session-authenticated');
      location.reload();
    } catch (error) {
      showLoginMessage(error.message || 'Usuário ou senha incorretos.');
      button.disabled = false;
    }
  }

  async function bootstrap() {
    const overlay = ensureOverlay();
    document.getElementById('loginForm').addEventListener('submit', login);
    try {
      const response = await fetch('/api/session', { cache: 'no-store', credentials: 'same-origin' });
      if (!response.ok) throw new Error('not-authenticated');
      const data = await response.json();
      if (!data.authenticated) throw new Error('not-authenticated');
      sessionStorage.setItem(SESSION_MARKER, '1');
      sessionStorage.setItem('shortsCloudPin', 'session-authenticated');
      overlay.hidden = true;
      const user = document.getElementById('sessionUser');
      if (user) user.textContent = data.username || 'Conectado';
    } catch {
      sessionStorage.removeItem(SESSION_MARKER);
      sessionStorage.removeItem('shortsCloudPin');
      overlay.hidden = false;
    }
  }

  window.shortsCloudLogout = async function () {
    try { await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' }); } catch {}
    sessionStorage.removeItem(SESSION_MARKER);
    sessionStorage.removeItem('shortsCloudPin');
    location.reload();
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bootstrap);
  else bootstrap();
})();
