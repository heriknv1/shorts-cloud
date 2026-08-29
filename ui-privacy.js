(()=>{
  const replacements=[
    [/\bGitHub\b/gi,'serviço interno'],
    [/\bGitHub Actions\b/gi,'processamento interno'],
    [/\bActions\b/gi,'processamento'],
    [/\bVercel\b/gi,'plataforma'],
    [/\bPexels\b/gi,'biblioteca de mídia'],
    [/\bGroq\b/gi,'serviço de inteligência'],
    [/\bdeploy(?:ment)?\b/gi,'atualização'],
    [/\brelease\b/gi,'publicação'],
    [/\breposit[oó]rio\b/gi,'projeto'],
    [/\bworkflow\b/gi,'processo'],
    [/\brenderiza(?:r|ção|do|ndo)\b/gi,'gera$&'.replace('$&','')],
    [/\brender(?:s)?\b/gi,'gerações'],
    [/\bMP4\b/g,'vídeo']
  ];

  const stageMap=[
    [/Baixar Short Cloud Studio/i,'Preparando'],
    [/Preparar Python/i,'Preparando recursos'],
    [/Instalar motor de vídeo/i,'Preparando recursos'],
    [/Preparar voz brasileira/i,'Preparando narração'],
    [/Gerar mídia e montar vídeo/i,'Criando vídeo'],
    [/Validar MP4/i,'Finalizando vídeo'],
    [/Guardar vídeo/i,'Finalizando vídeo'],
    [/Publicar MP4/i,'Vídeo pronto']
  ];

  function clean(text){
    if(!text)return text;
    let out=String(text);
    for(const [rx,value] of stageMap) out=out.replace(rx,value);
    for(const [rx,value] of replacements) out=out.replace(rx,value);
    out=out
      .replace(/Escolha conteúdo, visual, mídia, voz e legenda antes de gerar\.?/i,'Escolha conteúdo, visual, mídia, voz e legenda antes de criar seu vídeo.')
      .replace(/Vídeos hoje/i,'Criações hoje')
      .replace(/Você ainda não gastou uma? gerações?\.?/i,'Você ainda não iniciou a geração.')
      .replace(/Pronto para gerar\??/i,'Pronto para criar seu vídeo?')
      .replace(/Nenhuma? gerações? ainda\.?/i,'Nenhum vídeo criado ainda.')
      .replace(/Enviando vídeo para geração…?/i,'Preparando seu vídeo…')
      .replace(/Geração iniciado/i,'Geração iniciada')
      .replace(/o sistema busca fotos e\/ou vídeos da biblioteca de mídia de acordo com cada cena\.?/i,'o sistema seleciona fotos e/ou vídeos de acordo com cada cena.')
      .replace(/Falha no status/gi,'Não foi possível atualizar agora');
    return out;
  }

  function sanitizeNode(node){
    if(node.nodeType===Node.TEXT_NODE){
      const next=clean(node.nodeValue);
      if(next!==node.nodeValue)node.nodeValue=next;
      return;
    }
    if(node.nodeType!==Node.ELEMENT_NODE)return;
    const tag=node.tagName;
    if(tag==='SCRIPT'||tag==='STYLE'||tag==='NOSCRIPT')return;
    for(const attr of ['title','aria-label','placeholder']){
      if(node.hasAttribute?.(attr)){
        const old=node.getAttribute(attr),next=clean(old);
        if(next!==old)node.setAttribute(attr,next);
      }
    }
    node.childNodes.forEach(sanitizeNode);
  }

  function run(){sanitizeNode(document.body)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
  new MutationObserver(muts=>{for(const m of muts){if(m.type==='characterData')sanitizeNode(m.target);m.addedNodes.forEach(sanitizeNode)}}).observe(document.documentElement,{subtree:true,childList:true,characterData:true});
})();