const { workflowRuns } = require('./github');

function cleanText(value,max=180){return String(value||'').trim().replace(/\s+/g,' ').slice(0,max)}
function normalize(value){return cleanText(value,240).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9 ]/g,' ').replace(/\s+/g,' ').trim()}
function clientAvoid(body){
  const raw=Array.isArray(body?.avoidTopics)?body.avoidTopics:[];
  return [...new Set(raw.map(v=>cleanText(v,180)).filter(Boolean))].slice(0,18);
}
async function recentGeneratedTitles(limit=18){
  try{
    const data=await workflowRuns();
    return [...new Set((data.workflow_runs||[])
      .filter(r=>r.status==='completed'&&r.conclusion==='success')
      .map(r=>cleanText(String(r.display_title||'').replace(/^Short Cloud Studio\s*[—-]\s*/i,''),180))
      .filter(Boolean))].slice(0,limit);
  }catch{return []}
}
async function buildAvoidance(body){
  const local=clientAvoid(body),remote=await recentGeneratedTitles();
  return [...new Set([...local,...remote])].slice(0,24);
}
function avoidText(items){
  if(!items?.length)return 'Nenhum conteúdo recente registrado; ainda assim crie uma abordagem específica e não genérica.';
  return items.map((v,i)=>`${i+1}. ${v}`).join('\n');
}
function narrationWordCount(plan){
  return (plan?.scenes||[]).reduce((sum,s)=>sum+String(s?.narration||'').trim().split(/\s+/).filter(Boolean).length,0);
}
function speedFactor(speed){return speed==='veryfast'?1.15:speed==='fast'?1.08:1}
function targetNarrationWords(duration,speed){
  const seconds=Math.min(70,Math.max(20,Number(duration)||60));
  return Math.round(seconds*2.15*speedFactor(speed));
}
function minNarrationWords(duration,speed){return Math.round(targetNarrationWords(duration,speed)*0.86)}
function maxNarrationWords(duration,speed){return Math.round(targetNarrationWords(duration,speed)*1.10)}
function similarity(a,b){
  const aa=new Set(normalize(a).split(' ').filter(x=>x.length>2)),bb=new Set(normalize(b).split(' ').filter(x=>x.length>2));
  if(!aa.size||!bb.size)return 0;
  let common=0;for(const x of aa)if(bb.has(x))common++;
  return common/Math.min(aa.size,bb.size);
}
function tooSimilar(title,avoid){return (avoid||[]).some(v=>similarity(title,v)>=0.72)}
function pickUnused(list,avoid,describe=x=>String(x)){
  const candidates=(list||[]).filter(x=>!(avoid||[]).some(v=>similarity(describe(x),v)>=0.58));
  const pool=candidates.length?candidates:list;
  return pool[Math.floor(Math.random()*pool.length)];
}
module.exports={cleanText,clientAvoid,recentGeneratedTitles,buildAvoidance,avoidText,narrationWordCount,targetNarrationWords,minNarrationWords,maxNarrationWords,tooSimilar,pickUnused,speedFactor};
