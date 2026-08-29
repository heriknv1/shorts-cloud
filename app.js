const $ = (id) => document.getElementById(id);
const quotaText = $('quotaText');
const runsBox = $('runs');
const message = $('message');
let appPin = sessionStorage.getItem('shortsCloudPin') || '';
let currentPlan = null;
let references = [];
let selectedPresetKey = '';
$('pin').value = appPin;

const PRESETS = {
  biblical: { label:'Histórias bíblicas', duration:65, tone:'cinematic', visualStyle:'realistic', mediaMode:'photos', voice:'pm_alex', captions:'on', music:'epic-ancient', musicVolume:'low' },
  cinematic: { label:'Histórias cinematográficas', duration:65, tone:'cinematic', visualStyle:'realistic', mediaMode:'hybrid', voice:'pm_alex', captions:'on', music:'cinematic-rise', musicVolume:'low' },
  mysteries: { label:'Mistérios e curiosidades', duration:65, tone:'dramatic', visualStyle:'realistic', mediaMode:'photos', voice:'pm_santa', captions:'on', music:'mystery-tension', musicVolume:'low' },
  ancient: { label:'História antiga', duration:65, tone:'documentary', visualStyle:'realistic', mediaMode:'photos', voice:'pm_alex', captions:'on', music:'epic-ancient', musicVolume:'low' },
  motivation: { label:'Motivacional', duration:60, tone:'energetic', visualStyle:'realistic', mediaMode:'hybrid', voice:'pm_alex', captions:'on', music:'viral-pulse', musicVolume:'low' },
  science: { label:'Ciência e espaço', duration:65, tone:'documentary', visualStyle:'realistic', mediaMode:'hybrid', voice:'pm_alex', captions:'on', music:'emotional-ambient', musicVolume:'low' },
  'true-stories': { label:'Histórias reais surpreendentes', duration:65, tone:'documentary', visualStyle:'realistic', mediaMode:'photos', voice:'pf_dora', captions:'on', music:'cinematic-rise', musicVolume:'low' },
  horror: { label:'Terror e suspense', duration:65, tone:'dramatic', visualStyle:'realistic', mediaMode:'photos', voice:'pm_santa', captions:'on', music:'mystery-tension', musicVolume:'low' },
  'life-lessons': { label:'Reflexões e lições de vida', duration:60, tone:'cinematic', visualStyle:'realistic', mediaMode:'photos', voice:'pf_dora', captions:'on', music:'emotional-ambient', musicVolume:'low' },
  animals: { label:'Natureza e animais', duration:60, tone:'documentary', visualStyle:'realistic', mediaMode:'videos', voice:'pf_dora', captions:'on', music:'viral-pulse', musicVolume:'low' }
};

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
function updateConditionalFields() {
  const cartoon = $('visualStyle').value === 'cartoon';
  $('cartoonNotice').hidden = !cartoon;
  $('cartoonStyleWrap').hidden = !cartoon;
  if (cartoon) $('mediaMode').value = 'photos';
  $('musicVolumeWrap').hidden = $('music').value === 'off';
}
function applyPreset(key) {
  const p = PRESETS[key];
  if (!p) return;
  selectedPresetKey = key;
  $('duration').value = String(p.duration);
  $('tone').value = p.tone;
  $('visualStyle').value = p.visualStyle;
  $('mediaMode').value = p.mediaMode;
  $('voice').value = p.voice;
  $('captions').value = p.captions;
  $('music').value = p.music;
  $('musicVolume').value = p.musicVolume;
  [...document.querySelectorAll('.preset')].forEach(btn => btn.classList.toggle('active', btn.dataset.preset === key));
  $('presetStatus').textContent = `${p.label} selecionado — preparando tema, direção e cenas.`;
  updateConditionalFields();
}
function elapsedLabel(run) {
  if (!run.createdAt || run.status === 'completed') return '';
  const seconds = Math.max(0, Math.round((Date.now() - new Date(run.createdAt).getTime()) / 1000));
  const min = Math.floor(seconds / 60), sec = seconds % 60;
  return `${min ? `${min} min ` : ''}${sec}s`;
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
      const progress = Math.max(0, Math.min(100, Number(run.progress ?? (run.status === 'completed' ? 100 : 8))));
      const elapsed = elapsedLabel(run);
      const progressBlock = `<div class="progress-wrap"><div class="progress-head"><span>${escapeHtml(run.stage || label)}</span><strong>${progress}%</strong></div><div class="progress-track"><div class="progress-fill ${run.status === 'completed' ? 'done' : ''}" style="width:${progress}%"></div></div>${elapsed ? `<div class="progress-time">Tempo decorrido: ${elapsed} • estimativa por etapa</div>` : ''}</div>`;
      return `<div class="run"><div><div class="run-title">${escapeHtml(run.name)}</div><div class="run-meta">${date}</div><span class="badge ${cls}">${label}</span>${progressBlock}</div>${download}</div>`;
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

$('visualStyle').addEventListener('change', updateConditionalFields);
$('mediaMode').addEventListener('change', () => {
  if ($('visualStyle').value === 'cartoon' && $('mediaMode').value !== 'photos') $('mediaMode').value = 'photos';
});
$('music').addEventListener('change', updateConditionalFields);
updateConditionalFields();

$('ideasBtn').addEventListener('click', async () => {
  if (!appPin) return setMessage('Entre com o PIN primeiro.', true);
  const niche = $('niche').value.trim();
  if (!niche) return setMessage('Digite o nicho primeiro.', true);
  selectedPresetKey = '';
  [...document.querySelectorAll('.preset')].forEach(btn => btn.classList.remove('active'));
  $('presetStatus').textContent = 'Modo personalizado ativo.';
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
    for (const file of files) references.push({ name: file.name, dataUrl: await compressImage(file) });
    $('referencePreview').innerHTML = references.map((r, i) => `<div class="reference-item"><img src="${r.dataUrl}" alt="Referência ${i+1}"><span>Ref. ${i+1}</span></div>`).join('');
    if (references.length) setMessage(`${references.length} referência(s) pronta(s) para análise visual.`);
  } catch (err) { setMessage(err.message, true); }
});

