const {gh,config}=require('../lib/github');
const {requireAuth}=require('../lib/auth');

module.exports=async function handler(req,res){
  if(req.method!=='POST')return res.status(405).json({error:'Use POST.'});if(!requireAuth(req,res))return;
  const id=String(req.body?.id||'');if(!/^ill-[0-9]{10,16}-[a-f0-9]{8}$/.test(id))return res.status(400).json({error:'Identificador de análise inválido.'});
  try{
    const{repo}=config(),data=await gh(`/repos/${repo}/actions/workflows/analyze-illustrated.yml/runs?event=workflow_dispatch&per_page=30`),run=(data.workflow_runs||[]).find(x=>x.status!=='completed'&&String(x.display_title||'').includes(id));
    if(!run)return res.status(409).json({error:'Essa análise já foi encerrada.'});
    await gh(`/repos/${repo}/actions/runs/${run.id}/cancel`,{method:'POST'});return res.status(202).json({ok:true,message:'Análise cancelada.'});
  }catch(error){console.error('illustrated-cancel',error);return res.status(500).json({error:'Não foi possível cancelar a análise agora.'})}
};
