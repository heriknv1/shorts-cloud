const { createSessionToken, verifyCredentials, setSessionCookie } = require('../lib/auth');
const attempts=new Map();
const WINDOW_MS=15*60*1000,MAX_ATTEMPTS=8,BLOCK_MS=10*60*1000;
function keyFor(req){return String(req.headers['x-forwarded-for']||req.socket?.remoteAddress||'unknown').split(',')[0].trim()}
function stateFor(key){const now=Date.now(),s=attempts.get(key);if(!s||now-s.windowStart>WINDOW_MS){const n={count:0,windowStart:now,blockedUntil:0};attempts.set(key,n);return n}return s}
module.exports=async function handler(req,res){
 if(req.method!=='POST')return res.status(405).json({error:'Use POST.'});
 try{
  const k=keyFor(req),s=stateFor(k),now=Date.now();
  if(s.blockedUntil>now)return res.status(429).json({error:'Muitas tentativas. Aguarde alguns minutos e tente novamente.'});
  const username=String(req.body?.username||'').trim(),password=String(req.body?.password||'');
  if(!username||!password)return res.status(400).json({error:'Informe usuário e senha.'});
  if(!verifyCredentials(username,password)){
    s.count+=1;if(s.count>=MAX_ATTEMPTS)s.blockedUntil=now+BLOCK_MS;attempts.set(k,s);
    return res.status(401).json({error:'Usuário ou senha incorretos.'});
  }
  attempts.delete(k);setSessionCookie(res,createSessionToken(username));res.setHeader('Cache-Control','no-store');return res.status(200).json({ok:true,username});
 }catch(error){console.error(error);return res.status(500).json({error:'Não foi possível entrar agora.'})}
};