import { put } from '@vercel/blob/client';

(() => {
  const $ = id => document.getElementById(id);
  const MAX_MB = 200;
  const MAX_BYTES = MAX_MB * 1024 * 1024;
  const LIMIT = 12;
  const PLAN_KEY = 'short-cloud-scale-publication-plan-v1';
  const state = {file:null, mime:'', url:'', sourcePathname:'', template:'impact', busy:false, duration:0, historyTimer:null};
  const el = {
    file:$('scaleFile'), info:$('scaleFileInfo'), video:$('scalePreviewVideo'),
    start:$('scaleStart'), end:$('scaleEnd'), framing:$('scaleFraming'), titles:$('scaleHeadlines'),
    topic:$('scaleTopic'), generate:$('scaleGenerate'), suggest:$('scaleSuggest'), count:$('scaleCount'),
    notice:$('scaleNotice'), history:$('scaleHistory'), planned:$('scalePlanned')
  };
  function notice(message, type='') {
    el.notice.textContent = String(message || '');
    el.notice.hidden = !message;
    el.notice.className = 'scale-notice' + (type ? ' ' + type : '');
    if (type === 'error') el.notice.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  function isBusy(value) {
    state.busy = value;
    el.generate.disabled = value;
    el.suggest.disabled = value;
    el.file.disabled = value;
    el.generate.querySelector('span').textContent = value ? '…' : '→';
  }
  function request(url, options) {
    return fetch(url, {credentials:'same-origin',cache:'no-store',...options}).then(async response => {
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw Error(data.error || 'Não foi possível completar a operação.');
      return data;
    });
  }
  function panes(id) {
    document.querySelectorAll('.scale-nav [data-pane]').forEach(b => b.classList.toggle('is-active', b.dataset.pane === id));
    document.querySelectorAll('[data-pane-panel]').forEach(p => p.classList.toggle('is-active',p.dataset.panePanel === id));
    if (id === 'history') refreshHistory();
    if (id === 'calendar') renderPosts();
    window.scrollTo({top:0,behavior:'smooth'});
  }
  function getTitles() {
    return [...new Set(el.titles.value.split(/\r?\n/).map(s => s.replace(/\s+/g,' ').trim()).filter(Boolean))].slice(0,LIMIT);
  }
  function updateCount() {
    const lines = el.titles.value.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    el.count.textContent = lines.length + ' de ' + LIMIT + ' versões • cada linha vira um vídeo' + (lines.length > LIMIT ? ' — máximo excedido!' : '');
    el.count.style.color = lines.length > LIMIT ? '#ffabb7' : '';
    updatePreview();
  }
  function updatePreview() {
    const title = getTitles()[0] || 'SEU TÍTULO';
    const top = $('scalePreviewTop'), bottom = $('scalePreviewBottom'), news = $('scalePreviewNews');
    top.hidden = state.template === 'minimal';
    bottom.hidden = state.template !== 'minimal';
    news.hidden = state.template !== 'news';
    top.textContent = title;
    bottom.textContent = title;
    $('scalePhone').classList.toggle('video-fit',el.framing.value === 'fit');
    const accent = $('scaleAccent').value;
    top.style.borderColor = accent;
    news.style.background = accent;
    const scale = {small:'14px',medium:'18px',large:'21px'}[$('scaleSize').value] || '18px';
    top.style.fontSize = scale;
    bottom.style.fontSize = scale;
  }
  function guessMime(file) {
    const known = {
      mp4:'video/mp4',mov:'video/quicktime',webm:'video/webm',m4v:'video/x-m4v',
      mpg:'video/mpeg',mpeg:'video/mpeg',ogv:'video/ogg',3gp:'video/3gpp',mkv:'video/x-matroska'
    };
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    return known[ext] || file.type;
  }
  function safeName(name) {
    return String(name || 'video.mp4').normalize('NFD').replace(/[\u0300-\u036f]/g,'')
      .replace(/[^a-zA-Z0-9._-]/g,'-').slice(-95) || 'video.mp4';
  }
  function onFile() {
    const file = el.file.files?.[0];
    if (state.url) URL.revokeObjectURL(state.url);
    state.file = null;
    state.sourcePathname = '';
    state.duration = 0;
    el.video.hidden = true;
    el.video.removeAttribute('src');
    $('scalePreviewEmpty').hidden = false;
    el.info.hidden = true;
    if (!file) return;
    const mime = guessMime(file);
    if (!mime.startsWith('video/') || file.size > MAX_BYTES || file.size < 1024) {
      notice('Escolha um vídeo de formato válido, com até 200 MB.', 'error');
      el.file.value = '';
      return;
    }
    state.file = file;
    state.mime = mime;
    state.url = URL.createObjectURL(file);
    el.video.src = state.url;
    el.video.hidden = false;
    $('scalePreviewEmpty').hidden = true;
    $('scaleFileTitle').textContent = file.name;
    el.info.hidden = false;
    el.info.textContent = file.name + ' · ' + (file.size / (1024*1024)).toFixed(1) + ' MB';
    el.video.onloadedmetadata = () => {
      const duration = el.video.duration;
      if (Number.isFinite(duration) && duration >= 2) {
        state.duration = duration;
        el.start.value = '0';
        el.end.value = Math.min(120, duration).toFixed(1);
        el.end.max = String(duration);
        el.info.textContent += ' · ' + Math.round(duration) + ' segundos';
      } else {
        notice('Não consegui determinar a duração. Informe manualmente o segundo final.', 'error');
      }
    };
    el.video.onerror = () => {
      el.video.hidden = true;
      $('scalePreviewEmpty').hidden = false;
      $('scalePreviewEmpty').textContent = 'A prévia deste formato não está disponível no navegador. O arquivo ainda pode ser processado.';
    };
    notice('');
  }
  async function uploadFile() {
    if (state.sourcePathname) return state.sourcePathname;
    if (!state.file) throw Error('Escolha um arquivo original.');
    const file = state.file;
    const filename = 'illustrated-inputs/scale-' + Date.now() + '-' + safeName(file.name);
    notice('Autorizando upload privado...');
    const tokenData = await request('/api/source-upload',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({type:'blob.generate-client-token',payload:{
        pathname:filename,clientPayload:null,multipart:file.size > 5*1024*1024
      }})
    });
    if (!String(tokenData.clientToken || '').startsWith('vercel_blob_client_')) {
      throw Error('O armazenamento não devolveu uma autorização válida.');
    }
    const uploadable = file.type === state.mime ? file : new File([file],file.name,{type:state.mime});
    const result = await put(filename,uploadable,{
      access:'private',token:tokenData.clientToken,multipart:file.size > 5*1024*1024,
      onUploadProgress:progress => notice('Enviando vídeo privado: ' + Math.round(progress.percentage || 0) + '%')
    });
    if (!result.pathname) throw Error('O upload não retornou o identificador do arquivo.');
    state.sourcePathname = result.pathname;
    return result.pathname;
  }
  async function generate() {
    if (state.busy) return;
    const titles = getTitles();
    const start = Number(el.start.value), end = Number(el.end.value);
    if (!state.file) return notice('Escolha um vídeo original.', 'error');
    if (!titles.length || el.titles.value.split(/\r?\n/).filter(v => v.trim()).length > LIMIT) return notice('Informe entre 1 e 12 títulos, um por linha.', 'error');
    if (!el.end.value.trim() || !Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end - start < 2 || end - start > 120 || (state.duration && end > state.duration + .3)) return notice('Defina um trecho válido de 2 a 120 segundos, dentro da duração do vídeo.', 'error');
    if (!$('scaleRights').checked || !$('scalePublic').checked) return notice('Marque as duas confirmações de direitos e privacidade.', 'error');
    isBusy(true);
    try {
      await uploadFile();
      notice('Enviando lote para renderização na nuvem...');
      const result = await request('/api/scale',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          action:'generate',sourcePathname:state.sourcePathname,sourceMime:state.mime,
          sourceName:state.file.name,topic:el.topic.value.trim(),titles,
          template:state.template,framing:el.framing.value,
          accent:$('scaleAccent').value,textSize:$('scaleSize').value,
          startAt:start,endAt:end,rightsConfirmed:true,publicReleaseAcknowledged:true
        })
      });
      notice('Lote enviado com sucesso! ' + result.count + ' variações serão produzidas. Acompanhe na aba Criações e downloads.', 'ok');
      panes('history');
    } catch (error) {
      notice(error.message || 'Não foi possível iniciar a criação.', 'error');
    } finally { isBusy(false); }
  }
  async function suggest() {
    if (state.busy) return;
    const topic = el.topic.value.trim() || getTitles()[0] || '';
    if (topic.length < 6) return notice('Escreva o assunto do vídeo para receber sugestões da IA.', 'error');
    isBusy(true);
    try {
      notice('Gerando títulos alternativos com IA...');
      const data = await request('/api/scale',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'suggest',topic,count:8})});
      if (!Array.isArray(data.titles) || !data.titles.length) throw Error('A IA não retornou sugestões.');
      el.titles.value = data.titles.join('\n');
      updateCount();
      notice(data.titles.length + ' títulos sugeridos. Revise os textos antes de gerar.', 'ok');
    } catch (error) {
      notice(error.message || 'Falha ao sugerir títulos.', 'error');
    } finally { isBusy(false); }
  }
  function create(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function safeHref(href) {
    try {
      const u = new URL(String(href),location.origin);
      return u.protocol === 'https:' && (u.hostname === 'github.com' || u.hostname === 'www.github.com') ? u.href : '';
    } catch {return '';}
  }
  async function refreshHistory() {
    try {
      const data = await request('/api/scale');
      el.history.replaceChildren();
      if (!data.items?.length) {
        el.history.appendChild(create('p','scale-help','Nenhum lote criado até agora. Comece pela aba Multiplicar vídeos.'));
        return;
      }
      data.items.forEach(job => {
        const item = create('article','scale-job');
        const head = create('div','scale-job-head');
        const label = create('div');
        label.appendChild(create('h3','', 'Lote #' + job.id));
        label.appendChild(create('p','scale-help',new Date(job.createdAt).toLocaleString('pt-BR')));
        const completed = job.status === 'completed';
        const success = completed && job.conclusion === 'success';
        head.append(label, create('span','scale-job-state' + (success ? ' good' : completed ? ' bad' : ''),success ? 'Concluído' : completed ? 'Falhou ou cancelado' : 'Processando'));
        item.appendChild(head);
        const links = create('div','scale-job-links');
        (job.assets || []).forEach((asset,index) => {
          const href = safeHref(asset.url);
          if (!href) return;
          const anchor = create('a','', 'Baixar MP4 ' + (index + 1));
          anchor.href = href;anchor.target = '_blank';anchor.rel = 'noopener noreferrer';
          anchor.title = String(asset.name || '');
          links.appendChild(anchor);
        });
        if (safeHref(job.releaseUrl)) {
          const a = create('a','','Ver lote completo');a.href = safeHref(job.releaseUrl);a.target = '_blank';a.rel = 'noopener noreferrer';links.appendChild(a);
        }
        if (safeHref(job.logsUrl) && !success) {
          const a = create('a','','Ver execução');a.href = safeHref(job.logsUrl);a.target = '_blank';a.rel = 'noopener noreferrer';links.appendChild(a);
        }
        if (completed && success && !job.assets?.length) item.appendChild(create('p','scale-help','Finalizado. Os arquivos podem ainda estar sendo publicados no GitHub.'));
        if (!completed) item.appendChild(create('p','scale-help','O processamento acontece no GitHub Actions. Atualize para consultar o andamento.'));
        item.appendChild(links);
        el.history.appendChild(item);
      });
    } catch (error) {
      el.history.replaceChildren(create('p','scale-help',error.message || 'Histórico indisponível.'));
    }
  }
  function getPosts() {
    try {
      const data = JSON.parse(localStorage.getItem(PLAN_KEY) || '[]');
      return Array.isArray(data) ? data.slice(0,100) : [];
    } catch { return []; }
  }
  function putPosts(items) {
    try { localStorage.setItem(PLAN_KEY,JSON.stringify(items.slice(0,100)));return true;}
    catch {notice('O navegador não permitiu salvar o planejamento.','error');return false;}
  }
  function renderPosts() {
    el.planned.replaceChildren();
    const posts = getPosts().sort((a,b) => a.date.localeCompare(b.date));
    if (!posts.length) return el.planned.appendChild(create('p','scale-help','Nenhuma publicação planejada.'));
    posts.forEach(post => {
      const card = create('article','scale-post');
      const summary = create('div');
      summary.append(create('strong','',post.title),create('small','',post.network + ' · ' + new Date(post.date).toLocaleString('pt-BR')));
      const actions = create('div','scale-job-links');
      const copy = create('button','scale-secondary','Copiar legenda');
      copy.type = 'button';
      copy.addEventListener('click',async () => {
        try {await navigator.clipboard.writeText(post.caption || post.title);notice('Legenda copiada.','ok');}
        catch {notice('Não foi possível copiar automaticamente.','error');}
      });
      const del = create('button','scale-secondary','Excluir');
      del.type = 'button';
      del.addEventListener('click',() => {putPosts(getPosts().filter(x => x.id !== post.id));renderPosts();});
      actions.append(copy,del);
      card.append(summary,actions);el.planned.appendChild(card);
    });
  }
  function savePost() {
    const title = $('scalePostTitle').value.trim().slice(0,160);
    const date = $('scalePostDate').value;
    if (!title || !date || Number.isNaN(new Date(date).getTime())) return notice('Informe título, data e horário da publicação.','error');
    const posts = getPosts();
    posts.unshift({id:Date.now().toString() + Math.random().toString(36).slice(2,6),
      title,network:$('scaleNetwork').value,date,caption:$('scalePostCaption').value.slice(0,2000)});
    if (putPosts(posts)) {renderPosts();notice('Planejamento salvo neste navegador. A publicação será manual.','ok');$('scalePostTitle').value='';$('scalePostCaption').value='';}
  }
  document.querySelectorAll('.scale-nav [data-pane]').forEach(b => b.addEventListener('click',() => panes(b.dataset.pane)));
  document.querySelectorAll('.scale-template').forEach(b => b.addEventListener('click',() => {
    state.template = b.dataset.template;
    document.querySelectorAll('.scale-template').forEach(x => {x.classList.toggle('selected',x === b);x.setAttribute('aria-pressed',String(x === b));});
    updatePreview();
  }));
  el.file.addEventListener('change',onFile);
  el.titles.addEventListener('input',updateCount);
  el.framing.addEventListener('change',updatePreview);
  $('scaleAccent').addEventListener('input',updatePreview);
  $('scaleSize').addEventListener('change',updatePreview);
  el.generate.addEventListener('click',generate);
  el.suggest.addEventListener('click',suggest);
  $('scaleRefresh').addEventListener('click',refreshHistory);
  $('scaleSavePost').addEventListener('click',savePost);
  document.addEventListener('visibilitychange',() => {if (!document.hidden && document.querySelector('[data-pane-panel="history"].is-active')) refreshHistory();});
  window.setInterval(() => {if (!document.hidden && document.querySelector('[data-pane-panel="history"].is-active')) refreshHistory();},25000);
  window.addEventListener('pagehide',() => {if (state.url) URL.revokeObjectURL(state.url);});
  updateCount();
})();
