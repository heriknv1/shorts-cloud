(()=>{
  let submitting=false,cancelling=false,activeRunId=null,lastKnownActive=false,startedAt=0,statusBusy=false,pollTimer=null,statusInitialized=false,audioContext=null;
  const $=id=>document.getElementById(id);
  const setProp=(el,key,value)=>{if(el&&el[key]!==value)el[key]=value};
  const watchedRuns=new Set(),notifiedRuns=new Set();

  function prepareCompletionAlert(){
    try{const AudioCtx=window.AudioContext||window.webkitAudioContext;if(AudioCtx&&!audioContext)audioContext=new AudioCtx();audioContext?.resume?.()}catch{}
    try{if('Notification'in window&&Notification.permission==='default')Notification.requestPermission().catch(()=>{})}catch{}
  }

  function completionChime(){
    try{
      const AudioCtx=window.AudioContext||window.webkitAudioContext;if(!AudioCtx)return;
      const ctx=audioContext||new AudioCtx();audioContext=ctx;ctx.resume?.();const start=ctx.currentTime+.03;
      [[659.25,0,.16],[783.99,.13,.18],[1046.5,.28,.32]].forEach(([freq,delay,duration])=>{const osc=ctx.createOscillator(),gain=ctx.createGain();osc.type='sine';osc.frequency.value=freq;gain.gain.setValueAtTime(.0001,start+delay);gain.gain.exponentialRampToValueAtTime(.13,start+delay+.025);gain.gain.exponentialRampToValueAtTime(.0001,start+delay+duration);osc.connect(gain).connect(ctx.destination);osc.start(start+delay);osc.stop(start+delay+duration+.03)})
    }catch{}
  }

  function showCompletionToast(){
    let toast=$('videoCompletionToast');
    if(!toast){toast=document.createElement('div');toast.id='videoCompletionToast';toast.setAttribute('role','status');toast.style.cssText='position:fixed;right:18px;bottom:18px;z-index:99999;max-width:min(360px,calc(100vw - 36px));padding:15px 18px;border:1px solid rgba(166,139,255,.55);border-radius:16px;background:rgba(19,22,34,.97);color:#f7f4ff;box-shadow:0 18px 55px rgba(0,0,0,.38);font:700 14px/1.45 system-ui;opacity:0;transform:translateY(14px);transition:.25s ease';document.body.appendChild(toast)}
    toast.innerHTML='✓ Seu vídeo está pronto!<div style="margin-top:3px;font-weight:400;color:#c9c4d8">Você já pode baixar o resultado.</div>';requestAnimationFrame(()=>{toast.style.opacity='1';toast.style.transform='translateY(0)'});clearTimeout(toast._hideTimer);toast._hideTimer=setTimeout(()=>{toast.style.opacity='0';toast.style.transform='translateY(14px)'},9000)
  }

  function notifyCompletion(run){
    const id=String(run?.id||'');if(!id||notifiedRuns.has(id))return;notifiedRuns.add(id);completionChime();showCompletionToast();setNote('Seu vídeo foi concluído e está pronto para baixar.');
    try{if(document.hidden&&'Notification'in window&&Notification.permission==='granted')new Notification('Short Cloud Studio',{body:'Seu vídeo foi concluído e está pronto para baixar.',tag:`short-cloud-${id}`})}catch{}
  }

  function ensureUI(){
    const generate=$('generateBtn');if(!generate)return null;
    let cancel=$('cancelGenerationBtn');
    if(!cancel){cancel=document.createElement('button');cancel.id='cancelGenerationBtn';cancel.type='button';cancel.className='ghost';cancel.textContent='Cancelar geração';cancel.hidden=true;cancel.style.marginLeft='10px';generate.insertAdjacentElement('afterend',cancel);cancel.addEventListener('click',cancelGeneration)}
    let note=$('generationControlNote');
    if(!note){note=document.createElement('div');note.id='generationControlNote';note.className='muted';note.style.marginTop='10px';generate.parentElement?.insertAdjacentElement('afterend',note)}
    return{generate,cancel,note};
  }

  function setNote(text,error=false){const ui=ensureUI();if(!ui)return;if(ui.note.textContent!==String(text||''))ui.note.textContent=text||'';ui.note.style.color=error?'#ffb4b4':''}
  function applyLock(){
    const ui=ensureUI();if(!ui)return;const locked=submitting||lastKnownActive||cancelling;
    if(locked){setProp(ui.generate,'disabled',true);ui.generate.textContent=lastKnownActive?'Geração em andamento':'Iniciando…';setProp(ui.cancel,'hidden',false);setProp(ui.cancel,'disabled',cancelling);ui.cancel.textContent=cancelling?'Cancelando…':'Cancelar geração'}
    else{setProp(ui.cancel,'hidden',true);setProp(ui.cancel,'disabled',false);ui.cancel.textContent='Cancelar geração';ui.generate.textContent='Gerar vídeo'}
  }

  async function readStatus(){
    if(statusBusy)return null;statusBusy=true;
    try{
      const r=await fetch('/api/status',{cache:'no-store'}),d=await r.json();if(!r.ok)return null;
      const runs=d.runs||[],active=runs.find(x=>x.status!=='completed');
      if(statusInitialized){for(const run of runs){const id=String(run.id||'');if(run.status!=='completed')watchedRuns.add(id);else if(run.conclusion==='success'&&watchedRuns.has(id))notifyCompletion(run)}}
      else statusInitialized=true;
      lastKnownActive=!!active;activeRunId=active?.id||null;
      if(active){submitting=false;setNote('Seu vídeo está sendo criado. Você pode cancelar com segurança enquanto estiver em andamento.')}
      else if(submitting&&Date.now()-startedAt>15000){submitting=false;setNote('A solicitação não foi confirmada. Você pode tentar novamente.',true)}
      applyLock();return d;
    }catch{return null}finally{statusBusy=false}
  }

  async function waitForCancellation(targetId){
    for(let i=0;i<24;i++){
      await new Promise(r=>setTimeout(r,1000));const d=await readStatus();if(!d)continue;
      const target=(d.runs||[]).find(x=>String(x.id)===String(targetId));
      if(target?.status==='completed'){
        cancelling=false;submitting=false;lastKnownActive=false;activeRunId=null;applyLock();
        if(target.conclusion==='cancelled')setNote('Geração cancelada. Ela não será contabilizada na sua cota diária.');
        else if(target.conclusion==='success')setNote('O vídeo terminou antes que o cancelamento pudesse ser concluído.',true);
        else setNote('A geração foi encerrada e não foi concluída.');return;
      }
      if(!(d.runs||[]).some(x=>x.status!=='completed')){cancelling=false;submitting=false;lastKnownActive=false;activeRunId=null;applyLock();setNote('A geração foi encerrada.');return}
    }
    cancelling=false;applyLock();setNote('O cancelamento ainda está sendo confirmado. Atualize o progresso em alguns segundos.')
  }

  async function cancelGeneration(){
    if(cancelling)return;cancelling=true;applyLock();setNote('Solicitando cancelamento seguro…');
    try{const r=await fetch('/api/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({runId:activeRunId})}),d=await r.json();if(!r.ok)throw new Error(d.error||'Não foi possível cancelar agora.');const target=d.runId||activeRunId;setNote('Cancelamento solicitado. Aguarde a confirmação.');if(target)await waitForCancellation(target);else{cancelling=false;setTimeout(readStatus,1200)}}
    catch(e){cancelling=false;applyLock();setNote(e.message||'Não foi possível cancelar agora.',true);setTimeout(readStatus,1200)}
  }

  function interceptGenerate(e){
    if(submitting||lastKnownActive||cancelling){e.preventDefault();e.stopImmediatePropagation();return}
    prepareCompletionAlert();
    submitting=true;startedAt=Date.now();applyLock();setNote('Iniciando a criação. O botão fica bloqueado para evitar envios duplicados.');
    setTimeout(readStatus,1200);setTimeout(readStatus,3500);setTimeout(readStatus,7000);
  }

  function boot(){const ui=ensureUI();if(!ui)return;ui.generate.addEventListener('click',interceptGenerate,true);readStatus();pollTimer=setInterval(readStatus,5000);window.addEventListener('beforeunload',()=>pollTimer&&clearInterval(pollTimer),{once:true})}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
