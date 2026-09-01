const {list,del}=require('@vercel/blob');
const {gh,config}=require('./github');

module.exports=async function handler(req,res){
  if(req.method!=='GET')return res.status(405).json({error:'Use GET.'});
  const expected=String(process.env.CRON_SECRET||'');const supplied=String(req.headers.authorization||'');if(!expected||supplied!==`Bearer ${expected}`)return res.status(401).json({error:'Não autorizado.'});
  try{
    const cutoff=Date.now()-24*60*60*1000;let cursor,removedBlobs=0;
    do{
      const page=await list({prefix:'illustrated-inputs/',limit:1000,cursor});const old=(page.blobs||[]).filter(x=>new Date(x.uploadedAt).getTime()<cutoff).map(x=>x.url);if(old.length){await del(old);removedBlobs+=old.length}cursor=page.hasMore?page.cursor:undefined;
    }while(cursor);
    let removedAnalyses=0;const{repo}=config(),releases=await gh(`/repos/${repo}/releases?per_page=100`).catch(()=>[]);
    for(const release of releases||[]){if(!String(release.tag_name||'').startsWith('analysis-')||new Date(release.created_at).getTime()>=cutoff)continue;await gh(`/repos/${repo}/releases/${release.id}`,{method:'DELETE'}).catch(()=>null);await gh(`/repos/${repo}/git/refs/tags/${encodeURIComponent(release.tag_name)}`,{method:'DELETE'}).catch(()=>null);removedAnalyses++}
    return res.status(200).json({ok:true,removedBlobs,removedAnalyses});
  }catch(error){console.error('cleanup-sources',error);return res.status(500).json({error:'Falha ao limpar arquivos temporários.'})}
};
