const { requirePin } = require('../lib/auth');

const BIBLICAL_STORY_POOL = [
  'A criação e a queda em Gênesis 1–3', 'Noé e o dilúvio em Gênesis 6–9', 'A chamada de Abraão em Gênesis 12',
  'Abraão e Isaque no monte Moriá em Gênesis 22', 'Jacó luta com Deus em Gênesis 32', 'José é vendido pelos irmãos e chega ao Egito em Gênesis 37–50',
  'Moisés e a sarça ardente em Êxodo 3', 'As dez pragas do Egito em Êxodo 7–12', 'A travessia do Mar Vermelho em Êxodo 14',
  'O maná no deserto em Êxodo 16', 'A queda das muralhas de Jericó em Josué 6', 'Gideão e os trezentos em Juízes 6–7',
  'Sansão e Dalila em Juízes 16', 'Rute e Boaz no livro de Rute', 'Ana ora por um filho em 1 Samuel 1',
  'Samuel ouve a voz de Deus em 1 Samuel 3', 'Davi e Golias em 1 Samuel 17', 'Davi poupa a vida de Saul em 1 Samuel 24',
  'Salomão pede sabedoria em 1 Reis 3', 'Elias no monte Carmelo em 1 Reis 18', 'Elias e a viúva de Sarepta em 1 Reis 17',
  'Naamã é curado da lepra em 2 Reis 5', 'Ezequias recebe mais anos de vida em 2 Reis 20', 'Ester intercede por seu povo no livro de Ester',
  'Jó permanece fiel em meio ao sofrimento no livro de Jó', 'Jonas e a cidade de Nínive no livro de Jonas', 'Daniel na cova dos leões em Daniel 6',
  'Sadraque, Mesaque e Abede-Nego na fornalha em Daniel 3', 'Neemias reconstrói os muros de Jerusalém em Neemias', 'O nascimento de Jesus em Lucas 1–2',
  'Jesus acalma a tempestade em Marcos 4', 'A multiplicação dos pães e peixes em João 6', 'A mulher samaritana em João 4',
  'A cura do paralítico em Marcos 2', 'A ressurreição de Lázaro em João 11', 'Zaqueu encontra Jesus em Lucas 19',
  'O filho pródigo em Lucas 15', 'O bom samaritano em Lucas 10', 'Pedro anda sobre as águas em Mateus 14',
  'A conversão de Paulo em Atos 9', 'Paulo e Silas na prisão em Atos 16', 'O naufrágio de Paulo em Atos 27',
  'Pentecostes em Atos 2', 'Estêvão permanece fiel até o fim em Atos 6–7'
];

const DEVOTIONAL_POOL = [
  { ref: 'Salmo 23:1', theme: 'confiança no cuidado de Deus em tempos de incerteza' },
  { ref: 'Isaías 41:10', theme: 'coragem quando o medo tenta dominar' },
  { ref: 'Filipenses 4:6-7', theme: 'oração e paz em meio à ansiedade cotidiana' },
  { ref: 'Provérbios 3:5-6', theme: 'confiar em Deus mesmo quando não entendemos o caminho' },
  { ref: 'Romanos 8:28', theme: 'esperança de que Deus continua agindo mesmo em fases difíceis' },
  { ref: 'Mateus 11:28-30', theme: 'descanso em Cristo para quem está cansado e sobrecarregado' },
  { ref: 'Salmo 46:1', theme: 'Deus como refúgio e força em momentos de crise' },
  { ref: 'Lamentações 3:22-23', theme: 'recomeço, misericórdia e fidelidade de Deus a cada manhã' },
  { ref: 'Josué 1:9', theme: 'força e coragem para avançar diante de desafios' },
  { ref: '2 Coríntios 12:9', theme: 'a graça de Deus se manifesta em nossa fraqueza' },
  { ref: 'Salmo 37:5', theme: 'entregar planos e caminhos ao Senhor' },
  { ref: '1 Pedro 5:7', theme: 'lançar sobre Deus as preocupações do coração' },
  { ref: 'João 14:27', theme: 'a paz de Cristo em contraste com a inquietação do mundo' },
  { ref: 'Gálatas 6:9', theme: 'não desistir de fazer o bem quando os resultados demoram' },
  { ref: 'Hebreus 11:1', theme: 'fé como confiança no que ainda não vemos' },
  { ref: 'Salmo 121:1-2', theme: 'lembrar de onde vem o nosso socorro' },
  { ref: 'Tiago 1:5', theme: 'buscar sabedoria em Deus para decisões importantes' },
  { ref: 'Mateus 6:33', theme: 'priorizar o Reino de Deus em meio às pressões da vida' }
];

