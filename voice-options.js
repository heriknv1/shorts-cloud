(()=>{
  const MALE=[
    ['gemini:AlgenibDeep','Algenib Grave — Masculina • grave e encorpada'],
    ['gemini:Charon','Charon — Masculina • clara e documental'],
    ['gemini:Puck','Puck — Masculina • viva e energética']
  ];
  const FEMALE=[
    ['gemini:Sulafat','Sulafat — Feminina • calorosa e expressiva'],
    ['gemini:Gacrux','Gacrux — Feminina • madura e acolhedora'],
    ['gemini:Achernar','Achernar — Feminina • suave e íntima'],
    ['gemini:Kore','Kore — Feminina • confiante e marcante']
  ];
  const VOICES=[...MALE,...FEMALE];
  const LABELS=Object.fromEntries(VOICES);LABELS.off='Sem narração';
  const LEGACY={'gemini:GacruxDeep':'gemini:AlgenibDeep','pt-BR-AntonioNeural':'gemini:Charon','pt-BR-FranciscaNeural':'gemini:Sulafat','pt-BR-ThalitaNeural':'gemini:Achernar'};
  const SPEED_LABELS={default:'Padrão',fast:'Rápido',veryfast:'Veloz'};
  function voiceMarkup(){const opts=group=>group.map(([value,label])=>`<option value="${value}">${label}</option>`).join('');return `<option value="off">Sem narração</option><optgroup label="Vozes masculinas">${opts(MALE)}</optgroup><optgroup label="Vozes femininas">${opts(FEMALE)}</optgroup>`}
  function configureSpeed(){const speed=document.getElementById('voiceSpeed');if(!speed)return;const previous=['default','fast','veryfast'].includes(speed.value)?speed.value:'default';speed.innerHTML='<option value="default">Padrão</option><option value="fast">Rápido</option><option value="veryfast">Veloz</option>';speed.value=previous;const label=speed.parentElement?.querySelector('label');if(label)label.textContent='Velocidade da narração'}
  function syncVoiceControls(select){const off=select.value==='off',pitch=document.getElementById('voicePitch'),speed=document.getElementById('voiceSpeed');if(pitch){pitch.disabled=off;if(pitch.parentElement)pitch.parentElement.hidden=off}if(speed){speed.disabled=off;if(speed.parentElement)speed.parentElement.hidden=off}}
  function syncAudioNotice(select){const notice=document.getElementById('audioNotice');if(!notice)return;const music=document.getElementById('music')?.value||'off',vol=document.getElementById('musicVolume')?.value||'medium',musicText=music==='off'?'Sem música de fundo.':`Música ativada com volume ${vol==='low'?'baixo':vol==='high'?'alto':'médio'}.`;let next;if(select.value==='off')next=`Sem narração. ${musicText} As legendas continuam opcionais.`;else{const pitch=document.getElementById('voicePitch')?.value||'default',speed=document.getElementById('voiceSpeed')?.value||'default';next=`Narração ${pitch==='low'?'grave':pitch==='high'?'aguda':'natural'}, velocidade ${speed==='fast'?'rápida':speed==='veryfast'?'veloz':'padrão'}. ${musicText}`}if(notice.textContent!==next)notice.textContent=next}
  function configure(){const select=document.getElementById('voice');configureSpeed();if(!select)return;if(!select.dataset.geminiVoices){const previous=LEGACY[select.value]||select.value;select.dataset.geminiVoices='1';select.innerHTML=voiceMarkup();select.value=LABELS[previous]?previous:'gemini:Sulafat'}const sync=()=>{configureSpeed();syncVoiceControls(select);const label=document.getElementById('previewVoiceLabel');if(label){if(select.value==='off')label.textContent='Sem narração';else{const short=(LABELS[select.value]||'Narração natural').split(' — ')[0],gender=MALE.some(([v])=>v===select.value)?'Masculina':'Feminina',pitch=document.getElementById('voicePitch')?.value||'default',speed=document.getElementById('voiceSpeed')?.value||'default',forcedDeep=select.value==='gemini:AlgenibDeep';label.textContent=`${short} • ${gender} • ${forcedDeep||pitch==='low'?'Grave':pitch==='high'?'Aguda':'Natural'} • ${SPEED_LABELS[speed]||'Padrão'}`}}syncAudioNotice(select)};if(!select.dataset.voiceSync){select.dataset.voiceSync='1';select.addEventListener('change',sync);document.getElementById('voicePitch')?.addEventListener('change',()=>setTimeout(sync,0));document.getElementById('voiceSpeed')?.addEventListener('change',()=>setTimeout(sync,0));document.getElementById('music')?.addEventListener('change',()=>setTimeout(sync,0));document.getElementById('musicVolume')?.addEventListener('change',()=>setTimeout(sync,0))}sync()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',configure,{once:true});else configure();
})();