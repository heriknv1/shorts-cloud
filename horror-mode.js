(()=>{
  let horrorMode='';
  const nativeFetch=window.fetch.bind(window);
  const $=id=>document.getElementById(id);
  function setMode(value){horrorMode=value||'';document.body.dataset.horrorMode=horrorMode}
  function isReal(){return horrorMode==='horror-real'}
  function isAnalog(){return horrorMode==='analog-horror'}
  async function syncPreview(){
    if(!horrorMode)return;
    const caption=$('previewCaption');if(caption)caption.textContent=isAnalog()?'ARQUIVO 07 — NÃO ASSISTA APÓS 00:00':isReal()?'Alguns dos relatos mais assustadores não nasceram da ficção.':'Às vezes, o pior não é o que você vê — é o que percebe tarde demais.';
    if($('mediaSource')?.value==='reference')return;
    const visual=$('visualStyle')?.value||'realistic',photo=$('previewPhoto'),fallback=$('previewIllustration');if(!photo||!fallback)return;fallback.hidden=true;photo.hidden=false;
    if(visual==='cartoon'){
      const style=$('cartoonStyle')?.value||'classic-2d',styleText={'classic-2d':'premium cinematic 2D suspense animation',comic:'dark cinematic graphic novel art','paper-cut':'layered atmospheric paper cut suspense illustration','retro-surreal':'retro surreal psychological suspense illustration',interdimensional:'surreal psychological suspense illustration'}[style]||'premium cinematic 2D suspense animation';
      const base=isAnalog()?'1990s analog horror emergency broadcast, red black CRT screen, VHS tracking error, ominous silhouette':isReal()?'documentary reconstruction of a documented historical mystery, eerie realistic location':'psychological horror suspense, lonely hallway at night, subtle unsettling detail';
      photo.src=`https://image.pollinations.ai/prompt/${encodeURIComponent(`${base}, low key lighting, volumetric shadows, ${styleText}, non graphic, vertical 9:16, no watermark`)}?width=512&height=910&nologo=true&seed=${isAnalog()?1997:isReal()?1900:13082026}&enhance=true`;photo.alt=isAnalog()?'Prévia de terror analógico VHS':isReal()?'Prévia de conto real de terror':'Prévia de terror e suspense';return;
    }
    try{const r=await nativeFetch(`/api/preview-media?preset=${encodeURIComponent(horrorMode)}`,{cache:'default'}),d=await r.json();if(r.ok&&horrorMode){photo.src=d.url;photo.alt=d.alt||'Prévia de suspense'}}catch{}
  }
  function select(mode){
    setMode(mode);document.querySelectorAll('.preset').forEach(b=>b.classList.toggle('active',b.dataset.preset===mode));
    if($('tone'))$('tone').value='dramatic';if($('music'))$('music').value=isAnalog()?'off':'mystery-tension';if($('musicVolumeWrap'))$('musicVolumeWrap').hidden=isAnalog();
    if(isAnalog()){
      if($('visualStyle'))$('visualStyle').value='cartoon';if($('cartoonStyle'))$('cartoonStyle').value='retro-surreal';if($('mediaMode'))$('mediaMode').value='photos';
      if($('editingPace'))$('editingPace').value='cinematic';if($('sfxMode'))$('sfxMode').value='subtle';if($('ambienceMode'))$('ambienceMode').value='subtle';if($('cleanExport'))$('cleanExport').value='off';if($('brandingMode'))$('brandingMode').value='off';
      if($('captionFont'))$('captionFont').value='Roboto';if($('captionSize'))$('captionSize').value='56';if($('captions'))$('captions').value='on';
    }
    if($('presetStatus'))$('presetStatus').textContent=isAnalog()?'Terror Analógico selecionado. O Studio criará uma fita VHS fictícia com arquivo, transmissão ou alerta perturbador, usando estética própria e identificação de ficção.':isReal()?'Terror Real selecionado. O Studio escolherá um caso real diferente, separando fatos de hipóteses. Você também pode informar um caso específico.':'Terror e Suspense selecionado. O Studio criará uma história diferente a cada roteiro, ou você pode informar um tema específico.';
    syncPreview();
  }
  function makeButton(mode,title,subtitle){const b=document.createElement('button');b.type='button';b.className='preset';b.dataset.preset=mode;b.innerHTML=`<strong>${title}</strong><span>${subtitle}</span>`;b.addEventListener('click',()=>select(mode));return b}
  function inject(){
    const grid=$('presetGrid');if(!grid)return;
    let horror=grid.querySelector('[data-preset="horror"]');if(!horror){horror=makeButton('horror','Terror e Suspense','Histórias originais • tensão psicológica e mistério');const mysteries=grid.querySelector('[data-preset="mysteries"]');if(mysteries)mysteries.insertAdjacentElement('afterend',horror);else grid.appendChild(horror)}
    if(!grid.querySelector('[data-preset="horror-real"]'))horror.insertAdjacentElement('afterend',makeButton('horror-real','Terror Real','Casos reais perturbadores • fatos e mistérios documentados'));
    const realButton=grid.querySelector('[data-preset="horror-real"]');
    if(!grid.querySelector('[data-preset="analog-horror"]'))realButton.insertAdjacentElement('afterend',makeButton('analog-horror','Terror Analógico','Fitas VHS • transmissões perdidas • ficção inquietante'));
    grid.querySelectorAll('.preset:not([data-preset="horror"]):not([data-preset="horror-real"]):not([data-preset="analog-horror"])').forEach(b=>b.addEventListener('click',()=>setMode('')));
  }
  function patchBody(body,url){
    if(!horrorMode)return body;
    try{const parsed=JSON.parse(body||'{}');parsed.presetKey=url.includes('/api/generate')&&isAnalog()?'horror':horrorMode;const sentinel=['Criar uma história original de terror e suspense','Criar um conto real de terror diferente','Criar uma fita fictícia de terror analógico'];if(sentinel.includes(parsed.topic)){parsed.topic=parsed.plan?.title||''}if((url.includes('/api/plan')||url.includes('horror-plan'))&&sentinel.includes(String(JSON.parse(body||'{}').topic||'')))parsed.topic='';return JSON.stringify(parsed)}catch{return body}
  }
  window.fetch=async function(input,init){
    const originalUrl=typeof input==='string'?input:input?.url||'';let target=input,nextInit=init;
    if(horrorMode&&init?.method==='POST'){
      if(originalUrl.includes('/api/plan'))target='/api/horror-plan';
      else if(originalUrl.includes('/api/scene-query'))target='/api/horror-scene-query';
      if(originalUrl.includes('/api/plan')||originalUrl.includes('/api/scene-query')||originalUrl.includes('/api/generate'))nextInit={...init,body:patchBody(init.body,originalUrl)};
    }
    return nativeFetch(target,nextInit);
  };
  function boot(){inject();$('planBtn')?.addEventListener('click',()=>{if(horrorMode&&!$('topic')?.value.trim())$('topic').value=isAnalog()?'Criar uma fita fictícia de terror analógico':isReal()?'Criar um conto real de terror diferente':'Criar uma história original de terror e suspense'},true);['visualStyle','mediaMode','cartoonStyle','captionFont','captionSize','captions','voicePitch','voiceSpeed','music','musicVolume'].forEach(id=>$(id)?.addEventListener('change',()=>setTimeout(syncPreview,0)));document.addEventListener('change',e=>{if(e.target?.id==='mediaSource')setTimeout(syncPreview,0)})}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
