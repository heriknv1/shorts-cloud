const {issueSignedToken,presignUrl}=require('@vercel/blob');

const PRIVATE_SOURCE_RX=/^illustrated-inputs\/[A-Za-z0-9._-]{1,200}$/;

function validPrivateSourcePath(value){
  return PRIVATE_SOURCE_RX.test(String(value||''));
}

async function signPrivateSource(pathname){
  if(!validPrivateSourcePath(pathname))throw new Error('Arquivo temporário inválido.');
  const validUntil=Date.now()+3*60*60*1000;
  const token=await issueSignedToken({pathname,operations:['get'],validUntil});
  const {presignedUrl}=await presignUrl(token,{operation:'get',pathname,access:'private',validUntil,useCache:false});
  return presignedUrl;
}

module.exports={validPrivateSourcePath,signPrivateSource};
