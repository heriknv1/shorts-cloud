const crypto=require('crypto');
const {gh,config}=require('./github');
const {requireAuth}=require('./auth');
const {validPrivateSourcePath,signPrivateSource}=require('./source-access');

const SOURCE_TYPES=new Set(['audio','video','link']);
const DOODLE_STYLES=new Set(['clean-doodle','soft-accent','playful-ink']);

function validSourceUrl(value){
  try{
    const url=new URL(String(value||''));
    if(url.protocol!=='https:'||url.username||url.password||String(value).length>1800)return false;
    const host=url.hostname.toLowerCase();
    if(host==='localhost'||host.endsWith('.local')||/^127\./.test(host)||/^10\./.test(host)||/^192\.168\./.test(host)||/^169\.254\./.test(host))return false;
    return true;
  }catch{return false}
}

module.exports=async function handler(req,res){
  if(req.method!=='POST')return res.status(405).json({error:'Use POST.'});if(!requireAuth(req,res))return;
  try{
    const sourceKind=SOURCE_TYPES.has(req.body?.sourceKind)?req.body.sourceKind:'link';
    const sourcePathname=String(req.body?.sourcePathname||'').trim();let sourceUrl=String(req.body?.sourceUrl||'').trim();
    if(sourceKind==='link'){if(!validSourceUrl(sourceUrl))return res.status(400).json({error:'Envie um link público válido.'})}
    else{if(!validPrivateSourcePath(sourcePathname))return res.status(400).json({error:'Envie um arquivo de áudio ou vídeo válido.'});sourceUrl=await signPrivateSource(sourcePathname)}
    if(req.body?.rightsConfirmed!==true)return res.status(400).json({error:'Confirme que você tem autorização para utilizar esse conteúdo.'});
    const sourceMime=String(req.body?.sourceMime||'application/octet-stream').replace(/[^A-Za-z0-9.+\-/]/g,'').slice(0,90)||'application/octet-stream';
    const sourceName=String(req.body?.sourceName||'conteudo').replace(/[\r\n\0]/g,' ').trim().slice(0,160)||'conteudo';
    const userContext=String(req.body?.userContext||'').replace(/[\r\0]/g,' ').trim().slice(0,600);
    const doodleStyle=DOODLE_STYLES.has(req.body?.doodleStyle)?req.body.doodleStyle:'clean-doodle';
    const requestId=`ill-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;
    const planKey=crypto.randomBytes(32).toString('hex');
    const{repo}=config();
    const activeData=await gh(`/repos/${repo}/actions/workflows/analyze-illustrated.yml/runs?event=workflow_dispatch&per_page=10`).catch(()=>({workflow_runs:[]}));
    if((activeData.workflow_runs||[]).some(run=>run.status!=='completed'))return res.status(409).json({error:'Já existe um conteúdo sendo analisado. Aguarde a conclusão antes de iniciar outro.',active:true});
    await gh(`/repos/${repo}/actions/workflows/analyze-illustrated.yml/dispatches`,{method:'POST',body:JSON.stringify({ref:'main',inputs:{source_url:sourceUrl,source_kind:sourceKind,source_mime:sourceMime,source_name:sourceName,user_context:userContext,doodle_style:doodleStyle,request_id:requestId,plan_key:planKey}})});
    res.setHeader('Cache-Control','no-store');return res.status(202).json({ok:true,analysisId:requestId,analysisKey:planKey,stage:'Análise iniciada.'});
  }catch(error){console.error('illustrated-plan',error);return res.status(500).json({error:'Não foi possível iniciar a análise agora. Tente novamente em alguns instantes.'})}
};
