(()=>{
  const nativeFetch=window.fetch.bind(window);
  const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const isPlan=url=>String(url||'').includes('/api/plan');

  async function resilientFetch(input,init){
    const url=typeof input==='string'?input:input?.url||'';
    if(!isPlan(url))return nativeFetch(input,init);

    let response=await nativeFetch(input,init);
    if(response.status!==429)return response;

    for(let attempt=0;attempt<1&&response.status===429;attempt++){
      let retryAfter=10;
      try{
        const data=await response.clone().json();
        retryAfter=Math.max(8,Math.min(30,Number(data.retryAfterSeconds)||10));
      }catch{}
      const message=document.getElementById('message');
      if(message){
        message.hidden=false;
        message.style.color='';
        message.textContent=`Muita atividade no momento. Tentando novamente automaticamente em ${Math.ceil(retryAfter)} segundos…`;
      }
      await wait(retryAfter*1000);
      response=await nativeFetch(input,init);
    }
    return response;
  }

  window.fetch=resilientFetch;
})();
