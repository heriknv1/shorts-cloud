(()=>{
  const KEY='short-cloud-content-history-v2';
  const nativeFetch=window.fetch.bind(window);
  const $=id=>document.getElementById(id);
  function read(){try{const v=JSON.parse(localStorage.getItem(KEY)||'[]');return Array.isArray(v)?v:[]}catch{return[]}}
  function write(items){try{localStorage.setItem(KEY,JSON.stringify(items.slice(0,40)))}catch{}}
  function activePreset(){return document.querySelector('.preset.active')?.dataset?.preset||''}
  function remember(plan,preset){
    const title=String(plan?.title||'').trim();if(!title)return;
    const list=read().filter(x=>String(x?.title||'').toLowerCase()!==title.toLowerCase());
    list.unshift({preset:String(preset||plan?.niche_key||'custom'),title,at:Date.now()});write(list);
  }
  function recentFor(preset){
    const list=read(),same=list.filter(x=>x.preset===preset),chosen=same.length>=6?same:list;
    return chosen.map(x=>x.title).filter(Boolean).slice(0,18);
  }
  window.fetch=async function(input,init){
    const url=typeof input==='string'?input:input?.url||'';let nextInit=init,preset='';
    const isPlan=init?.method==='POST'&&(url.includes('/api/plan')||url.includes('/api/horror-plan')||url.includes('/api/horror-real-plan'));
    if(isPlan){
      try{
        const body=JSON.parse(init.body||'{}');preset=body.presetKey||activePreset()||'custom';
        body.avoidTopics=[...new Set([...(Array.isArray(body.avoidTopics)?body.avoidTopics:[]),...recentFor(preset)])].slice(0,18);
        body.voiceSpeed=$('voiceSpeed')?.value||body.voiceSpeed||'default';
        nextInit={...init,body:JSON.stringify(body)};
      }catch{}
    }
    const response=await nativeFetch(input,nextInit);
    if(isPlan&&response.ok){response.clone().json().then(d=>{if(d?.plan)remember(d.plan,preset||activePreset())}).catch(()=>{})}
    return response;
  };
})();
