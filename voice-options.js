(()=>{
  const VOICES=[
    ['gemini:GacruxDeep','Gacrux Grave — masculina profunda e natural'],
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
  const SPEED_LABELS={default:'Padrão',fast:'Rápido',veryfast:'Veloz'};

  function configureSpeed(){
    const speed=document.getElementById('voiceSpeed');
    if(!speed)return;
    const previous=['default','fast','veryfast'].includes(speed.value)?speed.value:'default';
    speed.innerHTML='<option value="default">Padrão</option><option value="fast">Rápido</option><option value="veryfast">Veloz</option>';
    speed.value=previous;
    const wrap=speed.parentElement;
    if(wrap)wrap.hidden=false;
    const label=wrap?.querySelector('label');
    if(label)label.textContent='Velocidade da narração';
  }

  function syncAudioNotice(){
    const notice=document.getElementById('audioNotice');
    const speed=document.getElementById('voiceSpeed')?.value||'default';
    if(!notice)return;
    let value=String(notice.textContent||'');
    const speedWord=speed==='fast'?'rápida':speed==='veryfast'?'veloz':'padrão';
    if(/velocidade\s+(lenta|rápida|padrão|normal|veloz)/i.test(value)){
      value=value.replace(/velocidade\s+(lenta|rápida|padrão|normal|veloz)/gi,`velocidade ${speedWord}`);
    }else if(/^Voz\s/i.test(value)){
      value=value.replace(/(Voz\s+[^.]+?)(\.\s|$)/i,`$1, velocidade ${speedWord}$2`);
    }
    value=value.replace(/Tom da voz, música/gi,'Tom e velocidade da voz, música');
    notice.textContent=value;
  }

  function configure(){
    const select=document.getElementById('voice');
    configureSpeed();
    if(!select)return;
    if(!select.dataset.geminiVoices){
      const previous=LEGACY[select.value]||select.value;
      select.dataset.geminiVoices='1';
      select.innerHTML=VOICES.map(([value,label])=>`<option value="${value}">${label}</option>`).join('');
      select.value=LABELS[previous]?previous:'gemini:Sulafat';
    }
    const sync=()=>{
      configureSpeed();
      const label=document.getElementById('previewVoiceLabel');
      if(label){
        const short=(LABELS[select.value]||'Narração natural').split(' — ')[0];
        const pitch=document.getElementById('voicePitch')?.value||'default';
        const speed=document.getElementById('voiceSpeed')?.value||'default';
        const forcedDeep=select.value==='gemini:GacruxDeep';
        label.textContent=`${short} • ${forcedDeep||pitch==='low'?'Grave':pitch==='high'?'Aguda':'Natural'} • ${SPEED_LABELS[speed]||'Padrão'}`;
      }
      setTimeout(syncAudioNotice,0);
    };
    if(!select.dataset.voiceSync){
      select.dataset.voiceSync='1';
      select.addEventListener('change',sync);
      document.getElementById('voicePitch')?.addEventListener('change',()=>setTimeout(sync,0));
      document.getElementById('voiceSpeed')?.addEventListener('change',()=>setTimeout(sync,0));
    }
    sync();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',configure,{once:true});else configure();
})();