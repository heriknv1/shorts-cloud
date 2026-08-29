#!/usr/bin/env python3
from pathlib import Path
import re

path=Path('scripts/generate_turbo.py')
s=path.read_text(encoding='utf-8')

if 'import textwrap' not in s:
    s=s.replace('import json, math, os, subprocess, hashlib, re','import json, math, os, subprocess, hashlib, re, textwrap')

old="""def clean_query(q):
    q=re.sub(r'\\b(illustration|cartoon|drawing|animated|animation)\\b',' ',str(q),flags=re.I)
    return ' '.join(q.split())[:220]
"""
new="""RELIGIOUS_RX=re.compile(r'\\b(jesus|christ|cristo|messiah|messias|bible|biblical|bíblia|bíblico|god|deus|gospel|evangelho|baptism|batismo|prayer|oração|church|igreja|apostle|apóstolo|disciple|discípulo)\\b',re.I)
CATHOLIC_RX=re.compile(r'\\b(catholic|cathedral|pope|papal|rosary|terço|crucifix|crucifixo|statue|estátua|saint|santo|santa|virgin mary|virgem maria|madonna|marian|mariana|mass|missa|monstrance|ostensório|religious icon|ícone religioso|altar candles)\\b',re.I)
JESUS_RX=re.compile(r'\\b(jesus|jesus christ|christ|cristo|jesus cristo|messiah|messias)\\b',re.I)

def clean_query(q):
    q=re.sub(r'\\b(illustration|cartoon|drawing|animated|animation)\\b',' ',str(q),flags=re.I)
    if RELIGIOUS_RX.search(q):
        q=CATHOLIC_RX.sub(' ',q)
        if JESUS_RX.search(q):
            q=JESUS_RX.sub(' ',q)+' ancient Galilee biblical setting disciples crowd landscape symbolic scene no identifiable central Jesus figure'
        q+=' evangelical protestant biblical context scripture centered no catholic icons no rosary no statues no crucifix no saint imagery no Marian imagery'
    return ' '.join(q.split())[:300]
"""
if old in s: s=s.replace(old,new)

needle="""def ai_image(scene,path,style,niche,idx,realistic=False):
    desc=str(scene.get('visual_description') or scene.get('visual_query') or 'cinematic scene')
"""
replacement="""def ai_image(scene,path,style,niche,idx,realistic=False):
    desc=str(scene.get('visual_description') or scene.get('visual_query') or 'cinematic scene')
    religious=bool(RELIGIOUS_RX.search(desc+' '+str(scene.get('narration','')))) or niche in {'biblical','devotional'}
    if religious:
        desc=CATHOLIC_RX.sub(' ',desc)
        if realistic and JESUS_RX.search(desc+' '+str(scene.get('narration',''))):
            desc=JESUS_RX.sub(' ',desc)+' ancient biblical environment, disciples and crowd, symbolic environmental composition, no identifiable or photorealistic Jesus figure'
"""
if needle in s: s=s.replace(needle,replacement)

s=s.replace("if niche in {'biblical','devotional'}: style_text+=', ancient biblical Middle East when historical, authentic tunics and sandals, no modern objects, no medieval European armor'",
"if religious: style_text+=', evangelical Protestant biblical visual language, scripture-centered, ancient biblical Middle East when historical, authentic tunics and sandals, no modern objects, no medieval European armor, no Catholic iconography, no rosary, no statues, no crucifix, no saints, no Marian imagery, no ornate cathedral altar'")

start=s.find('def make_srt(scenes,durations,path):')
end=s.find('\ndef music_track(',start)
if start!=-1 and end!=-1:
    dynamic="""def make_srt(scenes,durations,path):
    font_size=max(36,min(92,int(os.getenv('INPUT_CAPTION_SIZE','56'))))
    per=6 if font_size<=44 else 5 if font_size<=58 else 4 if font_size<=72 else 3
    width=30 if font_size<=44 else 25 if font_size<=58 else 21 if font_size<=72 else 17
    lines=[]; offset=0.; n=1
    for scene,dur in zip(scenes,durations):
        words=str(scene.get('narration','')).split(); chunks=[words[i:i+per] for i in range(0,len(words),per)] or [['']]; cursor=offset
        for ch in chunks:
            part=dur/max(1,len(chunks)); end=min(offset+dur,cursor+part)
            wrapped=textwrap.wrap(' '.join(ch),width=width,break_long_words=False,break_on_hyphens=False)
            caption='\\n'.join(wrapped[:2])
            lines += [str(n),f'{ts(cursor)} --> {ts(end)}',caption,'']; n+=1; cursor=end
        offset+=dur
    path.write_text('\\n'.join(lines),encoding='utf-8')
"""
    s=s[:start]+dynamic+s[end:]

s=s.replace("font_size=max(24,min(64,font_size))","font_size=max(36,min(92,font_size))")
s=s.replace("Alignment=2,MarginV=55,Bold=1","Alignment=2,MarginL=82,MarginR=82,MarginV=92,Bold=1")

path.write_text(s,encoding='utf-8')
print('render policies applied')
