(()=>{
  const nativeFetch=window.fetch.bind(window);
  let sceneQueue=Promise.resolve();
  let blankTopicBeforePlan=false;

  function queuedFetch(input,init){
    const url=typeof input==='string'?input:input?.url||'';
    if(!String(url).includes('/api/scene-query'))return nativeFetch(input,init);
    const task=()=>nativeFetch(input,init);
    const result=sceneQueue.then(task,task);
    sceneQueue=result.then(()=>undefined,()=>undefined);
    return result;
  }
  window.fetch=queuedFetch;

  function boot(){
    const topic=document.getElementById('topic');
    const planBtn=document.getElementById('planBtn');
    if(planBtn&&topic){
      planBtn.addEventListener('click',()=>{blankTopicBeforePlan=!topic.value.trim()},{capture:true});
      const workspace=document.querySelector('.workspace');
      if(workspace){
        new MutationObserver(()=>{
          const stage3=document.querySelector('.stage[data-stage="3"].active');
          if(stage3&&blankTopicBeforePlan){topic.value='';blankTopicBeforePlan=false}
        }).observe(workspace,{subtree:true,attributes:true,attributeFilter:['class']});
      }
    }
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();