const {unzipSync}=require('fflate');
const crypto=require('crypto');
const {gh,ghBuffer,config}=require('../lib/github');
const {requireAuth}=require('../lib/auth');

function validId(value){return /^ill-[0-9]{10,16}-[a-f0-9]{8}$/.test(String(value||''))}
function decryptPlan(payload,id,keyHex){
  if(!/^[a-f0-9]{64}$/.test(keyHex)||payload.length<33||payload.subarray(0,4).toString()!=='ILA1')throw new Error('chave inválida');
  const nonce=payload.subarray(4,16),encrypted=payload.subarray(16),tag=encrypted.subarray(encrypted.length-16),ciphertext=encrypted.subarray(0,encrypted.length-16);
  const decipher=crypto.createDecipheriv('aes-256-gcm',Buffer.from(keyHex,'hex'),nonce);decipher.setAAD(Buffer.from(id));decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(ciphertext),decipher.final()]).toString('utf8');
}
function stageFromJobs(jobs){
  const steps=jobs?.jobs?.[0]?.steps||[];
  const map=[['Baixar e preparar o conteúdo','Preparando o conteúdo enviado…'],['Transcrever e compreender','Entendendo as falas e o contexto…'],['Criar storyboard ilustrado','Planejando personagens, reações e piadas visuais…'],['Disponibilizar storyboard','Finalizando o storyboard…']];
  let stage='Aguardando o processamento começar…';
  for(const[name,label]of map){const step=steps.find(x=>x.name===name);if(step?.status==='in_progress')return label;if(step?.status==='completed')stage=label}
  return stage;
}

module.exports=async function handler(req,res){
  if(req.method!=='GET')return res.status(405).json({error:'Use GET.'});if(!requireAuth(req,res))return;
  const id=String(req.query?.id||''),analysisKey=String(req.headers['x-analysis-key']||'');if(!validId(id)||!/^[a-f0-9]{64}$/.test(analysisKey))return res.status(400).json({error:'Identificador de análise inválido.'});
  try{
    const{repo}=config(),runs=await gh(`/repos/${repo}/actions/workflows/analyze-illustrated.yml/runs?event=workflow_dispatch&per_page=30`),run=(runs.workflow_runs||[]).find(x=>String(x.display_title||'').includes(id));
    if(!run)return res.status(200).json({ready:false,stage:'Aguardando o processamento começar…'});
    if(run.status==='completed'&&run.conclusion!=='success')return res.status(200).json({ready:false,failed:true,error:'Não foi possível compreender esse conteúdo. Se o link estiver bloqueado, envie o arquivo de áudio ou vídeo diretamente.'});
    if(run.status==='completed'){
      const artifacts=await gh(`/repos/${repo}/actions/runs/${run.id}/artifacts?per_page=20`),artifact=(artifacts.artifacts||[]).find(x=>x.name===`storyboard-${id}`&&!x.expired);
      if(!artifact)return res.status(200).json({ready:false,stage:'Finalizando o storyboard criativo…'});
      const archive=await ghBuffer(`/repos/${repo}/actions/artifacts/${artifact.id}/zip`),files=unzipSync(new Uint8Array(archive)),entry=Object.entries(files).find(([name])=>name.endsWith('illustrated_plan.enc'));
      if(!entry)throw new Error('storyboard ausente');const raw=decryptPlan(Buffer.from(entry[1]),id,analysisKey);if(raw.length>80000)throw new Error('plano grande demais');const plan=JSON.parse(raw);if(!Array.isArray(plan?.scenes)||plan.scenes.length<4)throw new Error('plano inválido');
      res.setHeader('Cache-Control','no-store');return res.status(200).json({ready:true,stage:'Storyboard criativo pronto.',plan});
    }
    const jobs=run.status==='completed'?null:await gh(`/repos/${repo}/actions/runs/${run.id}/jobs?per_page=5`).catch(()=>null);
    res.setHeader('Cache-Control','no-store');return res.status(200).json({ready:false,stage:stageFromJobs(jobs)});
  }catch(error){console.error('illustrated-status',error);return res.status(500).json({error:'Não foi possível acompanhar a análise agora.'})}
};
