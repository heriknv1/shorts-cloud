#!/usr/bin/env python3
from pathlib import Path
p=Path('scripts/generate_turbo.py');s=p.read_text(encoding='utf-8');changes=[]
def replace_once(old,new,label):
 global s
 if new in s:return
 if old not in s:raise SystemExit(f'Não consegui aplicar política obrigatória: {label}')
 s=s.replace(old,new,1);changes.append(label)
replace_once("pitch={'low':'-18Hz','default':'+0Hz','high':'+18Hz'}.get(pitch_mode,'+0Hz')","pitch={'low':'-8Hz','default':'+0Hz','high':'+8Hz'}.get(pitch_mode,'+0Hz')",'tom de voz natural')
replace_once("rate={'slow':'-14%','default':'-5%','fast':'+10%'}.get(speed_mode,'-5%')","rate={'slow':'-9%','default':'+0%','fast':'+7%'}.get(speed_mode,'+0%')",'ritmo de voz natural')
marker="def synthesize(text,idx):\n"
helper="""def naturalize_speech_text(text):
    text=str(text or '').strip()
    text=text.replace('—', ', ').replace('–', ', ').replace(';', '. ')
    text=' '.join(text.split())
    if text and text[-1] not in '.!?': text+='.'
    return text

def synthesize(text,idx):
"""
replace_once(marker,helper,'preparação natural da fala')
old="wav=WORK/f'voice_{idx:02d}.wav'; raw=WORK/f'voice_raw_{idx:02d}.wav'; mp3=WORK/f'voice_{idx:02d}.mp3'; voice=os.getenv('INPUT_VOICE','pt-BR-AntonioNeural'); _,_,pitch,rate=voice_settings()"
new="wav=WORK/f'voice_{idx:02d}.wav'; raw=WORK/f'voice_raw_{idx:02d}.wav'; mp3=WORK/f'voice_{idx:02d}.mp3'; voice=os.getenv('INPUT_VOICE','pt-BR-FranciscaNeural'); _,_,pitch,rate=voice_settings(); spoken=naturalize_speech_text(text)"
replace_once(old,new,'voz neural padrão')
replace_once("'--text',text,'--write-media'","'--text',spoken,'--write-media'",'fala neural tratada')
replace_once("run(['piper','--model',PIPER_MODEL,'--output_file',str(raw)],stdin=text.encode('utf-8'))","run(['piper','--model',PIPER_MODEL,'--output_file',str(raw)],stdin=spoken.encode('utf-8'))",'fala alternativa tratada')
oldrx="CATHOLIC_RX=re.compile(r'\\b(catholic|católico|católica|catolicismo|cathedral|catedral|pope|papa|papal|rosary|terço|crucifix|crucifixo|statue|estátua|saint|santo|santa|virgin mary|virgem maria|madonna|marian|mariana|mass|missa|monstrance|ostensório|religious icon|ícone religioso|altar|basilica|basílica|chapel|capela|nun|freira|priest|padre)\\b',re.I)"
newrx="CATHOLIC_RX=re.compile(r'\\b(catholic|católico|católica|catolicismo|cathedral|catedral|pope|papa|papal|rosary|terço|crucifix|crucifixo|statue|estátua|saint|santo|santa|virgin mary|virgem maria|madonna|marian|mariana|mass|missa|monstrance|ostensório|religious icon|ícone religioso|altar|basilica|basílica|chapel|capela|nun|freira|priest|padre|islam|islã|islão|islamic|islâmico|islâmica|muslim|muçulmano|muçulmana|mosque|mesquita|quran|corão|koran|mecca|meca|medina|ramadan|minaret|minarete|imam|candomblé|candomble|umbanda|orixá|orixa|orisha|terreiro|pombagira|pomba gira|iemanjá|iemanja|ogum|oxum|oxóssi|oxossi|xangô|xango|iansã|iansa|obaluaiê|obaluae)\\b',re.I)"
replace_once(oldrx,newrx,'bloqueio religioso ampliado')
required=['def make_ass(','PlayResX: 1080','margin_v=140','def safe_scene_queries(','pt-BR-FranciscaNeural',"'default':'+0%'",'candomblé','mesquita']
missing=[x for x in required if x not in s]
if missing:raise SystemExit('Políticas obrigatórias ausentes: '+', '.join(missing))
p.write_text(s,encoding='utf-8');print('Políticas de renderização e voz aplicadas com sucesso: '+(', '.join(changes) if changes else 'já presentes'))
