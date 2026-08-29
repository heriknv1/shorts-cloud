(()=>{
  let submitting=false,cancelling=false,activeRunId=null,lastKnownActive=false,startedAt=0,statusBusy=false,pollTimer=null;
  const $=id=>document.getElementById(id);
  const setProp=(el,key,value)=>{if(el&&el[key]!==value)el[key]=value};

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
      const active=(d.runs||[]).find(x=>x.status!=='completed');lastKnownActive=!!active;activeRunId=active?.id||null;
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
    submitting=true;startedAt=Date.now();applyLock();setNote('Iniciando a criação. O botão fica bloqueado para evitar envios duplicados.');
    setTimeout(readStatus,1200);setTimeout(readStatus,3500);setTimeout(readStatus,7000);
  }

  function boot(){const ui=ensureUI();if(!ui)return;ui.generate.addEventListener('click',interceptGenerate,true);readStatus();pollTimer=setInterval(readStatus,5000);window.addEventListener('beforeunload',()=>pollTimer&&clearInterval(pollTimer),{once:true})}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();