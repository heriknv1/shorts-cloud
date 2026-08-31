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

  function lockNormalSpeed(){
    const speed=document.getElementById('voiceSpeed');
    if(!speed)return;
    speed.innerHTML='<option value="default">Normal</option>';
    speed.value='default';
    const wrap=speed.parentElement;
    if(wrap)wrap.hidden=true;
  }

  function cleanAudioNotice(){
    const notice=document.getElementById('audioNotice');
    if(!notice)return;
    let value=String(notice.textContent||'');
    value=value.replace(/,\s*velocidade\s+(lenta|rápida|padrão|normal)/gi,'');
    value=value.replace(/Tom e velocidade da voz/gi,'Tom da voz');
    notice.textContent=value;
  }

  function configure(){
    const select=document.getElementById('voice');
    lockNormalSpeed();
    cleanAudioNotice();
    if(!select)return;
    if(!select.dataset.geminiVoices){
      const previous=LEGACY[select.value]||select.value;
      select.dataset.geminiVoices='1';
      select.innerHTML=VOICES.map(([value,label])=>`<option value="${value}">${label}</option>`).join('');
      select.value=LABELS[previous]?previous:'gemini:Sulafat';
    }
    const sync=()=>{
      lockNormalSpeed();
      const label=document.getElementById('previewVoiceLabel');
      if(label){
        const short=(LABELS[select.value]||'Narração natural').split(' — ')[0];
        const pitch=document.getElementById('voicePitch')?.value||'default';
        label.textContent=`${short} • ${pitch==='low'?'Grave':pitch==='high'?'Aguda':'Natural'}`;
      }
      setTimeout(cleanAudioNotice,0);
    };
    if(!select.dataset.voiceSync){
      select.dataset.voiceSync='1';
      select.addEventListener('change',sync);
      document.getElementById('voicePitch')?.addEventListener('change',()=>setTimeout(sync,0));
    }
    sync();
    const notice=document.getElementById('audioNotice');
    if(notice&&!notice.dataset.speedClean){
      notice.dataset.speedClean='1';
      new MutationObserver(()=>cleanAudioNotice()).observe(notice,{childList:true,characterData:true,subtree:true});
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',configure,{once:true});else configure();
})();