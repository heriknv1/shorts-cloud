const { requireAuth } = require('../lib/auth');

function extractJson(text){
  const raw=String(text||'').replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/i,'');
  const m=raw.match(/\{[\s\S]*\}/);
  if(!m)throw Error('Não foi possível criar um roteiro válido.');
  return JSON.parse(m[0]);
}
function compact(v,max=16){return String(v||'').trim().replace(/\s+/g,' ').split(' ').filter(Boolean).slice(0,max).join(' ')}

module.exports=async function handler(req,res){
  if(req.method!=='POST')return res.status(405).json({error:'Use POST.'});
  if(!requireAuth(req,res))return;
  try{
    const key=process.env.GROQ_API_KEY;
    if(!key)return res.status(500).json({error:'Serviço de criação indisponível.'});
    const topic=String(req.body?.topic||'').trim();
    const duration=Math.min(70,Math.max(60,Number(req.body?.duration||65)));
    const tone=String(req.body?.tone||'dramatic');
    const visualStyle=req.body?.visualStyle==='cartoon'?'cartoon':'realistic';
    const mediaMode=['photos','videos','hybrid'].includes(req.body?.mediaMode)?req.body.mediaMode:'hybrid';
    const sceneCount=duration<=60?8:duration>=70?10:9;
    const targetWords=Math.round(duration*2.12);
    const subject=topic||'Crie uma história original de terror e suspense psicológico, com situação concreta, tensão crescente e final marcante.';
    const prompt=`Crie roteiro e storyboard para UM Short vertical de terror e suspense em português do Brasil.\nASSUNTO: ${subject}\nDURAÇÃO: ${duration}s | TOM: ${tone} | VISUAL: ${visualStyle} | MÍDIA: ${mediaMode}\n\nNARRAÇÃO:\n- Cerca de ${targetWords} palavras em ${sceneCount} cenas.\n- Comece com um gancho inquietante nos primeiros segundos.\n- Construa tensão progressiva, pistas visuais, falsa sensação de segurança, clímax e fechamento forte.\n- Português brasileiro natural para narração, com frases curtas e pausas que ajudem o suspense.\n- Evite clichês vazios e repetições de “de repente”, “algo estava errado” e equivalentes.\n- O medo deve vir principalmente de atmosfera, antecipação, comportamento estranho, isolamento, som sugerido, espaço e descoberta.\n- Pode haver ficção sobrenatural ou terror psicológico conforme o tema, mas não dependa de violência gráfica.\n\nDIREÇÃO VISUAL PROFISSIONAL:\n- visual_context deve ser EM INGLÊS e definir continuidade: local, horário, clima, paleta fria ou dessaturada, baixa iluminação, fontes de luz práticas, textura cinematográfica, personagens recorrentes e linguagem de câmera.\n- Cada visual_description deve mostrar uma ação concreta e específica da cena.\n- Use composição de suspense: negative space, deep shadows, practical light, reflections, silhouettes, partially obscured spaces, long corridors, doorways, subtle background detail, restrained camera angles.\n- Evite sangue, gore, mutilação ou choque gráfico como preenchimento.\n- Cada visual_query e visual_query_backup deve estar EM INGLÊS, positiva, específica e entre 8 e 16 palavras.\n- Não repita o mesmo local, enquadramento ou objeto sem motivo narrativo.\n- Preserve continuidade de roupas, idade aproximada, ambiente e objetos recorrentes.\n- Em hybrid prefira image para cenas únicas ou sobrenaturais que precisam ser criadas com precisão; use video quando movimento real genérico melhorar a tensão.\n- Em photos use sempre image; em videos use sempre video.\n\nRetorne SOMENTE JSON válido com: title, summary, description, hashtags, niche_key, visual_context e scenes. Cada scene: beat, narration, visual_description, visual_query, visual_query_backup, recommended_media.`;
    const response=await fetch('https://api.groq.com/openai/v1/chat/completions',{method:'POST',headers:{Authorization:`Bearer ${key}`,'Content-Type':'application/json'},body:JSON.stringify({model:process.env.GROQ_MODEL||'qwen/qwen3.8-27b',temperature:.52,max_completion_tokens:3000,response_format:{type:'json_object'},messages:[{role:'user',content:prompt}]})});
    const data=await response.json();
    if(response.status===429)return res.status(429).json({error:'Muita atividade no momento. Tente novamente em alguns instantes.',retryAfterSeconds:5});
    if(!response.ok)throw Error('Falha temporária');
    const plan=extractJson(data.choices?.[0]?.message?.content||'');
    if(!Array.isArray(plan.scenes)||plan.scenes.length<6)throw Error('Poucas cenas');
    plan.niche_key='horror';
    plan.visual_context=String(plan.visual_context||'psychological horror, cinematic low key lighting, deep shadows, restrained color palette, consistent characters and location').slice(0,900);
    const seen=new Set();
    plan.scenes=plan.scenes.slice(0,10).map((s,i)=>{
      const narration=String(s.narration||'').trim();
      const desc=String(s.visual_description||'').trim().slice(0,900);
      let primary=compact(s.visual_query||desc||narration,16);
      let backup=compact(s.visual_query_backup||primary,16);
      const anchor='psychological horror suspense cinematic low key lighting non graphic';
      primary=`${primary} ${anchor}`.replace(/\s+/g,' ').slice(0,210);
      backup=`${backup} alternate angle ${anchor}`.replace(/\s+/g,' ').slice(0,210);
      if(seen.has(primary.toLowerCase()))primary=`${compact(desc,12)} suspense scene ${i+1} ${anchor}`.slice(0,210);
      seen.add(primary.toLowerCase());
      let recommended=s.recommended_media==='video'?'video':'image';
      if(mediaMode==='photos')recommended='image';
      if(mediaMode==='videos')recommended='video';
      return{beat:String(s.beat||`Cena ${i+1}`).slice(0,100),narration,visual_description:desc,visual_query:primary,visual_query_backup:backup,recommended_media:recommended};
    });
    if(plan.scenes.some(s=>!s.narration))throw Error('Cena sem narração');
    return res.status(200).json({plan,preset:'Terror e Suspense'});
  }catch(error){
    console.error('horror-plan',error);
    return res.status(500).json({error:'Não foi possível criar a história agora. Tente novamente em alguns instantes.'});
  }
};