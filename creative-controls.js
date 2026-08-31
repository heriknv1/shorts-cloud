(()=>{
  const nativeFetch=window.fetch.bind(window);
  const $=id=>document.getElementById(id);

  function value(id,fallback=''){return $(id)?.value||fallback}
  function ensurePunctuation(text){const t=String(text||'').trim();return t&&!/[.!?…]$/.test(t)?`${t}.`:t}
  function replaceOpening(text,hook){
    const h=ensurePunctuation(hook),src=String(text||'').trim();
    if(!h)return src;
    const rest=src.replace(/^[^.!?…]{0,220}[.!?…]\s*/,'').trim();
    return `${h}${rest?` ${rest}`:''}`.trim();
  }

  function injectStageOne(){
    const topic=$('topic');if(!topic||$('hookMode'))return;
    const box=document.createElement('div');box.className='creative-settings';
    box.innerHTML=`<div class="creative-grid">
      <div><label for="hookMode">Gancho inicial</label><select id="hookMode"><option value="auto" selected>Automático — a IA escolhe o melhor formato</option><option value="manual">Manual — escrever meu próprio gancho</option></select></div>
      <div><label for="writingStyle">Estilo do roteiro</label><select id="writingStyle"><option value="natural" selected>Natural e humano</option><option value="conversational">Conversa direta</option><option value="impactful">Impactante</option><option value="neutral">Neutro</option></select></div>
    </div><div id="manualHookWrap" hidden><label for="manualHook">Seu gancho <span class="muted">(abre o vídeo exatamente com esta ideia)</span></label><textarea id="manualHook" rows="2" maxlength="220" placeholder="Ex.: Você teria coragem de entrar neste lugar depois de saber o que aconteceu aqui?"></textarea><div class="muted">Use uma frase curta e forte. Ela será integrada ao restante do roteiro sem alterar os fatos.</div></div>`;
    topic.insertAdjacentElement('afterend',box);
    $('hookMode')?.addEventListener('change',()=>{$('manualHookWrap').hidden=value('hookMode','auto')!=='manual'});
  }

  function injectStageTwo(){
    const grid=document.querySelector('[data-stage="2"] .option-grid');if(!grid||$('editingPace'))return;
    const html=`
      <div><label for="editingPace">Ritmo da edição</label><select id="editingPace"><option value="balanced">Dinâmica equilibrada</option><option value="fast">Cortes rápidos</option><option value="cinematic" selected>Cinematográfica</option></select></div>
      <div><label for="sfxMode">Efeitos sonoros</label><select id="sfxMode"><option value="subtle">Discretos</option><option value="dynamic">Mais presentes</option><option value="off" selected>Desativados</option></select></div>
      <div><label for="ambienceMode">Ambiência</label><select id="ambienceMode"><option value="subtle" selected>Leve e contextual</option><option value="off">Desativada</option></select></div>
      <div><label for="cleanExport">Versão extra sem legenda</label><select id="cleanExport"><option value="on">Sim — para usar legenda nativa da rede</option><option value="off" selected>Não</option></select></div>
      <div><label for="brandingMode">Assinatura visual</label><select id="brandingMode"><option value="off" selected>Desativada</option><option value="on">Ativada</option></select></div>
      <div id="brandTextWrap" hidden><label for="brandText">Nome do canal</label><input id="brandText" maxlength="48" placeholder="Ex.: Histórias em 1 Minuto"></div>`;
    const holder=document.createElement('div');holder.style.display='contents';holder.innerHTML=html;while(holder.firstChild)grid.appendChild(holder.firstChild);
    $('brandingMode')?.addEventListener('change',()=>{$('brandTextWrap').hidden=value('brandingMode','off')!=='on'});
    const notice=document.createElement('div');notice.className='notice';notice.id='creativeNotice';notice.textContent='O vídeo recebe ritmo de edição, movimentos de câmera, efeitos discretos e direção visual coerente com cada fala.';grid.parentElement?.insertBefore(notice,grid.nextSibling);
  }

  function injectStyles(){if($('creativeControlsStyles'))return;const s=document.createElement('style');s.id='creativeControlsStyles';s.textContent='.creative-settings{margin:14px 0 18px;padding:14px;border:1px solid rgba(255,255,255,.08);border-radius:16px;background:rgba(255,255,255,.02)}.creative-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.creative-settings textarea{width:100%}#manualHookWrap{margin-top:12px}@media(max-width:720px){.creative-grid{grid-template-columns:1fr}}';document.head.appendChild(s)}

  function patchBody(body){
    try{
      const data=JSON.parse(body||'{}');
      data.hookMode=value('hookMode','auto');
      data.manualHook=data.hookMode==='manual'?String(value('manualHook','')).trim().slice(0,220):'';
      data.writingStyle=value('writingStyle','natural');
      data.editingPace=value('editingPace','cinematic');
      data.sfxMode=value('sfxMode','off');
      data.ambienceMode=value('ambienceMode','subtle');
      data.cleanExport=value('cleanExport','off');
      data.brandingMode=value('brandingMode','off');
      data.brandText=data.brandingMode==='on'?String(value('brandText','')).trim().slice(0,48):'';
      return JSON.stringify(data);
    }catch{return body}
  }

  async function patchPlanResponse(response){
    if(!response.ok||value('hookMode','auto')!=='manual')return response;
    const hook=String(value('manualHook','')).trim();if(!hook)return response;
    try{
      const data=await response.clone().json();
      if(!data?.plan?.scenes?.length)return response;
      data.plan.scenes[0].narration=replaceOpening(data.plan.scenes[0].narration,hook);
      data.plan.scenes[0].beat='Gancho';
      data.plan.scenes[0].visual_description=`Abertura visual diretamente ligada ao gancho: ${hook}. ${data.plan.scenes[0].visual_description||''}`.slice(0,900);
      return new Response(JSON.stringify(data),{status:response.status,statusText:response.statusText,headers:new Headers(response.headers)});
    }catch{return response}
  }

  window.fetch=async function(input,init){
    const url=typeof input==='string'?input:input?.url||'';
    const isPost=init?.method==='POST';
    const isPlan=isPost&&(url.includes('/api/plan')||url.includes('/api/horror-plan'));
    const isGenerate=isPost&&url.includes('/api/generate');
    let nextInit=init;
    if(isPlan||isGenerate)nextInit={...init,body:patchBody(init.body)};
    let response=await nativeFetch(input,nextInit);
    if(isPlan)response=await patchPlanResponse(response);
    return response;
  };

  function boot(){injectStageOne();injectStageTwo();injectStyles()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
