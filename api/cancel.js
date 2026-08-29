const { gh, config, workflowRuns } = require('../lib/github');
const { requireAuth } = require('../lib/auth');

const wait=ms=>new Promise(r=>setTimeout(r,ms));

async function findActiveRun(runId){
  for(let attempt=0;attempt<4;attempt++){
    const data=await workflowRuns();
    const runs=(data.workflow_runs||[]).filter(r=>r.name==='Generate Short'&&r.status!=='completed');
    const found=runId?runs.find(r=>String(r.id)===String(runId)):runs[0];
    if(found)return found;
    if(attempt<3)await wait(700);
  }
  return null;
}

module.exports=async function handler(req,res){
  if(req.method!=='POST')return res.status(405).json({error:'Use POST.'});
  if(!requireAuth(req,res))return;
  try{
    const { repo }=config();
    const run=await findActiveRun(req.body?.runId);
    if(!run)return res.status(409).json({error:'Não há uma geração em andamento para cancelar.'});
    await gh(`/repos/${repo}/actions/runs/${run.id}/cancel`,{method:'POST'});
    return res.status(202).json({ok:true,runId:run.id,message:'Cancelamento solicitado. Assim que for confirmado, esta geração não contará na sua cota diária.'});
  }catch(error){
    console.error(error);
    return res.status(500).json({error:'Não foi possível cancelar agora. Tente novamente em alguns segundos.'});
  }
};