const PRESETS = {
  biblical: {
    label: 'Histórias bíblicas',
    subject: 'histórias bíblicas conhecidas e visualmente fortes, abrangendo Antigo e Novo Testamento, sem concentrar a seleção em Davi',
    context: 'Oriente Médio antigo em contexto bíblico, roupas de linho e lã, túnicas, mantos, sandálias, pastores, acampamentos, desertos, vales, armas e armaduras plausíveis da Idade do Ferro. Nunca use objetos modernos, roupas modernas, castelos medievais europeus ou armaduras de cavaleiro medieval.',
    queryAnchor: 'ancient biblical middle east historical illustration'
  },
  devotional: {
    label: 'Devocional bíblico',
    subject: 'devocionais bíblicos curtos e variados baseados em um texto bíblico específico, com reflexão prática e aplicação para o dia a dia',
    context: 'ilustração simbólica e respeitosa, ambiente coerente com o texto bíblico quando houver narrativa histórica e cenas contemporâneas simples apenas quando forem claramente aplicação prática. Não invente falas de Deus nem trate opinião como se fosse versículo.',
    queryAnchor: 'biblical devotional peaceful symbolic illustration'
  },
  cinematic: { label:'Histórias cinematográficas', subject:'histórias humanas curtas com conflito, virada e conclusão emocional', context:'cinematografia realista, iluminação dramática, personagens coerentes entre cenas, ambiente definido e continuidade visual.', queryAnchor:'cinematic dramatic storytelling' },
  mysteries: { label:'Mistérios e curiosidades', subject:'mistérios históricos, fenômenos curiosos ou perguntas intrigantes que possam ser explicadas sem inventar fatos', context:'ambiente misterioso, documental, objetos e locais relacionados ao caso, sombras e detalhes investigativos; evite imagens aleatórias apenas por serem escuras.', queryAnchor:'mystery documentary investigation cinematic' },
  ancient: { label:'História antiga', subject:'eventos, personagens e curiosidades de civilizações antigas', context:'reconstituição histórica da Antiguidade, arquitetura, vestimentas, armas e paisagens compatíveis com a civilização e período narrados. Proibido misturar elementos modernos ou medievais quando não pertencem ao período.', queryAnchor:'ancient civilization historical illustration archaeology' },
  motivation: { label:'Motivacional', subject:'histórias de superação, disciplina, foco e mudança de vida', context:'pessoas em situações de esforço, treino, estudo, trabalho e conquista; imagens devem acompanhar exatamente a ação narrada.', queryAnchor:'motivational human achievement cinematic illustration' },
  science: { label:'Ciência e espaço', subject:'curiosidades científicas e do universo explicadas de forma simples e correta', context:'laboratórios, fenômenos naturais, astronomia, espaço, planetas, telescópios e visual documental científico; não use ficção científica quando o assunto for ciência real.', queryAnchor:'science documentary space astronomy illustration' },
  'true-stories': { label:'Histórias reais surpreendentes', subject:'histórias reais bem documentadas que tenham começo, conflito e desfecho', context:'mini-documentário visual, época e local compatíveis com a história, objetos e ambientes específicos do caso; nunca invente imagens anacrônicas.', queryAnchor:'true story documentary historical illustration' },
  horror: { label:'Terror e suspense', subject:'contos de suspense originais ou lendas claramente apresentadas como lendas', context:'atmosfera noturna, ambientes vazios, tensão, silhuetas e detalhes inquietantes; mantenha continuidade de local e personagem em vez de imagens de terror aleatórias.', queryAnchor:'dark suspense eerie cinematic illustration' },
  'life-lessons': { label:'Reflexões e lições de vida', subject:'histórias curtas com escolhas, consequências e uma reflexão final', context:'cenas humanas íntimas, cotidiano, emoções legíveis e continuidade entre personagens e ambientes.', queryAnchor:'emotional human story cinematic illustration' },
  animals: { label:'Natureza e animais', subject:'comportamentos, curiosidades e estratégias de sobrevivência de animais', context:'animal correto, habitat natural correto e comportamento compatível com a narração; nunca trocar por outra espécie apenas por ser visualmente bonita.', queryAnchor:'wildlife nature documentary animal behavior illustration' }
};

const CARTOON_STYLES = {
  interdimensional: 'animação 2D sci-fi surreal, proporções caricatas, olhos expressivos, cores vibrantes e cenários alienígenas simples; identidade própria, sem copiar personagens ou cenários de obras existentes',
  'paper-cut': 'animação 2D de recortes, formas geométricas simples, silhuetas chapadas, movimento visual satírico e composição minimalista; identidade própria',
  'retro-surreal': 'animação 2D retro surreal, personagens simples, objetos cotidianos estranhos, paleta nostálgica e humor visual absurdo; identidade própria',
  'classic-2d': 'animação 2D clássica, contornos limpos, formas legíveis, cores equilibradas e enquadramentos de desenho animado tradicional',
  comic: 'ilustração de HQ cinematográfica, contornos fortes, sombras marcadas, composição dramática e cores intensas'
};