function renderPlan(plan) {
  currentPlan = plan;
  if (!$('topic').value.trim()) $('topic').value = plan.title || '';
  $('planTitle').textContent = plan.title || 'Plano do vídeo';
  $('planSummary').textContent = plan.summary || '';
  $('sceneEditor').innerHTML = plan.scenes.map((scene, i) => `
    <article class="scene" data-index="${i}">
      <div class="scene-head"><span class="scene-number">${i+1}</span><div class="scene-title">${escapeHtml(scene.beat || `Cena ${i+1}`)}</div><span class="badge">${escapeHtml(scene.recommended_media || 'image')}</span></div>
      <div class="scene-grid">
        <div><label>Fala</label><textarea class="scene-narration">${escapeHtml(scene.narration || '')}</textarea></div>
        <div><label>O que deve aparecer</label><textarea class="scene-visual visual">${escapeHtml(scene.visual_description || '')}</textarea></div>
      </div>
      <label>Busca visual principal em inglês</label><input class="scene-query query" value="${escapeHtml(scene.visual_query || '')}" />
      <label>Busca alternativa</label><input class="scene-query-backup query" value="${escapeHtml(scene.visual_query_backup || '')}" />
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
    plan.scenes[i].visual_query_backup = el.querySelector('.scene-query-backup').value.trim();
  });
  return plan;
}

async function createPlan({auto = false} = {}) {
  if (!appPin) return setMessage('Entre com o PIN primeiro.', true);
  const topic = $('topic').value.trim();
  if (!topic && !selectedPresetKey) return setMessage('Digite o tema do vídeo ou escolha um nicho pronto.', true);
  $('planBtn').disabled = true;
  [...document.querySelectorAll('.preset')].forEach(btn => btn.disabled = auto);
  currentPlan = null;
  $('planSection').hidden = true;
  setMessage(auto ? 'Nicho escolhido. Criando automaticamente o tema, a direção e as cenas…' : (references.length ? 'Analisando referências e construindo a história cena por cena…' : 'Construindo a história cena por cena…'));
  try {
    const payload = {
      topic,
      presetKey: selectedPresetKey,
      duration: Number($('duration').value),
      tone: $('tone').value,
      visualStyle: $('visualStyle').value,
      cartoonStyle: $('cartoonStyle').value,
      mediaMode: $('mediaMode').value,
      references
    };
    const res = await fetch('/api/plan', { method: 'POST', headers: headers({'Content-Type':'application/json'}), body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao criar plano.');
    renderPlan(data.plan);
    setMessage(auto ? 'Tudo preparado em um clique. Revise o plano e, quando quiser, aprove o MP4.' : 'Plano criado sem renderizar. Revise as cenas e só então aprove o MP4.');
  } catch (err) { setMessage(err.message, true); }
  finally {
    $('planBtn').disabled = false;
    [...document.querySelectorAll('.preset')].forEach(btn => btn.disabled = false);
  }
}

[...document.querySelectorAll('.preset')].forEach(btn => btn.addEventListener('click', async () => {
  if (!appPin) return setMessage('Entre com o PIN primeiro.', true);
  applyPreset(btn.dataset.preset);
  $('topic').value = '';
  $('ideaChips').innerHTML = '';
  await createPlan({ auto: true });
}));

$('planBtn').addEventListener('click', () => createPlan({ auto: false }));

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
        topic: $('topic').value.trim() || approvedPlan.title,
        presetKey: selectedPresetKey,
        plan: approvedPlan,
        duration: Number($('duration').value),
        tone: $('tone').value,
        visualStyle: $('visualStyle').value,
        cartoonStyle: $('cartoonStyle').value,
        mediaMode: $('mediaMode').value,
        voice: $('voice').value,
        captions: $('captions').value,
        music: $('music').value,
        musicVolume: $('musicVolume').value
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Falha ao iniciar geração.');
    setMessage('Renderização iniciada. A barra de progresso aparecerá no histórico e continuará atualizando.');
    setTimeout(refreshStatus, 2500);
  } catch (err) { setMessage(err.message, true); }
  finally { setTimeout(() => refreshStatus(), 1200); }
});

$('refreshBtn').addEventListener('click', refreshStatus);
refreshStatus();
setInterval(refreshStatus, 8000);
