#!/usr/bin/env python3
import os


def install(natural_voice):
    def voice_settings():
        requested=os.getenv('INPUT_VOICE','')
        pitch_mode=os.getenv('INPUT_VOICE_PITCH','default')
        speed_mode=os.getenv('INPUT_VOICE_SPEED','default')
        if speed_mode not in {'default','fast','veryfast'}: speed_mode='default'
        if requested in {'gemini:AlgenibDeep','gemini:GacruxDeep'}: pitch_mode='low'
        pitch={'low':'-8Hz','default':'+0Hz','high':'+7Hz'}.get(pitch_mode,'+0Hz')
        edge_rate={'default':'-4%','fast':'+5%','veryfast':'+10%'}.get(speed_mode,'-4%')
        tempo={'default':0.96,'fast':1.05,'veryfast':1.10}.get(speed_mode,0.96)
        return pitch_mode,speed_mode,pitch,edge_rate,tempo
    natural_voice.voice_settings=voice_settings
    print('Velocidade de narração alinhada ao perfil natural.',flush=True)
