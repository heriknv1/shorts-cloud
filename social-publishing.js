(()=>{
  const STORAGE='short-cloud-social-copy-v1';
  const nativeFetch=window.fetch.bind(window);
  const $=id=>document.getElementById(id);
  let current=null;

  function save(data){current=data;try{localStorage.setItem(STORAGE,JSON.stringify(data))}catch{}}
  function load(){try{return JSON.parse(localStorage.getItem(STORAGE)||'null')}catch{return null}}
  async function copy(text,button){
    try{await navigator.clipboard.writeText(String(text||''));const old=button.textContent;button.textContent='Copiado';setTimeout(()=>button.textContent=old,1200)}catch{button.textContent='Selecione e copie'}
  }
  function showStage(){
    document.querySelectorAll('.stage').forEach(s=>s.classList.remove('active'));
    document.querySelectorAll('.step-tab').forEach(b=>b.classList.remove('active'));
    $('socialStage')?.classList.add('active');$('socialTab')?.classList.add('active');window.scrollTo({top:0,behavior:'smooth'});
  }
  function back(){
    $('socialStage')?.classList.remove('active');$('socialTab')?.classList.remove('active');
    document.querySelector('[data-stage="4"]')?.classList.add('active');document.querySelector('.step-tab[data-step="4"]')?.classList.add('active');window.scrollTo({top:0,behavior:'smooth'});
  }
  function render(data){
    if(!data)return;
    save(data);
    $('socialEmpty')?.setAttribute('hidden','');
    const content=$('socialContent');if(content)content.hidden=false;
    if($('socialTitle'))$('socialTitle').value=data.title||'';
    if($('socialTikTok'))$('socialTikTok').value=data.tiktok||'';
    if($('socialInstagram'))$('socialInstagram').value=data.instagram||'';
    if($('socialHashtags'))$('socialHashtags').value=(data.hashtags||[]).join(' ');
    if($('socialPinned'))$('socialPinned').value=data.pinned_comment||'';
    const open=$('openSocialStage');if(open){open.hidden=false;open.textContent='Abrir textos para redes sociais'}
  }
  function inject(){
    const stepper=document.querySelector('.stepper');if(stepper&&!$('socialTab')){
      const tab=document.createElement('button');tab.className='step-tab';tab.id='socialTab';tab.dataset.step='5';tab.innerHTML='<span>5</span><b>Publicação</b>';tab.addEventListener('click',()=>{if(current)showStage()});stepper.appendChild(tab);
    }
    const workspace=document.querySelector('.workspace');if(workspace&&!$('socialStage')){
      const stage=document.createElement('div');stage.className='stage';stage.id='socialStage';stage.dataset.stage='5';
      stage.innerHTML=`<div class="stage-head"><div><span class="eyebrow">Etapa 5</span><h2>Pronto para publicar</h2></div><span class="stage-tip">Copie e cole na rede social.</span></div>
      <div id="socialEmpty" class="notice">Os textos serão criados automaticamente quando você iniciar a geração do vídeo.</div>
      <div id="socialContent" hidden>
        <div class="social-copy-card"><div class="social-copy-head"><div><span class="eyebrow">Título</span><h3>Título sugerido</h3></div><button class="ghost social-copy-btn" data-target="socialTitle">Copiar</button></div><textarea id="socialTitle" rows="2" readonly></textarea></div>
        <div class="social-copy-card"><div class="social-copy-head"><div><span class="eyebrow">TikTok</span><h3>Legenda pronta</h3></div><button class="ghost social-copy-btn" data-target="socialTikTok">Copiar</button></div><textarea id="socialTikTok" rows="8" readonly></textarea></div>
        <div class="social-copy-card"><div class="social-copy-head"><div><span class="eyebrow">Instagram Reels</span><h3>Legenda pronta</h3></div><button class="ghost social-copy-btn" data-target="socialInstagram">Copiar</button></div><textarea id="socialInstagram" rows="10" readonly></textarea></div>
        <div class="social-copy-card"><div class="social-copy-head"><div><span class="eyebrow">Hashtags</span><h3>Hashtags recomendadas</h3></div><button class="ghost social-copy-btn" data-target="socialHashtags">Copiar</button></div><textarea id="socialHashtags" rows="3" readonly></textarea></div>
        <div class="social-copy-card"><div class="social-copy-head"><div><span class="eyebrow">Engajamento</span><h3>Comentário fixado sugerido</h3></div><button class="ghost social-copy-btn" data-target="socialPinned">Copiar</button></div><textarea id="socialPinned" rows="3" readonly></textarea></div>
        <div class="notice">Os textos são adaptados ao conteúdo para despertar curiosidade de forma coerente e incentivar conversa genuína.</div>
      </div><div class="stage-actions"><button class="ghost" id="socialBack">Voltar para geração</button><span></span></div>`;
      workspace.appendChild(stage);
      stage.querySelectorAll('.social-copy-btn').forEach(b=>b.addEventListener('click',()=>copy($(b.dataset.target)?.value,b)));
      $('socialBack')?.addEventListener('click',back);
    }
    const panel=document.querySelector('[data-stage="4"] .generate-panel');if(panel&&!$('openSocialStage')){
      const b=document.createElement('button');b.id='openSocialStage';b.className='ghost';b.hidden=true;b.textContent='Abrir textos para redes sociais';b.addEventListener('click',showStage);panel.appendChild(b);
    }
    if(!$('socialPublishingStyles')){
      const style=document.createElement('style');style.id='socialPublishingStyles';style.textContent='.social-copy-card{margin:14px 0;padding:16px;border:1px solid rgba(255,255,255,.09);border-radius:16px;background:rgba(255,255,255,.025)}.social-copy-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px}.social-copy-card h3{margin:3px 0 0}.social-copy-card textarea{width:100%;resize:vertical;min-height:62px}';document.head.appendChild(style);
    }
    const remembered=load();if(remembered)render(remembered);
  }

  window.fetch=async function(input,init){
    const url=typeof input==='string'?input:input?.url||'';const response=await nativeFetch(input,init);
    if(init?.method==='POST'&&url.includes('/api/generate')&&response.ok){
      response.clone().json().then(d=>{if(d?.social){render(d.social);setTimeout(showStage,250)}}).catch(()=>{});
    }
    return response;
  };

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',inject,{once:true});else inject();
})();