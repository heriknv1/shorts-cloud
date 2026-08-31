(()=>{
  const state={mode:'auto',b64:'',dataUrl:'',name:'',busy:false};
  const nativeFetch=window.fetch.bind(window);
  const $=id=>document.getElementById(id);
  const text=(id,value)=>{const el=$(id);if(el)el.textContent=value};

  function injectStyles(){
    if(document.getElementById('referenceAiStyles'))return;
    const s=document.createElement('style');s.id='referenceAiStyles';s.textContent=`
      .reference-source{grid-column:1/-1;border:1px solid var(--line);background:rgba(10,13,20,.65);border-radius:16px;padding:14px;margin-top:2px}
      .reference-source>label{margin-top:0}.reference-upload{display:grid;grid-template-columns:92px 1fr;gap:12px;align-items:center;margin-top:12px;padding:12px;border:1px dashed #4b5470;border-radius:14px;background:#0b0f17}
      .reference-upload[hidden]{display:none}.reference-thumb{width:92px;height:92px;border-radius:12px;object-fit:cover;background:#171c28;border:1px solid #30384b}
      .reference-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}.reference-actions button{padding:9px 11px;font-size:12px}.reference-note{font-size:11px;line-height:1.45;color:var(--muted);margin:6px 0 0}
      .engine-panel{margin-top:14px;border:1px solid var(--line);background:linear-gradient(135deg,rgba(124,92,255,.08),rgba(12,15,23,.7));border-radius:16px;padding:14px}
      .engine-panel h3{margin:0 0 10px;font-size:14px}.engine-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.engine-item{border:1px solid #293146;background:#0b0f16;border-radius:12px;padding:10px}.engine-item span{display:block;color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.08em}.engine-item strong{display:block;margin-top:4px;font-size:12px;line-height:1.35}.engine-active{color:#c9bdff}
      @media(max-width:560px){.reference-upload{grid-template-columns:72px 1fr}.reference-thumb{width:72px;height:72px}.engine-grid{grid-template-columns:1fr}}
    `;document.head.appendChild(s);
  }

  function injectUI(){
    const media=$('mediaMode');if(!media||$('mediaSource'))return;
    const wrap=document.createElement('div');wrap.className='reference-source';wrap.innerHTML=`
      <label for="mediaSource">Origem visual</label>
      <select id="mediaSource"><option value="auto" selected>Criação automática</option><option value="reference">Gerar usando foto de referência</option></select>
      <p class="reference-note" id="referenceModeNote">No modo automático, o sistema escolhe a melhor forma de criar cada cena.</p>
      <div class="reference-upload" id="referenceUpload" hidden>
        <img class="reference-thumb" id="referenceThumb" alt="Prévia da referência">
        <div><strong>Foto de referência</strong><p class="reference-note" id="referenceFileText">Envie JPG, PNG ou WEBP. A foto será usada diretamente na geração visual.</p><div class="reference-actions"><button type="button" class="ghost" id="chooseReferenceBtn">Escolher foto</button><button type="button" class="ghost" id="removeReferenceBtn" hidden>Remover</button></div><input id="referenceImageInput" type="file" accept="image/jpeg,image/png,image/webp" hidden></div>
      </div>`;
    media.parentElement.insertAdjacentElement('afterend',wrap);
    const stage4=document.querySelector('.stage[data-stage="4"] .generate-panel');
    if(stage4){const panel=document.createElement('div');panel.className='engine-panel';panel.id='enginePanel';panel.innerHTML=`<h3>IA e motores em uso</h3><div class="engine-grid"><div class="engine-item"><span>Etapa atual</span><strong class="engine-active" id="engineStage">Aguardando</strong></div><div class="engine-item"><span>Roteiro</span><strong id="engineScript">Qwen 3.8 27B</strong></div><div class="engine-item"><span>Visual</span><strong id="engineVisual">Seleção automática</strong></div><div class="engine-item"><span>Voz</span><strong id="engineVoice">Edge Neural</strong></div></div>`;stage4.insertAdjacentElement('afterend',panel)}
    $('mediaSource').addEventListener('change',()=>{state.mode=$('mediaSource').value==='reference'?'reference':'auto';syncMode()});
    $('chooseReferenceBtn').addEventListener('click',()=>$('referenceImageInput').click());
    $('removeReferenceBtn').addEventListener('click',clearReference);
    $('referenceImageInput').addEventListener('change',async e=>{const file=e.target.files?.[0];if(!file)return;try{setReferenceBusy(true);const result=await compressImage(file);state.b64=result.b64;state.dataUrl=result.dataUrl;state.name=file.name;text('referenceFileText',`${file.name} • pronta para gerar diretamente a partir desta foto.`);$('referenceThumb').src=result.dataUrl;$('removeReferenceBtn').hidden=false;syncPreview()}catch(err){clearReference();text('referenceFileText',err.message||'Não consegui preparar essa foto.')}finally{setReferenceBusy(false)}});
    ['visualStyle','mediaMode','cartoonStyle'].forEach(id=>$(id)?.addEventListener('change',()=>setTimeout(syncMode,0)));
    syncMode();
  }

  function setReferenceBusy(value){state.busy=!!value;const b=$('chooseReferenceBtn');if(b){b.disabled=state.busy;b.textContent=state.busy?'Preparando…':'Escolher foto'}}
  function clearReference(){state.b64='';state.dataUrl='';state.name='';if($('referenceImageInput'))$('referenceImageInput').value='';if($('referenceThumb'))$('referenceThumb').removeAttribute('src');if($('removeReferenceBtn'))$('removeReferenceBtn').hidden=true;text('referenceFileText','Envie JPG, PNG ou WEBP. A foto será usada diretamente na geração visual.');syncPreview()}
  function syncMode(){state.mode=$('mediaSource')?.value==='reference'?'reference':'auto';const ref=state.mode==='reference';if($('referenceUpload'))$('referenceUpload').hidden=!ref;text('referenceModeNote',ref?'A foto será entrada direta da geração. O sistema não buscará imagens ou vídeos parecidos.':'No modo automático, o sistema escolhe a melhor forma de criar cada cena.');const notice=$('visualNotice');if(notice&&ref)notice.textContent='Modo Referência: as cenas visuais serão geradas diretamente a partir da foto enviada, sem busca de mídia parecida.';text('engineVisual',ref?'FLUX.2 Klein • referência obrigatória':'FLUX.2 Klein → FLUX.1 Schnell → auxiliar');syncPreview()}
  function syncPreview(){if(state.mode!=='reference'||!state.dataUrl)return;const photo=$('previewPhoto'),fallback=$('previewIllustration');if(photo){photo.hidden=false;photo.src=state.dataUrl;photo.alt='Foto de referência enviada'}if(fallback)fallback.hidden=true}

  function blobToBase64(blob){return blob.arrayBuffer().then(buf=>{const bytes=new Uint8Array(buf);let binary='';for(let i=0;i<bytes.length;i+=0x8000)binary+=String.fromCharCode(...bytes.subarray(i,i+0x8000));return btoa(binary)})}
  async function compressImage(file){
    if(!/^image\/(jpeg|png|webp)$/i.test(file.type))throw Error('Use uma imagem JPG, PNG ou WEBP.');
    const bitmap=await createImageBitmap(file);let max=512,quality=.78,last=null;
    for(let attempt=0;attempt<8;attempt++){
      const scale=Math.min(1,max/Math.max(bitmap.width,bitmap.height));const w=Math.max(1,Math.round(bitmap.width*scale)),h=Math.max(1,Math.round(bitmap.height*scale));const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d',{alpha:false});ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);ctx.drawImage(bitmap,0,0,w,h);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',quality));if(!blob)throw Error('Não consegui preparar essa foto.');const b64=await blobToBase64(blob);last={b64,dataUrl:`data:image/jpeg;base64,${b64}`};if(b64.length<=26000){bitmap.close?.();return last}quality=Math.max(.42,quality-.09);if(attempt%2===1)max=Math.max(320,max-64)
    }
    bitmap.close?.();if(last?.b64?.length<=30000)return last;throw Error('A foto ficou grande demais. Tente outra imagem com menos detalhes ou resolução menor.');
  }

  function engineFromStatus(data){
    const runs=data?.runs||[],active=runs.find(r=>r.status!=='completed'),latest=runs.find(r=>r.status==='completed'&&r.conclusion==='success');
    if(active){text('engineStage',active.stage||'Processando');text('engineScript','Qwen 3.8 27B');text('engineVisual',state.mode==='reference'?'FLUX.2 Klein • referência obrigatória':'FLUX.2 Klein → FLUX.1 Schnell → auxiliar');text('engineVoice','Edge Neural → alternativa local');return}
    if(latest?.engines){text('engineStage','Concluído');text('engineScript',latest.engines.script||'Qwen 3.8 27B');text('engineVisual',latest.engines.visual||'Não informado');text('engineVoice',latest.engines.voice||'Não informado')}
  }

  function fakeJson(status,obj){return Promise.resolve(new Response(JSON.stringify(obj),{status,headers:{'Content-Type':'application/json'}}))}
  window.fetch=async function(input,init){
    const url=typeof input==='string'?input:input?.url||'';let nextInit=init;
    if(url.includes('/api/scene-query')&&state.mode==='reference'){
      let body={};try{body=JSON.parse(init?.body||'{}')}catch{}
      const desc=String(body.visualDescription||body.narration||'cinematic scene').trim();return fakeJson(200,{visual_query:desc,visual_query_backup:desc,recommended_media:'image',engine:{stage:'visual',model:'FLUX.2 Klein'}})
    }
    if(url.includes('/api/plan')&&init?.method==='POST'){text('engineStage','Criando roteiro');text('engineScript','Qwen 3.8 27B');try{const body=JSON.parse(init.body||'{}');body.mediaSource=state.mode;nextInit={...init,body:JSON.stringify(body)}}catch{}}
    if(url.includes('/api/generate')&&init?.method==='POST'){
      if(state.mode==='reference'&&!state.b64)return fakeJson(400,{error:'Envie uma foto de referência antes de gerar.'});
      if(state.busy)return fakeJson(400,{error:'Aguarde a foto terminar de ser preparada.'});
      text('engineStage','Iniciando geração');try{const body=JSON.parse(init.body||'{}');body.mediaSource=state.mode;if(state.mode==='reference'){body.referenceImageB64=state.b64;body.referenceImageMime='image/jpeg'}nextInit={...init,body:JSON.stringify(body)}}catch{}
    }
    const response=await nativeFetch(input,nextInit);
    if(url.includes('/api/status'))response.clone().json().then(engineFromStatus).catch(()=>{});
    if(url.includes('/api/plan')&&response.ok)response.clone().json().then(()=>text('engineStage','Roteiro pronto')).catch(()=>{});
    if(url.includes('/api/generate')&&response.ok)response.clone().json().then(d=>{if(d?.engines){text('engineVisual',d.engines.visual||'');text('engineVoice',d.engines.voice||'')}text('engineStage','Geração iniciada')}).catch(()=>{});
    return response;
  };

  function boot(){injectStyles();injectUI();const observer=new MutationObserver(()=>{if(state.mode==='reference'&&state.dataUrl)syncPreview()});const preview=$('previewMedia');if(preview)observer.observe(preview,{subtree:true,attributes:true,attributeFilter:['src','hidden']})}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();