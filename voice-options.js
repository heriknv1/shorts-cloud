(()=>{
  const VOICES=[
    ['gemini:Sulafat','Sulafat — calorosa e expressiva'],
    ['gemini:Gacrux','Gacrux — firme e acolhedora'],
    ['gemini:Achernar','Achernar — suave e íntima'],
    ['gemini:Charon','Charon — clara e documental'],
    ['gemini:Kore','Kore — confiante e marcante'],
    ['gemini:Puck','Puck — viva e energética']
  ];
  const LABELS=Object.fromEntries(VOICES);
  const LEGACY={
    'pt-BR-AntonioNeural':'gemini:Gacrux',
    'pt-BR-FranciscaNeural':'gemini:Sulafat',
    'pt-BR-ThalitaNeural':'gemini:Achernar'
  };
  function configure(){
    const select=document.getElementById('voice');
    if(!select||select.dataset.geminiVoices)return;
    const previous=LEGACY[select.value]||select.value;
    select.dataset.geminiVoices='1';
    select.innerHTML=VOICES.map(([value,label])=>`<option value="${value}">${label}</option>`).join('');
    select.value=LABELS[previous]?previous:'gemini:Sulafat';
    const sync=()=>{
      const label=document.getElementById('previewVoiceLabel');
      if(label){
        const short=(LABELS[select.value]||'Narração natural').split(' — ')[0];
        const pitch=document.getElementById('voicePitch')?.value||'default';
        const speed=document.getElementById('voiceSpeed')?.value||'default';
        label.textContent=`${short} • ${pitch==='low'?'Grave':pitch==='high'?'Aguda':'Natural'} • ${speed==='slow'?'Lenta':speed==='fast'?'Rápida':'Normal'}`;
      }
    };
    select.addEventListener('change',sync);
    ['voicePitch','voiceSpeed'].forEach(id=>document.getElementById(id)?.addEventListener('change',()=>setTimeout(sync,0)));
    sync();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',configure,{once:true});else configure();
})();