const { requireAuth } = require('../lib/auth');
function compact(value,max=16){return String(value||'').trim().replace(/\s+/g,' ').split(' ').filter(Boolean).slice(0,max).join(' ')}
function fallback(description,narration,analog=false){
  const base=compact(description||narration||'dark cinematic suspense scene',16);
  if(analog)return{visual_query:`${base} analog horror VHS CRT broadcast scanlines tracking error red black 4:3`.slice(0,210),visual_query_backup:`${compact(base,12)} surveillance tape alternate frame analog static institutional archive`.slice(0,210)};
  return{
    visual_query:`${base} psychological horror suspense low key lighting cinematic non graphic`.slice(0,210),
    visual_query_backup:`${compact(base,12)} alternate angle deep shadows practical light suspense cinematic`.slice(0,210)
  };
}
module.exports=async function handler(req,res){
  if(req.method!=='POST')return res.status(405).json({error:'Use POST.'});
  if(!requireAuth(req,res))return;
  const description=String(req.body?.visualDescription||'').trim();
  const narration=String(req.body?.narration||'').trim();
  const analog=req.body?.presetKey==='analog-horror';
  const visualStyle=req.body?.visualStyle==='cartoon'?'cartoon':'realistic';
  const mediaMode=['photos','videos','hybrid'].includes(req.body?.mediaMode)?req.body.mediaMode:'hybrid';
  if(!description&&!narration)return res.status(400).json({error:'Descreva a cena.'});
  const safe=fallback(description,narration,analog),key=process.env.GROQ_API_KEY;
  if(!key)return res.status(200).json({...safe,recommended_media:mediaMode==='videos'?'video':'image'});
  try{
    const prompt=`Transforme esta cena de ${analog?'terror analógico VHS':'terror/suspense'} em duas descrições visuais específicas EM INGLÊS.\nDESCRIÇÃO: ${description||narration}\nNARRAÇÃO: ${narration}\nESTILO: ${visualStyle}\nMÍDIA: ${mediaMode}\nREGRAS:\n- Mostre a ação exata e o detalhe inquietante da cena.\n- ${analog?'Faça parecer um quadro de fita VHS/CRT em 4:3: transmissão institucional, câmera de segurança, gráfico de emergência ou gravação doméstica; use scanlines, tracking error, timestamp, red/black/gray palette e composição simples.':'Priorize suspense psicológico, composição cinematográfica, negative space, deep shadows, practical light, reflections, silhouettes, doorway framing ou background detail quando fizer sentido.'}\n- Não use gore, mutilação ou violência gráfica como preenchimento.\n- 8 a 16 palavras, termos positivos e específicos.\n- As duas opções precisam ser diferentes.\n- Preserve local, personagem e época descritos.\n- Em hybrid use image para cenas sobrenaturais/específicas e video para movimento genérico útil; em photos use image; em videos use video.\nResponda SOMENTE JSON: {"visual_query":"...","visual_query_backup":"...","recommended_media":"image ou video"}`;
    const response=await fetch('https://api.groq.com/openai/v1/chat/completions',{method:'POST',headers:{Authorization:`Bearer ${key}`,'Content-Type':'application/json'},body:JSON.stringify({model:process.env.GROQ_MODEL||'qwen/qwen3.8-27b',temperature:.18,max_completion_tokens:350,response_format:{type:'json_object'},messages:[{role:'user',content:prompt}]})});
    const data=await response.json();if(!response.ok)throw Error('temporary');
    const parsed=JSON.parse(String(data.choices?.[0]?.message?.content||'{}'));
    let primary=compact(parsed.visual_query,16)||safe.visual_query;
    let backup=compact(parsed.visual_query_backup,16)||safe.visual_query_backup;
    primary=`${primary} ${analog?'analog horror VHS CRT broadcast scanlines red black 4:3':'psychological horror suspense cinematic low key lighting non graphic'}`.slice(0,210);
    backup=`${backup} ${analog?'alternate VHS surveillance frame tracking error institutional archive':'alternate angle cinematic suspense practical light deep shadows'}`.slice(0,210);
    let recommended=parsed.recommended_media==='video'?'video':'image';
    if(mediaMode==='photos')recommended='image';if(mediaMode==='videos')recommended='video';
    return res.status(200).json({visual_query:primary,visual_query_backup:backup,recommended_media:recommended});
  }catch(error){console.error('horror-scene-query',error);return res.status(200).json({...safe,recommended_media:mediaMode==='videos'?'video':'image'})}
};
