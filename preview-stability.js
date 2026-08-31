(()=>{
  const ensureCaptionOptions=()=>{
    const select=document.getElementById('captionSize');
    if(!select)return;
    const expected=[['42','Pequena'],['56','Média'],['70','Grande'],['84','Extra grande']];
    const current=[...select.options].map(o=>o.value).join(',');
    if(current!=='42,56,70,84'){
      select.replaceChildren(...expected.map(([value,label])=>{const option=document.createElement('option');option.value=value;option.textContent=label;if(value==='56')option.selected=true;return option;}));
      select.dispatchEvent(new Event('change',{bubbles:true}));
    }
  };
  const ensureNaturalVoiceDefault=()=>{
    const select=document.getElementById('voice');
    if(!select)return;
    if(!select.dataset.defaultAdjusted){select.dataset.defaultAdjusted='1';if(select.value==='pt-BR-AntonioNeural'){select.value='pt-BR-FranciscaNeural';select.dispatchEvent(new Event('change',{bubbles:true}));}}
  };
  const scaleCaption=()=>{
    const select=document.getElementById('captionSize'),caption=document.getElementById('previewCaption');
    if(!select||!caption)return;
    const size=Number(select.value||56),px=Math.max(10,Math.round(size*.22)),target=`${px}px`;
    if(caption.style.fontSize!==target)caption.style.fontSize=target;
    const label=document.getElementById('previewFontLabel'),font=document.getElementById('captionFont')?.value||'Montserrat';
    if(label)label.textContent=`${font} • ${size}`;
  };
  function boot(){
    ensureCaptionOptions();ensureNaturalVoiceDefault();scaleCaption();
    const caption=document.getElementById('previewCaption'),select=document.getElementById('captionSize');
    select?.addEventListener('change',()=>requestAnimationFrame(scaleCaption));
    document.querySelectorAll('.preset').forEach(btn=>btn.addEventListener('click',()=>requestAnimationFrame(scaleCaption)));
    ['visualStyle','mediaMode','music','musicVolume','voice','voicePitch','voiceSpeed','cartoonStyle','captionFont','captions'].forEach(id=>document.getElementById(id)?.addEventListener('change',()=>requestAnimationFrame(scaleCaption)));
    if(caption)new MutationObserver(scaleCaption).observe(caption,{attributes:true,attributeFilter:['style']});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
