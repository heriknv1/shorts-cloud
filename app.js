const $ = (id) => document.getElementById(id);
const quotaText = $('quotaText');
const runsBox = $('runs');
const message = $('message');
let appPin = sessionStorage.getItem('shortsCloudPin') || '';
let currentPlan = null;
let references = [];
$('pin').value = appPin;

function headers(extra = {}) { return { 'X-App-Pin': appPin, ...extra }; }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[c])); }
function setMessage(text, error = false) {
  message.hidden = !text;
  message.textContent = text;
  message.style.borderColor = error ? '#6d3030' : '#2d3a50';
  message.style.color = error ? '#ffb4b4' : '';
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
    $('generateBtn').disabled = data.remaining <= 0 || !currentPlan;
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
    quotaText.textContent = 'serviço indisponível';
    runsBox.innerHTML = `<p class="muted">${escapeHtml(err.message)}</p>`;
  }
}

$('savePinBtn').addEventListener('click', () => {
  appPin = $('pin').value.trim();
  if (!appPin) return setMessage('Digite seu PIN.', true);
  sessionStorage.setItem('shortsCloudPin', appPin);
  setMessage('Acesso salvo nesta sessão.');
  refreshStatus();
});

$('visualStyle').addEventListener('change', () => {
  const cartoon = $('visualStyle').value === 'cartoon';
  $('cartoonNotice').hidden = !cartoon;
  if (cartoon) $('mediaMode').value = 'photos';
});
$('mediaMode').addEventListener('change', () => {
  if ($('visualStyle').value === 'cartoon' && $('mediaMode').value !== 'photos') {
    $('mediaMode').value = 'photos';
    $('cartoonNotice').hidden = false;
  }
});

$('ideasBtn').addEventListener('click', async () => {
  if (!appPin) return setMessage('Entre com o PIN primeiro.', true);
  const niche = $('niche').value.trim();
  if (!niche) return setMessage('Digite o nicho primeiro.', true);
  $('ideasBtn').disabled = true;
  setMessage('Criando três ideias diferentes…');
  try {
    const res = await fetch('/api/ideas', { method: 'POST', headers: headers({'Content-Type':'application/json'}), body: JSON.stringify({ niche }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao sugerir temas.');
    $('ideaChips').innerHTML = data.ideas.map((idea, i) => `<button class="chip" data-idea="${i}">${escapeHtml(idea)}</button>`).join('');
    [...$('ideaChips').querySelectorAll('.chip')].forEach((btn, i) => btn.addEventListener('click', () => { $('topic').value = data.ideas[i]; }));
    setMessage('Escolha uma das sugestões ou escreva seu próprio tema.');
  } catch (err) { setMessage(err.message, true); }
  finally { $('ideasBtn').disabled = false; }
});

async function compressImage(file) {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) throw new Error('Use apenas JPG, PNG ou WEBP.');
  const bitmap = await createImageBitmap(file);
  const max = 900;
  const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  const ctx = canvas.getContext('2d');
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return canvas.toDataURL('image/jpeg', .72);
}

$('references').addEventListener('change', async (event) => {
  const files = [...event.target.files].slice(0, 3);
  references = [];
  $('referencePreview').innerHTML = '';
  try {
    for (const file of files) {
      const dataUrl = await compressImage(file);
      references.push({ name: file.name, dataUrl });
    }
    $('referencePreview').innerHTML = references.map((r, i) => `<div class="reference-item"><img src="${r.dataUrl}" alt="Referência ${i+1}"><span>Ref. ${i+1}</span></div>`).join('');
    if (references.length) setMessage(`${references.length} referência(s) pronta(s) para análise visual.`);
  } catch (err) { setMessage(err.message, true); }
});

function renderPlan(plan) {
  currentPlan = plan;
  $('planTitle').textContent = plan.title || 'Plano do vídeo';
  $('planSummary').textContent = plan.summary || '';
  $('sceneEditor').innerHTML = plan.scenes.map((scene, i) => `
    <article class="scene" data-index="${i}">
      <div class="scene-head"><span class="scene-number">${i+1}</span><div class="scene-title">${escapeHtml(scene.beat || `Cena ${i+1}`)}</div><span class="badge">${escapeHtml(scene.recommended_media || 'image')}</span></div>
      <div class="scene-grid">
        <div><label>Fala</label><textarea class="scene-narration">${escapeHtml(scene.narration || '')}</textarea></div>
        <div><label>O que deve aparecer</label><textarea class="scene-visual visual">${escapeHtml(scene.visual_description || '')}</textarea></div>
      </div>
      <label>Busca visual em inglês</label>
      <input class="scene-query query" value="${escapeHtml(scene.visual_query || '')}" />
    </article>`).join('');
  $('planSection').hidden = false;
  $('planSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
  refreshStatus();
}

function collectEditedPlan() {
  const plan = JSON.parse(JSON.stringify(currentPlan));
  [...$('sceneEditor').querySelectorAll('.scene')].forEach((el, i) => {
    plan.scenes[i].narration = el.querySelector('.scene-narration').value.trim();
    plan.scenes[i].visual_description = el.querySelector('.scene-visual').value.trim();
    plan.scenes[i].visual_query = el.querySelector('.scene-query').value.trim();
  });
  return plan;
}

$('planBtn').addEventListener('click', async () => {
  if (!appPin) return setMessage('Entre com o PIN primeiro.', true);
  const topic = $('topic').value.trim();
  if (!topic) return setMessage('Digite o tema do vídeo.', true);
  $('planBtn').disabled = true;
  currentPlan = null;
  $('planSection').hidden = true;
  setMessage(references.length ? 'Analisando referências e construindo a história cena por cena…' : 'Construindo a história cena por cena…');
  try {
    const payload = {
      topic,
      duration: Number($('duration').value),
      tone: $('tone').value,
      visualStyle: $('visualStyle').value,
      mediaMode: $('mediaMode').value,
      references
    };
    const res = await fetch('/api/plan', { method: 'POST', headers: headers({'Content-Type':'application/json'}), body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao criar plano.');
    renderPlan(data.plan);
    setMessage('Plano criado sem renderizar. Revise as cenas e só então aprove o MP4.');
  } catch (err) { setMessage(err.message, true); }
  finally { $('planBtn').disabled = false; }
});

$('generateBtn').addEventListener('click', async () => {
  if (!appPin) return setMessage('Entre com o PIN primeiro.', true);
  if (!currentPlan) return setMessage('Crie e revise o plano primeiro.', true);
  const approvedPlan = collectEditedPlan();
  if (approvedPlan.scenes.some(s => !s.narration || !s.visual_query)) return setMessage('Há cena sem fala ou sem busca visual.', true);
  $('generateBtn').disabled = true;
  setMessage('Plano aprovado. Enviando a renderização para o GitHub…');
  try {
    const res = await fetch('/api/generate', {
      method: 'POST', headers: headers({'Content-Type':'application/json'}),
      body: JSON.stringify({
        topic: $('topic').value.trim(),
        plan: approvedPlan,
        duration: Number($('duration').value),
        tone: $('tone').value,
        visualStyle: $('visualStyle').value,
        mediaMode: $('mediaMode').value,
        voice: $('voice').value,
        captions: $('captions').value
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao iniciar geração.');
    setMessage('Renderização iniciada. Você pode fechar a página; o GitHub continua trabalhando na nuvem.');
    setTimeout(refreshStatus, 3500);
  } catch (err) { setMessage(err.message, true); }
  finally { setTimeout(() => refreshStatus(), 1200); }
});

$('refreshBtn').addEventListener('click', refreshStatus);
refreshStatus();
setInterval(refreshStatus, 12000);
