const crypto=require('crypto');
const zlib=require('zlib');

const VERSION='SCW1';
const KEY_CONTEXT='short-cloud-workflow-payload-v1\0';

function workflowSecret(){
  const value=String(process.env.WORKFLOW_PAYLOAD_SECRET||process.env.GROQ_API_KEY||'').trim();
  if(value.length<16)throw new Error('A proteção dos dados do processamento não está configurada.');
  return value;
}

function deriveKey(){
  return crypto.createHash('sha256').update(KEY_CONTEXT).update(workflowSecret()).digest();
}

function encode(value){
  return Buffer.from(value).toString('base64url');
}

function sealWorkflowPayload(payload,requestId){
  const id=String(requestId||'').trim();
  if(!/^[A-Za-z0-9._-]{8,100}$/.test(id))throw new Error('Identificador de processamento inválido.');
  const serialized=Buffer.from(JSON.stringify({...payload,request_id:id}),'utf8');
  if(serialized.length>180000)throw new Error('Os dados do processamento ficaram grandes demais.');
  const compressed=zlib.deflateRawSync(serialized,{level:9});
  const nonce=crypto.randomBytes(12),cipher=crypto.createCipheriv('aes-256-gcm',deriveKey(),nonce);
  cipher.setAAD(Buffer.from(`short-cloud:${id}`,'utf8'));
  const encrypted=Buffer.concat([cipher.update(compressed),cipher.final()]),tag=cipher.getAuthTag();
  const token=[VERSION,encode(nonce),encode(encrypted),encode(tag)].join('.');
  if(token.length>60000)throw new Error('Os dados protegidos do processamento ficaram grandes demais.');
  return token;
}

module.exports={sealWorkflowPayload};
