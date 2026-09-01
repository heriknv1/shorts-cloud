const { handleUpload } = require('@vercel/blob/client');
const { getSession } = require('./auth');

const ALLOWED_TYPES = [
  'audio/mpeg','audio/mp3','audio/mp4','audio/m4a','audio/x-m4a','audio/aac','audio/x-aac','audio/wav','audio/x-wav','audio/ogg','audio/opus','audio/webm','audio/flac',
  'video/mp4','video/webm','video/quicktime','video/x-m4v','video/mpeg','video/ogg','video/3gpp','video/x-matroska'
];

module.exports = async function handler(req,res){
  if(req.method!=='POST')return res.status(405).json({error:'Use POST.'});
  const eventType=String(req.body?.type||'');
  if(eventType==='blob.generate-client-token'){
    if(!getSession(req))return res.status(401).json({error:'Sua sessão expirou. Entre novamente antes de enviar o arquivo.'});
    if(!String(process.env.BLOB_READ_WRITE_TOKEN||'').trim())return res.status(503).json({error:'O armazenamento temporário está indisponível no momento.'});
  }
  try{
    const result=await handleUpload({
      body:req.body,
      request:req,
      onBeforeGenerateToken:async pathname=>{
        if(!getSession(req))throw new Error('Sessão expirada ou acesso não autorizado.');
        if(!String(pathname||'').startsWith('illustrated-inputs/'))throw new Error('Destino de arquivo inválido.');
        return{
          allowedContentTypes:ALLOWED_TYPES,
          maximumSizeInBytes:200*1024*1024,
          addRandomSuffix:true,
          cacheControlMaxAge:60,
          tokenPayload:JSON.stringify({purpose:'illustrated-source',createdAt:Date.now()})
        };
      },
      onUploadCompleted:async()=>{}
    });
    return res.status(200).json(result);
  }catch(error){
    console.error('source-upload',error);
    const message=String(error?.message||'');
    if(/token|store|blob/i.test(message))return res.status(503).json({error:'O armazenamento temporário não conseguiu autorizar o envio agora.'});
    return res.status(400).json({error:message||'Não foi possível enviar o arquivo.'});
  }
};