function extractJson(text){const raw=String(text||'').trim().replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/i,'');const match=raw.match(/\{[\s\S]*\}/);if(!match)throw new Error('A IA não retornou um plano JSON válido.');return JSON.parse(match[0]);}
function compactWords(value,max=10){return String(value||'').trim().split(/\s+/).filter(Boolean).slice(0,max).join(' ');}
function pickRandom(list){return list[Math.floor(Math.random()*list.length)];}

module.exports = async function handler(req,res){
  if(req.method!=='POST')return res.status(405).json({error:'Use POST.'});
  if(!requirePin(req,res))return;
  try{
    const key=process.env.GROQ_API_KEY;if(!key)return res.status(500).json({error:'Configure GROQ_API_KEY na Vercel.'});
    const presetKey=String(req.body?.presetKey||''),preset=PRESETS[presetKey]||null,topic=String(req.body?.topic||'').trim();
    if(!topic&&!preset)return res.status(400).json({error:'Informe o tema ou escolha um nicho pronto.'});
    const duration=Math.min(70,Math.max(60,Number(req.body?.duration||65))),tone=String(req.body?.tone||'cinematic');
    const visualStyle=['realistic','cartoon'].includes(req.body?.visualStyle)?req.body.visualStyle:'realistic';
    const cartoonStyle=CARTOON_STYLES[req.body?.cartoonStyle]?String(req.body.cartoonStyle):'classic-2d';
    let mediaMode=['photos','videos','hybrid'].includes(req.body?.mediaMode)?req.body.mediaMode:'photos';if(visualStyle==='cartoon')mediaMode='photos';
    const references=Array.isArray(req.body?.references)?req.body.references.slice(0,3):[],targetWords=Math.round(duration*2.30),sceneCount=duration<=60?8:duration>=70?10:9;
    const toneMap={cinematic:'cinematográfico, emocional e envolvente',documentary:'documental, claro e intrigante',dramatic:'dramático, tenso e misterioso',energetic:'rápido, energético e direto'};
    const nicheContext=preset?`${preset.label}. ${preset.context}`:'Siga rigorosamente a época, o lugar, os personagens, objetos e ambiente descritos no tema.';

    let subjectInstruction;
    if(topic){
      subjectInstruction=`TEMA DEFINIDO PELO USUÁRIO: ${topic}`;
    } else if(presetKey==='biblical'){
      const chosen=pickRandom(BIBLICAL_STORY_POOL);
      subjectInstruction=`TEMA BÍBLICO ALEATÓRIO DEFINIDO PELO SISTEMA: ${chosen}. Conte esta história específica. NÃO troque por Davi e Golias nem por outra história. Varie entre Antigo e Novo Testamento ao longo das gerações.`;
    } else if(presetKey==='devotional'){
      const chosen=pickRandom(DEVOTIONAL_POOL);
      subjectInstruction=`DEVOCIONAL ALEATÓRIO DEFINIDO PELO SISTEMA: base bíblica ${chosen.ref}; tema central: ${chosen.theme}. Produza um devocional curto com abertura que conecte com uma necessidade real, explicação fiel do texto em contexto, reflexão e aplicação prática. Não transforme em sermão longo e não invente citações bíblicas.`;
    } else {
      subjectInstruction=`ESCOLHA VOCÊ MESMO um tema específico e forte dentro de: ${preset.subject}. O título escolhido deve identificar claramente o assunto.`;
    }

    const visualInstruction=visualStyle==='cartoon'?`A saída será desenho. Estética desejada: ${CARTOON_STYLES[cartoonStyle]}. As descrições devem ser coerentes em época, roupa, cenário, ação e identidade visual.`:'A saída será fotográfica. Descreva cenas plausíveis e coerentes com a época, cenário, pessoas, ação e iluminação.';
    const mediaInstruction=mediaMode==='photos'?'Todas as cenas usarão imagens estáticas com movimento de câmera.':mediaMode==='videos'?'Todas as cenas buscarão clipes de vídeo.':'Escolha image ou video em recommended_media para cada cena.';
    const devotionalRules=presetKey==='devotional'?`\nREGRAS ESPECÍFICAS DO DEVOCIONAL:\n- Cite a referência bíblica escolhida de forma clara no roteiro.\n- Não invente o texto exato do versículo se não tiver certeza; prefira explicar/parafrasear com fidelidade.\n- Inclua uma aplicação prática simples e uma frase final de encorajamento.\n- O conteúdo deve permanecer cristão, bíblico e respeitoso, sem promessas de prosperidade garantida ou afirmações que o texto não sustenta.\n`:'';

    const prompt=`Você é diretor, roteirista e pesquisador visual de Shorts em português do Brasil. Planeje UM vídeo vertical coerente e publicável.\n\n${subjectInstruction}\nDURAÇÃO: ${duration}s\nTOM: ${toneMap[tone]||toneMap.cinematic}\nESTILO VISUAL: ${visualStyle}\nMÍDIA: ${mediaMode}\nNICHO/CONTEXTO OBRIGATÓRIO: ${nicheContext}\n${devotionalRules}\nREGRAS DE ROTEIRO:\n- Aproximadamente ${targetWords} palavras no total, distribuídas em ${sceneCount} cenas.\n- Gancho, contexto, progressão lógica, clímax e conclusão.\n- Não repita informações nem dê saltos incoerentes.\n- Para fatos religiosos/históricos/científicos, não invente detalhes específicos quando não tiver segurança.\n- Cada cena deve narrar somente o que o visual daquela cena consegue representar.\n\nREGRAS VISUAIS CRÍTICAS:\n- A imagem deve ser condizente com nicho, época, local e ação.\n- ${visualInstruction}\n- ${mediaInstruction}\n- visual_query e visual_query_backup devem estar EM INGLÊS e descrever concretamente a ilustração desejada.\n- Cada query deve incluir pistas de época/contexto quando isso for relevante.\n- Não use nomes próprios como única pista; descreva os elementos visuais.\n- Evite anacronismos.\n- visual_query_backup deve representar a mesma cena com termos alternativos.\n- visual_description deve explicar exatamente o que precisa aparecer.\n- Não coloque texto dentro da imagem.\n\nRetorne SOMENTE JSON válido:\n{\n  "title":"...",\n  "summary":"resumo de 1 a 2 frases",\n  "description":"descrição para postagem",\n  "hashtags":["#..."],\n  "niche_key":"${presetKey||'custom'}",\n  "visual_context":"resumo visual consistente",\n  "scenes":[{"beat":"nome curto da cena","narration":"fala natural desta cena","visual_description":"o que deve aparecer exatamente","visual_query":"english illustration description","visual_query_backup":"alternative english description for same scene","recommended_media":"image ou video","reference_index":0}]\n}`;

    const content=[{type:'text',text:prompt}];
    for(const ref of references){const dataUrl=String(ref?.dataUrl||'');if(/^data:image\/(jpeg|png|webp);base64,/i.test(dataUrl)&&dataUrl.length<1300000)content.push({type:'image_url',image_url:{url:dataUrl}});}
    const model=process.env.GROQ_MODEL||'qwen/qwen3.8-27b';
    const response=await fetch('https://api.groq.com/openai/v1/chat/completions',{method:'POST',headers:{Authorization:`Bearer ${key}`,'Content-Type':'application/json'},body:JSON.stringify({model,temperature:presetKey==='biblical'||presetKey==='devotional'?0.52:preset?0.46:0.43,max_completion_tokens:4600,response_format:{type:'json_object'},messages:[{role:'user',content}]})});
    const data=await response.json();if(!response.ok)throw new Error(data?.error?.message||`Groq HTTP ${response.status}`);
    const plan=extractJson(data.choices?.[0]?.message?.content||'');if(!Array.isArray(plan.scenes)||plan.scenes.length<6)throw new Error('A IA retornou poucas cenas.');
    const anchor=preset?.queryAnchor||'';plan.niche_key=presetKey||'custom';plan.visual_context=String(plan.visual_context||nicheContext).slice(0,700);
    plan.scenes=plan.scenes.slice(0,10).map((scene,i)=>{const primary=compactWords(scene.visual_query||'cinematic illustration',11),backup=compactWords(scene.visual_query_backup||scene.visual_query||'cinematic illustration',11);return{beat:String(scene.beat||`Cena ${i+1}`).slice(0,80),narration:String(scene.narration||'').trim(),visual_description:String(scene.visual_description||'').trim(),visual_query:`${anchor} ${primary}`.trim().slice(0,180),visual_query_backup:`${anchor} ${backup}`.trim().slice(0,180),recommended_media:scene.recommended_media==='video'?'video':'image',reference_index:Math.max(0,Math.min(3,Number(scene.reference_index||0)))}});
    if(visualStyle==='cartoon'||mediaMode==='photos')plan.scenes.forEach(s=>s.recommended_media='image');if(mediaMode==='videos')plan.scenes.forEach(s=>s.recommended_media='video');
    return res.status(200).json({plan,model,preset:preset?preset.label:null});
  }catch(error){console.error(error);return res.status(500).json({error:error.message||'Falha ao criar o plano.'});}
};
