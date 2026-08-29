(()=>{
  const scaleCaption=()=>{
    const select=document.getElementById('captionSize');
    const caption=document.getElementById('previewCaption');
    if(!select||!caption)return;
    const size=Number(select.value||56);
    const px=Math.max(10,Math.round(size*.22));
    const target=`${px}px`;
    if(caption.style.fontSize!==target)caption.style.fontSize=target;
  };

  function boot(){
    scaleCaption();
    const caption=document.getElementById('previewCaption');
    const select=document.getElementById('captionSize');
    select?.addEventListener('change',()=>requestAnimationFrame(scaleCaption));
    document.querySelectorAll('.preset').forEach(btn=>btn.addEventListener('click',()=>requestAnimationFrame(scaleCaption)));
    ['visualStyle','mediaMode','music','musicVolume','voicePitch','voiceSpeed','cartoonStyle','captionFont','captions'].forEach(id=>document.getElementById(id)?.addEventListener('change',()=>requestAnimationFrame(scaleCaption)));
    if(caption)new MutationObserver(scaleCaption).observe(caption,{attributes:true,attributeFilter:['style']});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();