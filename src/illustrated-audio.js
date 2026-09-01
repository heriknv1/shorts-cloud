import { put } from '@vercel/blob/client';

(()=>{
  const nativeFetch=window.fetch.bind(window);
  const $=id=>document.getElementById(id);
  const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const MAX_SOURCE_BYTES=200*1024*1024;
  const PENDING_KEY='shortcloud_illustrated_pending_v1';
  const state={active:false,uploading:false,uploadPath:'',file:null,fileObjectUrl:'',mime:'',name:'',size:0,duration:0,analysisId:'',analysisKey:'',pendingSignature:'',lastPlan:null,planSignature:'',pollToken:0,snapshot:null};

  function jsonResponse(status,data){return Promise.resolve(new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}}))}
  function sourceMode(){return $('illustratedSourceMode')?.value==='link'?'link':'file'}
  function contextValue(){return String($('illustratedContext')?.value||'').trim().slice(0,600)}
  function doodleStyle(){return $('illustratedDoodleStyle')?.value||'clean-doodle'}
  function linkValue(){return String($('illustratedSourceLink')?.value||'').trim()}
  function sourceUrl(){return sourceMode()==='link'?linkValue():''}
  function sourcePathname(){return sourceMode()==='file'?state.uploadPath:''}
  function analysisSignature(){return JSON.stringify([sourceMode(),sourceUrl(),sourcePathname(),contextValue(),doodleStyle()])}
  function safeName(value){return String(value||'conteudo').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^A-Za-z0-9._-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,90)||'conteudo'}
  function escapeHtml(value){return String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]))}
  function validHttps(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password}catch{return false}}
  function setSourceStatus(text,kind='',progress=null){const el=$(sourceMode()==='link'?'illustratedLinkStatus':'illustratedSourceStatus');if(el){el.textContent=text;el.className=`illustrated-source-status ${kind}`.trim()}const bar=$('illustratedUploadBar');if(bar&&progress!==null)bar.style.width=`${Math.max(0,Math.min(100,Number(progress)||0))}%`}
  function rightsConfirmed(){return !!$('illustratedRights')?.checked}
  function savePending(signature){try{sessionStorage.setItem(PENDING_KEY,JSON.stringify({at:Date.now(),analysisId:state.analysisId,analysisKey:state.analysisKey,signature,mode:sourceMode(),uploadPath:state.uploadPath,link:linkValue(),mime:state.mime,name:state.name,size:state.size,context:contextValue(),style:doodleStyle()}))}catch{}}
  function clearPending(reset=false){try{sessionStorage.removeItem(PENDING_KEY)}catch{}state.pendingSignature='';if(reset){state.analysisId='';state.analysisKey=''}}

  function injectStyles(){
    if($('illustratedAudioStyles'))return;
    const style=document.createElement('style');style.id='illustratedAudioStyles';style.textContent=`
      .illustrated-source-panel{margin:16px 0 20px;padding:18px;border:1px solid rgba(170,142,255,.35);border-radius:18px;background:linear-gradient(145deg,rgba(123,92,255,.10),rgba(10,13,21,.72))}
      .illustrated-source-panel[hidden]{display:none}.illustrated-source-head{display:flex;gap:14px;align-items:flex-start;margin-bottom:14px}.illustrated-source-head>div{min-width:0}.illustrated-source-head>button{margin-left:auto;white-space:nowrap}.illustrated-source-icon{display:grid;place-items:center;flex:0 0 42px;height:42px;border-radius:13px;background:#8d72ff;color:white;font-size:21px}.illustrated-source-head h3{margin:0 0 4px;font-size:17px}.illustrated-source-head p{margin:0;color:var(--muted);font-size:12px;line-height:1.45}
      .illustrated-source-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.illustrated-source-grid .wide{grid-column:1/-1}.illustrated-file-box{margin-top:8px;padding:14px;border:1px dashed #555f7d;border-radius:14px;background:#0a0e17}.illustrated-file-actions{display:flex;gap:9px;align-items:center;flex-wrap:wrap}.illustrated-file-name{font-size:12px;color:#ddd8ec;overflow-wrap:anywhere}.illustrated-media-preview{display:block;width:100%;max-height:250px;margin-top:12px;border-radius:12px;background:#05070c}.illustrated-source-status{min-height:20px;margin-top:9px;color:var(--muted);font-size:11px;line-height:1.45}.illustrated-source-status.ok{color:#95e7bd}.illustrated-source-status.bad{color:#ffb4b4}.illustrated-source-status.busy{color:#c9bdff}.illustrated-upload-track{height:5px;margin-top:7px;border-radius:999px;background:#22283a;overflow:hidden}.illustrated-upload-bar{height:100%;width:0;background:linear-gradient(90deg,#7659ff,#bba8ff);transition:width .2s ease}
      .illustrated-rights{display:flex;gap:9px;align-items:flex-start;margin-top:12px;color:#c8c3d5;font-size:11px;line-height:1.45}.illustrated-rights input{margin-top:2px}.illustrated-meta{margin-top:9px;padding:9px 11px;border:1px solid rgba(155,130,255,.2);border-radius:11px;background:rgba(117,86,242,.07);font-size:11px;color:#c9c2dc;line-height:1.5}.illustrated-meta strong{color:#f3efff}.illustrated-readonly{opacity:.82;background:rgba(255,255,255,.025)!important}.illustrated-base-field-hidden{display:none!important}
      body[data-illustrated-mode="on"] .reference-source{display:none!important}body[data-illustrated-mode="on"] #manualHookWrap{display:none!important}
      @media(max-width:680px){.illustrated-source-grid{grid-template-columns:1fr}.illustrated-source-grid .wide{grid-column:auto}.illustrated-source-panel{padding:14px}}
    `;document.head.appendChild(style);
  }

  function injectUI(){
    const grid=$('presetGrid'),topic=$('topic');if(!grid||!topic||$('illustratedSourcePanel'))return;
    const button=document.createElement('button');button.type='button';button.className='preset';button.dataset.preset='audio-illustrated';button.innerHTML='<strong>Áudio Ilustrado</strong><span>Áudio, vídeo ou link • desenho divertido sincronizado</span>';
    const life=grid.querySelector('[data-preset="life-lessons"]');if(life)life.insertAdjacentElement('afterend',button);else grid.appendChild(button);
    const panel=document.createElement('div');panel.id='illustratedSourcePanel';panel.className='illustrated-source-panel';panel.hidden=true;panel.innerHTML=`
      <div class="illustrated-source-head"><span class="illustrated-source-icon">✎</span><div><h3>Transforme um conteúdo real em desenho</h3><p>O áudio original conduz as cenas. A análise identifica falas, participantes, ações, mudanças de contexto e oportunidades de humor.</p></div><button type="button" class="ghost" id="cancelIllustratedAnalysis" hidden>Cancelar análise</button></div>
      <div class="illustrated-source-grid">
        <div><label for="illustratedSourceMode">Entrada</label><select id="illustratedSourceMode"><option value="file" selected>Enviar áudio ou vídeo</option><option value="link">Colar link público</option></select></div>
        <div><label for="illustratedDoodleStyle">Traço</label><select id="illustratedDoodleStyle"><option value="clean-doodle" selected>Traço limpo e divertido</option><option value="soft-accent">Preto com cores suaves</option><option value="playful-ink">Nanquin expressivo</option></select></div>
        <div class="wide" id="illustratedFileWrap"><div class="illustrated-file-box"><div class="illustrated-file-actions"><button type="button" class="ghost" id="chooseIllustratedFile">Escolher áudio ou vídeo</button><span class="illustrated-file-name" id="illustratedFileName">Nenhum arquivo selecionado</span></div><input id="illustratedFileInput" type="file" accept="audio/*,video/*" hidden><div class="illustrated-upload-track"><div class="illustrated-upload-bar" id="illustratedUploadBar"></div></div><div class="illustrated-source-status" id="illustratedSourceStatus">Formatos comuns de áudio e vídeo, com até 200 MB.</div><div id="illustratedMediaPreview"></div></div></div>
        <div class="wide" id="illustratedLinkWrap" hidden><label for="illustratedSourceLink">Link do vídeo ou áudio</label><input id="illustratedSourceLink" type="url" inputmode="url" placeholder="https://..."><div class="muted">O conteúdo precisa estar público. Se a plataforma bloquear a leitura, envie o arquivo diretamente.</div><div class="illustrated-source-status" id="illustratedLinkStatus">Cole um endereço público iniciado por https://.</div></div>
        <div class="wide"><label for="illustratedContext">Orientação adicional <span class="muted">(opcional)</span></label><textarea id="illustratedContext" rows="2" maxlength="600" placeholder="Ex.: mantenha a conversa familiar e destaque a reação engraçada no final"></textarea></div>
      </div>
      <label class="illustrated-rights"><input id="illustratedRights" type="checkbox"><span>Confirmo que tenho autorização para utilizar o áudio ou vídeo enviado.</span></label>`;
    topic.insertAdjacentElement('afterend',panel);
    $('illustratedSourceMode').addEventListener('change',syncSourceMode);
    $('chooseIllustratedFile').addEventListener('click',()=>$('illustratedFileInput').click());
    $('illustratedFileInput').addEventListener('change',event=>prepareFile(event.target.files?.[0]));
    $('illustratedSourceLink').addEventListener('input',()=>{state.planSignature='';if(validHttps(linkValue()))setSourceStatus('Link pronto para análise.','ok');else setSourceStatus('Cole um endereço público iniciado por https://.','')});
    $('illustratedContext').addEventListener('input',()=>{state.planSignature=''});
    $('illustratedDoodleStyle').addEventListener('change',()=>{state.planSignature=''});
    $('cancelIllustratedAnalysis').addEventListener('click',cancelAnalysis);
  }

  function syncSourceMode(){
    const link=sourceMode()==='link';if($('illustratedFileWrap'))$('illustratedFileWrap').hidden=link;if($('illustratedLinkWrap'))$('illustratedLinkWrap').hidden=!link;
    if(link)setSourceStatus(validHttps(linkValue())?'Link pronto para análise.':'Cole um endereço público iniciado por https://.',validHttps(linkValue())?'ok':'');
    else if(state.uploadPath)setSourceStatus('Arquivo enviado e pronto para análise.','ok',100);
  }

  function renderLocalPreview(file){
    const wrap=$('illustratedMediaPreview');if(!wrap)return;if(state.fileObjectUrl)URL.revokeObjectURL(state.fileObjectUrl);state.fileObjectUrl=URL.createObjectURL(file);wrap.innerHTML='';
    const media=document.createElement(file.type.startsWith('video/')?'video':'audio');media.className='illustrated-media-preview';media.controls=true;media.preload='metadata';if(media.tagName==='VIDEO')media.muted=true;media.src=state.fileObjectUrl;wrap.appendChild(media);
  }

  async function prepareFile(file){
    if(!file)return;if(!/^(audio|video)\//i.test(file.type)){setSourceStatus('Escolha um arquivo de áudio ou vídeo válido.','bad');return}if(file.size>MAX_SOURCE_BYTES){setSourceStatus('O arquivo ultrapassa o limite de 200 MB.','bad');return}
    state.file=file;state.mime=file.type||'application/octet-stream';state.name=file.name;state.size=file.size;state.uploadPath='';state.planSignature='';renderLocalPreview(file);$('illustratedFileName').textContent=`${file.name} • ${(file.size/1024/1024).toFixed(1)} MB`;await uploadSource(file);
  }

  async function uploadSource(file){
    state.uploading=true;$('chooseIllustratedFile').disabled=true;setSourceStatus('Enviando arquivo temporário…','busy',2);
    try{
      const pathname=`illustrated-inputs/${Date.now()}-${safeName(file.name)}`;
      const multipart=file.size>5*1024*1024,tokenResponse=await nativeFetch('/api/source-upload',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'blob.generate-client-token',payload:{pathname,clientPayload:null,multipart}})});let tokenData={};try{tokenData=await tokenResponse.json()}catch{}
      if(!tokenResponse.ok)throw Error(tokenData.error||(tokenResponse.status===401?'Sua sessão expirou. Atualize a página e entre novamente.':'Não foi possível autorizar o envio agora.'));
      const token=String(tokenData.clientToken||'');if(!token.startsWith('vercel_blob_client_'))throw Error('O armazenamento temporário devolveu uma autorização inválida.');
      const result=await put(pathname,file,{access:'private',token,multipart,onUploadProgress:({percentage})=>setSourceStatus(`Enviando… ${Math.round(percentage)}%`,'busy',percentage)});
      state.uploadPath=result.pathname;setSourceStatus('Arquivo privado enviado e pronto para análise.','ok',100);
    }catch(error){state.uploadPath='';const detail=String(error?.message||'');setSourceStatus(detail||'Não foi possível enviar este arquivo.','bad',0)}finally{state.uploading=false;$('chooseIllustratedFile').disabled=false}
  }

  function previewSvg(){
    const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1280"><rect width="720" height="1280" fill="#fffdf9"/><g fill="none" stroke="#17151c" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"><circle cx="262" cy="580" r="108"/><path d="M235 478c20-38 58-52 94-39M226 560l18-5m70 5 18 5M258 615c30 24 59 22 84-2M262 688v226m0-152-88 74m88-74 93 63m-93 89-58 126m58-126 72 126"/><circle cx="477" cy="650" r="82"/><path d="M450 624l15-3m47 3 14 3m-68 57c25 18 47 17 66-2M477 732v174m0-112-70 55m70-55 76 48m-76 64-45 104m45-104 55 104"/><path d="M382 505c47-70 93-82 139-36"/></g><g fill="#17151c"><circle cx="241" cy="560" r="7"/><circle cx="310" cy="560" r="7"/><circle cx="458" cy="640" r="6"/><circle cx="504" cy="640" r="6"/></g><text x="360" y="230" text-anchor="middle" font-family="sans-serif" font-size="58" font-weight="800" fill="#17151c">O ÁUDIO VIROU DESENHO</text><path d="M515 450l24-30m12 57 41-7" stroke="#8d72ff" stroke-width="12" stroke-linecap="round"/></svg>`;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  }

  function syncPreview(){
    if(!state.active)return;const photo=$('previewPhoto'),fallback=$('previewIllustration');if(photo){const src=previewSvg();if(photo.hidden)photo.hidden=false;if(photo.getAttribute('src')!==src)photo.src=src;photo.alt='Prévia de animação ilustrada minimalista'}if(fallback&&!fallback.hidden)fallback.hidden=true;
    if($('previewModeBadge'))$('previewModeBadge').textContent='ÁUDIO ILUSTRADO • DESENHO';if($('mediaChip'))$('mediaChip').textContent='Áudio original';if($('previewCaption'))$('previewCaption').textContent='As falas aparecem sincronizadas embaixo';if($('visualNotice'))$('visualNotice').textContent='Personagens consistentes, traço simples e cada desenho ligado diretamente ao contexto da fala.';if($('audioNotice'))$('audioNotice').textContent='O áudio original será preservado. Não será criada uma nova narração nem música de fundo.';if($('creativeNotice'))$('creativeNotice').textContent='Cortes sincronizados, reações expressivas e piadas visuais específicas — sem movimentos de câmera ou cenas genéricas.';
  }

  function rememberAndApplyDefaults(){
    const ids=['visualStyle','mediaMode','cartoonStyle','tone','voice','captions','captionFont','captionSize','music','editingPace','sfxMode','ambienceMode','cleanExport','brandingMode'];state.snapshot={topicValue:$('topic')?.value||'',values:Object.fromEntries(ids.map(id=>[id,$(id)?.value])),durationDisabled:$('duration')?.disabled||false,durationLabel:$('duration')?.parentElement?.querySelector('label')?.textContent||'Duração',stageTitle:document.querySelector('[data-stage="1"] h2')?.textContent||'',stageTip:document.querySelector('[data-stage="1"] .stage-tip')?.textContent||'',planText:$('planBtn')?.textContent||''};
    const values={visualStyle:'cartoon',mediaMode:'photos',cartoonStyle:'classic-2d',tone:'energetic',voice:'off',captions:'on',captionFont:'Montserrat',captionSize:'70',music:'off',editingPace:'fast',sfxMode:'off',ambienceMode:'off',cleanExport:'off',brandingMode:'off'};
    for(const[id,value]of Object.entries(values)){const el=$(id);if(el&&Array.from(el.options||[]).some(option=>option.value===value)){el.value=value;el.dispatchEvent(new Event('change',{bubbles:true}))}}
    const duration=$('duration');if(duration){duration.disabled=true;const label=duration.parentElement?.querySelector('label');if(label)label.textContent='Duração — automática pelo conteúdo'}
  }

  function hideBaseTopic(hidden){const topic=$('topic'),label=topic?.previousElementSibling;if(topic)topic.classList.toggle('illustrated-base-field-hidden',hidden);if(label?.tagName==='LABEL')label.classList.toggle('illustrated-base-field-hidden',hidden)}

  function enableMode(){
    if(state.active)return;state.active=true;state.pollToken++;rememberAndApplyDefaults();document.body.dataset.illustratedMode='on';document.querySelectorAll('.preset').forEach(b=>b.classList.toggle('active',b.dataset.preset==='audio-illustrated'));if($('illustratedSourcePanel'))$('illustratedSourcePanel').hidden=false;
    const topic=$('topic');if(topic)topic.value='Conteúdo enviado para animação ilustrada';hideBaseTopic(true);const title=document.querySelector('[data-stage="1"] h2'),tip=document.querySelector('[data-stage="1"] .stage-tip');if(title)title.textContent='Qual conteúdo você quer transformar em desenho?';if(tip)tip.textContent='Envie um arquivo ou cole um link público.';if($('planBtn'))$('planBtn').textContent='Analisar conteúdo e criar storyboard';if($('presetStatus'))$('presetStatus').textContent='Áudio Ilustrado selecionado. O áudio original será entendido e transformado em cenas criativas e coerentes.';
    document.dispatchEvent(new CustomEvent('shortcloud:preset-selected',{detail:'audio-illustrated'}));syncSourceMode();setTimeout(syncPreview,80);
  }

  function disableMode(){
    if(!state.active)return;state.active=false;state.pollToken++;delete document.body.dataset.illustratedMode;if($('illustratedSourcePanel'))$('illustratedSourcePanel').hidden=true;hideBaseTopic(false);const snap=state.snapshot||{};if($('topic'))$('topic').value=snap.topicValue||'';for(const[id,value]of Object.entries(snap.values||{})){const el=$(id);if(el&&value!==undefined){el.value=value;el.dispatchEvent(new Event('change',{bubbles:true}))}}const duration=$('duration');if(duration){duration.disabled=!!snap.durationDisabled;const label=duration.parentElement?.querySelector('label');if(label)label.textContent=snap.durationLabel||'Duração'}const title=document.querySelector('[data-stage="1"] h2'),tip=document.querySelector('[data-stage="1"] .stage-tip');if(title&&snap.stageTitle)title.textContent=snap.stageTitle;if(tip&&snap.stageTip)tip.textContent=snap.stageTip;if($('planBtn'))$('planBtn').textContent=snap.planText||'Criar roteiro e avançar';state.snapshot=null;
  }

  function validateBeforeAnalysis(){
    if(!rightsConfirmed())return 'Confirme que você tem autorização para utilizar esse conteúdo.';
    if(sourceMode()==='file'){if(state.uploading)return 'Aguarde o arquivo terminar de ser enviado.';if(!state.uploadPath)return 'Escolha e envie um áudio ou vídeo antes de continuar.'}
    else if(!validHttps(linkValue()))return 'Cole um link público válido iniciado por https://.';
    return '';
  }

  async function waitForAnalysis(analysisId,analysisKey,token){
    let transientFailures=0;
    for(let attempt=0;attempt<600;attempt++){
      if(token!==state.pollToken||!state.active)throw Error('Análise interrompida.');await wait(attempt===0?1800:3000);
      const message=$('message');let response,data;
      try{response=await nativeFetch(`/api/illustrated-status?id=${encodeURIComponent(analysisId)}`,{cache:'no-store',headers:{'X-Analysis-Key':analysisKey}});data=await response.json()}catch(error){transientFailures++;if(transientFailures<=8){if(message){message.hidden=false;message.style.color='';message.textContent='A análise continua. Reconectando ao acompanhamento automaticamente…'}continue}throw Error('A análise continua, mas não foi possível acompanhar o progresso agora.')}
      if(!response.ok){if((response.status===429||response.status>=500)&&++transientFailures<=8){if(message){message.hidden=false;message.style.color='';message.textContent='O processamento continua. Tentando acompanhar novamente…'}continue}throw Error(data.error||'Não foi possível acompanhar a análise.')}
      transientFailures=0;if(message){message.hidden=false;message.style.color='';message.textContent=data.stage||'Entendendo o áudio, as cenas e o contexto…'}
      if(data.ready&&data.plan)return data.plan;if(data.failed){clearPending(true);throw Error(data.error||'Não foi possível analisar esse conteúdo.')}
    }
    throw Error('A análise demorou mais que o esperado. Tente novamente.');
  }

  function setAnalysisBusy(value){const button=$('cancelIllustratedAnalysis');if(button){button.hidden=!value;button.disabled=false;button.textContent='Cancelar análise'}}
  async function cancelAnalysis(){
    const button=$('cancelIllustratedAnalysis');if(!state.analysisId||!button)return;button.disabled=true;button.textContent='Cancelando…';
    try{const response=await nativeFetch('/api/illustrated-cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:state.analysisId})}),data=await response.json();if(!response.ok)throw Error(data.error||'Não foi possível cancelar.');state.pollToken++;clearPending(true);setAnalysisBusy(false);const message=$('message');if(message){message.hidden=false;message.style.color='';message.textContent='Análise cancelada. Você pode escolher outro conteúdo.'}}
    catch(error){button.disabled=false;button.textContent='Cancelar análise';setSourceStatus(error.message||'Não foi possível cancelar a análise.','bad')}
  }

  function enhanceStoryboard(){
    if(!state.active||!state.lastPlan?.scenes)return;document.querySelectorAll('#sceneEditor .scene').forEach((el,index)=>{const scene=state.lastPlan.scenes[index];if(!scene)return;const label=el.querySelector('.n')?.parentElement?.querySelector('label');if(label)label.textContent='Fala original';const narration=el.querySelector('.n');if(narration){narration.readOnly=true;narration.classList.add('illustrated-readonly')}let meta=el.querySelector('.illustrated-meta');if(!meta){meta=document.createElement('div');meta.className='illustrated-meta';el.querySelector('.scene-head')?.insertAdjacentElement('afterend',meta)}const start=Number(scene.start||0).toFixed(1),end=Number(scene.end||0).toFixed(1),word=String(scene.on_screen_text||'').trim(),gag=String(scene.visual_gag||scene.visual_description||'').trim(),speaker=String(scene.speaker||'').trim();meta.innerHTML=`<strong>${start}s–${end}s${speaker?` • ${escapeHtml(speaker)}`:''}</strong>${word?` • Palavra visual: “${escapeHtml(word)}”`:''}<br>${escapeHtml(gag)}`;const badge=el.querySelector('.badge');if(badge)badge.textContent='desenho sincronizado'})
  }

  window.fetch=async function(input,init){
    const url=typeof input==='string'?input:input?.url||'';if(!state.active)return nativeFetch(input,init);
    if(init?.method==='POST'&&url.includes('/api/scene-query')){let body={};try{body=JSON.parse(init.body||'{}')}catch{}const desc=String(body.visualDescription||body.narration||'').trim();return jsonResponse(200,{visual_query:desc,visual_query_backup:desc,recommended_media:'image'})}
    if(init?.method==='POST'&&url.includes('/api/plan')){
      const error=validateBeforeAnalysis();if(error)return jsonResponse(400,{error});let body={};try{body=JSON.parse(init.body||'{}')}catch{}
      const signature=analysisSignature(),payload={sourceUrl:sourceUrl(),sourcePathname:sourcePathname(),sourceKind:sourceMode()==='link'?'link':(state.mime.startsWith('audio/')?'audio':'video'),sourceMime:sourceMode()==='link'?'application/octet-stream':state.mime,sourceName:sourceMode()==='link'?safeName(new URL(linkValue()).hostname):state.name,sourceSize:state.size,userContext:contextValue(),doodleStyle:doodleStyle(),rightsConfirmed:true};
      if(!(state.analysisId&&/^[a-f0-9]{64}$/.test(state.analysisKey)&&state.pendingSignature===signature)){const started=await nativeFetch('/api/illustrated-plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}),startedData=await started.json();if(!started.ok)return jsonResponse(started.status,startedData);state.analysisId=startedData.analysisId;state.analysisKey=startedData.analysisKey;state.pendingSignature=signature;savePending(signature)}const token=++state.pollToken;setAnalysisBusy(true);
      try{const plan=await waitForAnalysis(state.analysisId,state.analysisKey,token);clearPending(false);state.analysisKey='';state.lastPlan=plan;state.planSignature=signature;state.duration=Number(plan?.source?.duration_seconds||plan?.duration_seconds||0);setTimeout(enhanceStoryboard,80);return jsonResponse(200,{plan,preset:'Áudio Ilustrado'})}catch(err){return jsonResponse(500,{error:err.message||'Não foi possível analisar esse conteúdo.'})}finally{setAnalysisBusy(false)}
    }
    if(init?.method==='POST'&&url.includes('/api/generate')){
      const error=validateBeforeAnalysis();if(error)return jsonResponse(400,{error});if(!state.planSignature||state.planSignature!==analysisSignature())return jsonResponse(400,{error:'O conteúdo ou o estilo mudou depois da análise. Crie o storyboard novamente para manter as cenas coerentes.'});let body={};try{body=JSON.parse(init.body||'{}')}catch{}
      body.presetKey='audio-illustrated';body.topic=body.plan?.title||'Áudio Ilustrado';body.duration=state.duration||Number(body.plan?.source?.duration_seconds)||30;body.visualStyle='cartoon';body.cartoonStyle='classic-2d';body.mediaMode='photos';body.voice='off';body.music='off';body.editingPace='fast';body.sfxMode='off';body.ambienceMode='off';body.sourceUrl=sourceUrl();body.sourcePathname=sourcePathname();body.sourceKind=sourceMode()==='link'?'link':(state.mime.startsWith('audio/')?'audio':'video');body.sourceMime=sourceMode()==='link'?'application/octet-stream':state.mime;body.sourceName=sourceMode()==='link'?safeName(new URL(linkValue()).hostname):state.name;body.sourceAnalysisId=state.analysisId;body.doodleStyle=doodleStyle();body.sourceRights=true;
      return nativeFetch(input,{...init,body:JSON.stringify(body)});
    }
    return nativeFetch(input,init);
  };

  function boot(){
    injectStyles();injectUI();document.addEventListener('click',event=>{const preset=event.target?.closest?.('.preset');if(!preset)return;if(preset.dataset.preset==='audio-illustrated')enableMode();else disableMode()},{capture:true});
    const sceneEditor=$('sceneEditor');if(sceneEditor)new MutationObserver(()=>setTimeout(enhanceStoryboard,0)).observe(sceneEditor,{childList:true,subtree:true});const preview=$('previewMedia');if(preview)new MutationObserver(()=>{if(state.active)setTimeout(syncPreview,0)}).observe(preview,{attributes:true,subtree:true,attributeFilter:['src','hidden']});
    try{const saved=JSON.parse(sessionStorage.getItem(PENDING_KEY)||'null');if(saved&&Date.now()-Number(saved.at||0)<3*60*60*1000&&/^ill-[0-9]{10,16}-[a-f0-9]{8}$/.test(saved.analysisId||'')&&/^[a-f0-9]{64}$/.test(saved.analysisKey||'')){state.analysisId=saved.analysisId;state.analysisKey=saved.analysisKey;state.pendingSignature=saved.signature||'';state.uploadPath=saved.uploadPath||'';state.mime=saved.mime||'';state.name=saved.name||'';state.size=Number(saved.size||0);$('illustratedSourceMode').value=saved.mode==='link'?'link':'file';$('illustratedSourceLink').value=saved.link||'';$('illustratedContext').value=saved.context||'';$('illustratedDoodleStyle').value=saved.style||'clean-doodle';$('illustratedRights').checked=true;if(state.name)$('illustratedFileName').textContent=`${state.name} • arquivo temporário preservado`;enableMode();setAnalysisBusy(true);setTimeout(()=>$('planBtn')?.click(),300)}else if(saved)clearPending(true)}catch{clearPending(true)}
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
