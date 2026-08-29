(()=>{
  const mq=window.matchMedia('(max-width: 820px)');
  const $=id=>document.getElementById(id);

  function isMobile(){return mq.matches}

  function ensurePreviewToggle(){
    const panel=document.querySelector('.preview-panel'),head=panel?.querySelector('.preview-head');
    if(!panel||!head||head.querySelector('.mobile-preview-toggle'))return;
    const btn=document.createElement('button');
    btn.type='button';
    btn.className='mobile-preview-toggle';
    btn.textContent='Ocultar prévia';
    btn.setAttribute('aria-expanded','true');
    btn.addEventListener('click',()=>{
      const collapsed=panel.classList.toggle('mobile-collapsed');
      btn.textContent=collapsed?'Mostrar prévia':'Ocultar prévia';
      btn.setAttribute('aria-expanded',String(!collapsed));
    });
    const badge=$('previewModeBadge');
    if(badge)head.insertBefore(btn,badge);else head.appendChild(btn);
  }

  function collapsePreviewAfterFirstStep(){
    if(!isMobile())return;
    const panel=document.querySelector('.preview-panel'),btn=panel?.querySelector('.mobile-preview-toggle');
    const active=document.querySelector('.stage.active');
    const step=Number(active?.dataset.stage||1);
    if(panel&&btn&&step>=2&&!panel.classList.contains('mobile-collapsed')){
      panel.classList.add('mobile-collapsed');
      btn.textContent='Mostrar prévia';
      btn.setAttribute('aria-expanded','false');
    }
  }

  function scrollToActiveStage(){
    if(!isMobile())return;
    const stage=document.querySelector('.stage.active');
    if(!stage)return;
    requestAnimationFrame(()=>stage.scrollIntoView({behavior:'smooth',block:'start'}));
  }

  function observeStages(){
    const workspace=document.querySelector('.workspace');
    if(!workspace)return;
    let last='';
    new MutationObserver(()=>{
      const active=document.querySelector('.stage.active');
      const key=active?.dataset.stage||'';
      if(!key||key===last)return;
      last=key;
      collapsePreviewAfterFirstStep();
      setTimeout(scrollToActiveStage,70);
    }).observe(workspace,{subtree:true,attributes:true,attributeFilter:['class']});
  }

  function autoGrowTextareas(){
    const grow=el=>{
      if(!isMobile()||!el.matches('textarea'))return;
      el.style.height='auto';
      el.style.height=`${Math.min(320,Math.max(el.scrollHeight,108))}px`;
    };
    document.addEventListener('input',e=>grow(e.target));
    document.querySelectorAll('textarea').forEach(grow);
    new MutationObserver(muts=>muts.forEach(m=>m.addedNodes.forEach(node=>{
      if(node.nodeType!==1)return;
      if(node.matches?.('textarea'))grow(node);
      node.querySelectorAll?.('textarea').forEach(grow);
    }))).observe(document.body,{subtree:true,childList:true});
  }

  function boot(){
    ensurePreviewToggle();
    observeStages();
    autoGrowTextareas();
    if(isMobile())setTimeout(()=>{collapsePreviewAfterFirstStep()},150);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();