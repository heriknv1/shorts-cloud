const $ = (id) => document.getElementById(id);
const quotaText = $('quotaText');
const runsBox = $('runs');
const message = $('message');
let appPin = sessionStorage.getItem('shortsCloudPin') || '';
$('pin').value = appPin;

function headers(extra = {}) {
  return { 'X-App-Pin': appPin, ...extra };
}

function setMessage(text, error = false) {
  message.hidden = !text;
  message.textContent = text;
  message.style.borderColor = error ? '#6d3030' : '#2d3a50';
}

function statusBadge(run) {
  if (run.status !== 'completed') return ['Processando', 'warn'];
  if (run.conclusion === 'success') return ['Concluído', 'ok'];
  if (run.conclusion === 'cancelled') return ['Cancelado', 'bad'];
  return ['Falhou', 'bad'];
}

async function refreshStatus() {
  if (!appPin) {
    quotaText.textContent = 'informe o PIN';
    runsBox.innerHTML = '<p class="muted">Entre com o PIN para ver os vídeos.</p>';
    return;
  }
  try {
    const res = await fetch('/api/status', { cache: 'no-store', headers: headers() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao carregar status.');
    quotaText.textContent = `${data.usedToday}/3 usados • ${data.remaining} restantes`;
    $('generateBtn').disabled = data.remaining <= 0;

    if (!data.runs?.length) {
      runsBox.innerHTML = '<p class="muted">Nenhum vídeo gerado ainda.</p>';
      return;
    }
    runsBox.innerHTML = data.runs.map(run => {
      const [label, cls] = statusBadge(run);
      const date = new Date(run.createdAt).toLocaleString('pt-BR');
      const download = run.downloadUrl ? `<a class="download" href="${run.downloadUrl}" target="_blank" rel="noopener">Baixar MP4</a>` : '';
      return `<div class="run"><div><div class="run-title">${escapeHtml(run.name)}</div><div class="run-meta">${date}</div><span class="badge ${cls}">${label}</span></div>${download}</div>`;
    }).join('');
  } catch (err) {
    quotaText.textContent = 'acesso/serviço indisponível';
    runsBox.innerHTML = `<p class="muted">${escapeHtml(err.message)}</p>`;
  }
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[c]));
}

$('savePinBtn').addEventListener('click', () => {
  appPin = $('pin').value.trim();
  if (!appPin) return setMessage('Digite seu PIN.', true);
  sessionStorage.setItem('shortsCloudPin', appPin);
  setMessage('PIN salvo nesta sessão.');
  refreshStatus();
});

$('ideasBtn').addEventListener('click', async () => {
  if (!appPin) return setMessage('Entre com o PIN primeiro.', true);
  const niche = $('niche').value.trim();
  if (!niche) return setMessage('Digite primeiro o nicho dos vídeos.', true);
  $('ideasBtn').disabled = true;
  setMessage('Criando três ideias diferentes…');
  try {
    const res = await fetch('/api/ideas', { method: 'POST', headers: headers({'Content-Type':'application/json'}), body: JSON.stringify({ niche }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao sugerir temas.');
    data.ideas.forEach((idea, i) => $(`topic${i + 1}`).value = idea);
    setMessage('Três ideias preenchidas. Revise se quiser e clique em Gerar.');
  } catch (err) { setMessage(err.message, true); }
  finally { $('ideasBtn').disabled = false; }
});

$('generateBtn').addEventListener('click', async () => {
  if (!appPin) return setMessage('Entre com o PIN primeiro.', true);
  const topics = [1,2,3].map(i => $(`topic${i}`).value.trim()).filter(Boolean);
  if (!topics.length) return setMessage('Preencha pelo menos um tema.', true);
  $('generateBtn').disabled = true;
  setMessage(`Enviando ${topics.length} vídeo(s) para a nuvem…`);
  try {
    const res = await fetch('/api/generate', {
      method: 'POST', headers: headers({'Content-Type':'application/json'}),
      body: JSON.stringify({ topics, duration: Number($('duration').value), style: $('style').value })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao iniciar geração.');
    setMessage(`${data.accepted.length} vídeo(s) iniciado(s). Você pode fechar esta página; o GitHub continua renderizando.`);
    setTimeout(refreshStatus, 4000);
  } catch (err) { setMessage(err.message, true); }
  finally { setTimeout(() => { $('generateBtn').disabled = false; }, 1200); }
});

$('refreshBtn').addEventListener('click', refreshStatus);
refreshStatus();
setInterval(refreshStatus, 12000);
