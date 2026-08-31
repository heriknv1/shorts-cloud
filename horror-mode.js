(()=>{
  let horrorSelected=false;
  const nativeFetch=window.fetch.bind(window);
  const $=id=>document.getElementById(id);

  function setHorrorSelected(value){
    horrorSelected=!!value;
    document.body.dataset.horrorMode=horrorSelected?'1':'0';
  }

  async function syncHorrorPreview(){
    if(!horrorSelected)return;
    const caption=$('previewCaption');
    if(caption)caption.textContent='Às vezes, o pior não é o que você vê — é o que percebe tarde demais.';
    const refMode=$('mediaSource')?.value==='reference';
    if(refMode)return;
    const visual=$('visualStyle')?.value||'realistic';
    const photo=$('previewPhoto'),fallback=$('previewIllustration');
    if(!photo||!fallback)return;
    fallback.hidden=true;photo.hidden=false;
    if(visual==='cartoon'){
      const style=$('cartoonStyle')?.value||'classic-2d';
      const styleText={
        'classic-2d':'premium cinematic 2D horror animation',
        comic:'dark cinematic graphic novel art',
        'paper-cut':'layered atmospheric paper cut horror illustration',
        'retro-surreal':'retro surreal psychological horror illustration',
        interdimensional:'surreal cosmic psychological horror illustration'
      }[style]||'premium cinematic 2D horror animation';
      const prompt=`psychological horror suspense, lonely hallway at night, subtle unsettling detail, low key lighting, volumetric shadows, ${styleText}, non graphic, vertical 9:16, no text, no watermark`;
      photo.src=`https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=512&height=910&nologo=true&seed=13082026&enhance=true`;
      photo.alt='Prévia de terror e suspense';
      return;
    }
    try{
      const r=await nativeFetch('/api/preview-media?preset=horror',{cache:'default'}),d=await r.json();
      if(r.ok&&horrorSelected){photo.src=d.url;photo.alt=d.alt||'Prévia de terror e suspense'}
    }catch{}
  }

  function selectHorror(){
    setHorrorSelected(true);
    document.querySelectorAll('.preset').forEach(b=>b.classList.toggle('active',b.dataset.preset==='horror'));
    if($('tone'))$('tone').value='dramatic';
    if($('music'))$('music').value='mystery-tension';
    if($('musicVolumeWrap'))$('musicVolumeWrap').hidden=false;
    if($('presetStatus'))$('presetStatus').textContent='Terror e Suspense selecionado. Você pode escrever uma história específica ou deixar o Studio criar uma situação original.';
    syncHorrorPreview();
  }

  function injectPreset(){
    const grid=$('presetGrid');
    if(!grid||grid.querySelector('[data-preset="horror"]'))return;
    const button=document.createElement('button');
    button.type='button';button.className='preset';button.dataset.preset='horror';
    button.innerHTML='<strong>Terror e Suspense</strong><span>Tensão psicológica, mistério e histórias assustadoras</span>';
    const mysteries=grid.querySelector('[data-preset="mysteries"]');
    if(mysteries)mysteries.insertAdjacentElement('afterend',button);else grid.appendChild(button);
    button.addEventListener('click',selectHorror);
    grid.querySelectorAll('.preset:not([data-preset="horror"])').forEach(b=>b.addEventListener('click',()=>setHorrorSelected(false)));
  }

  function patchBody(body){
    if(!horrorSelected)return body;
    try{
      const parsed=JSON.parse(body||'{}');
      parsed.presetKey='horror';
      return JSON.stringify(parsed);
    }catch{return body}
  }

  window.fetch=async function(input,init){
    const originalUrl=typeof input==='string'?input:input?.url||'';
    let target=input,nextInit=init;
    if(horrorSelected&&init?.method==='POST'){
      if(originalUrl.includes('/api/plan'))target='/api/horror-plan';
      else if(originalUrl.includes('/api/scene-query'))target='/api/horror-scene-query';
      if(originalUrl.includes('/api/plan')||originalUrl.includes('/api/scene-query')||originalUrl.includes('/api/generate')){
        nextInit={...init,body:patchBody(init.body)};
      }
    }
    return nativeFetch(target,nextInit);
  };

  function boot(){
    injectPreset();
    ['visualStyle','mediaMode','cartoonStyle'].forEach(id=>$(id)?.addEventListener('change',()=>setTimeout(syncHorrorPreview,0)));
    document.addEventListener('change',e=>{if(e.target?.id==='mediaSource')setTimeout(syncHorrorPreview,0)});
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();