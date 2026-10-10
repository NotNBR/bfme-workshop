"""Edit native Eight Kingdoms battle and strategic footage with original music."""

from common.paths import ROOT
import json
import math
import re
from pathlib import Path
import subprocess

import tomllib
from video.encoding import encode as encode_video, validate as validate_video
import imageio_ffmpeg

PROJECT=ROOT/'examples/showcases/eight_kingdoms'
OUT=ROOT/'local/artifacts/eight-kingdoms/trailer'
CAPTURE=OUT
EXPORT=OUT
VALIDATION=OUT
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
FONT="C\\:/Windows/Fonts/timesbd.ttf"
SANS="C\\:/Windows/Fonts/arial.ttf"


from .score import score

def encode(args,log):
    encode_video(args, OUT/log)


def title(text,x,y,size=70,color='0xeee8d6',font=FONT):
    return f"drawtext=fontfile='{font}':text='{text}':x={x}:y={y}:fontsize={size}:fontcolor={color}"


def main():
    for directory in (OUT,EXPORT,VALIDATION): directory.mkdir(parents=True,exist_ok=True)
    profiles=tomllib.loads((PROJECT/'exports.toml').read_text())['profiles']
    settings=tomllib.loads((PROJECT/'project.toml').read_text())
    report=json.loads((VALIDATION/'battle-validation.json').read_text())
    if report['outcome']!='pass':raise RuntimeError('Only verified battle footage can be exported')
    raw=CAPTURE/'battle-footage.bgr0'
    if raw.exists():
        encode(['-f','rawvideo','-pixel_format','bgr0','-video_size','1600x720','-framerate','30','-i',str(raw),
            '-an','-c:v','libx264','-preset','fast','-crf',str(profiles['master']['crf']),'-pix_fmt','yuv420p',str(OUT/'battle-footage.mp4')],'footage-encode.log')
    elif CAPTURE!=OUT and not (OUT/'battle-footage.mp4').exists():
        import shutil
        shutil.copy2(CAPTURE/'battle-footage.mp4',OUT/'battle-footage.mp4')
    if (settings['fps'],settings['intro_seconds'],settings['outro_seconds'])!=(30,6,6):
        raise ValueError('This edit template requires 30 fps and six-second title cards')
    duration=settings['intro_seconds']+settings['outro_seconds']+report['movie']['frames']/settings['fps']
    expected_frames=report['movie']['frames']+12*settings['fps']
    score(duration, OUT)
    portrait=ROOT/settings['portrait']
    intro=("[1:v]scale=960:960,zoompan=z='1+on*0.00006':d=180:s=960x960:fps=30[map];"
        "[0:v][map]overlay=900:60,"+
        title('EIGHT',105,280,112)+','+title('KINGDOMS',100,400,112)+','+
        'drawbox=x=110:y=548:w=660:h=3:color=0xa99a70:t=fill,'+
        title('EIGHT PLAYERS. FOUR FRONTS.',112,590,27,font=SANS)+','+
        title('A KINGDOM WORTH FIGHTING FOR',112,652,30,color='0xcbbb93')+','+
        title('THE BATTLE FOR MIDDLE-EARTH II',112,906,22,color='0x9da9a7',font=SANS)+',fade=t=in:st=0:d=0.7[v]')
    encode(['-f','lavfi','-i','color=c=0x10191a:s=1920x1080:r=30:d=6','-loop','1','-i',str(portrait),
        '-filter_complex',intro,'-map','[v]','-t','6','-an','-c:v','libx264','-preset','fast','-crf',str(profiles['master']['crf']),'-pix_fmt','yuv420p',str(OUT/'intro.mp4')],'intro-encode.log')
    plan=json.loads((CAPTURE/'battle-plan.json').read_text())
    titles=json.loads((PROJECT/'titles.json').read_text())
    labels=[t['title'] for t in titles]
    chapters=[t['chapter'] for t in titles]
    # The bottom 48 pixels can catch the native palantir's upper edge while
    # changing zoom. Keep that UI outside every cinematic shot.
    vf='crop=1600:672:0:0,eq=brightness=0.008:contrast=1.06:gamma=1.12:saturation=1.07,scale=1920:806:flags=lanczos,unsharp=3:3:0.25:3:3:0,pad=1920:1080:0:137:color=0x080c0d'
    shots=json.loads((PROJECT/settings['shots']).read_text())
    if len(shots)!=len(labels): raise ValueError('Each shot needs one title entry')
    elapsed=0.
    for i,label in enumerate(labels):
        shot_seconds=shots[i]['frames']/settings['fps']
        start=elapsed+.35;end=elapsed+shot_seconds-.5
        elapsed+=shot_seconds
        opacity=f":alpha='min(1,max(0,(t-{start})/.4))*min(1,max(0,({end}-t)/.5))'"
        vf+=','+title(chapters[i],80,966,20,color='0x99aaa8',font=SANS)+opacity
        vf+=','+title(label,78,999,38,color='0xe9ddbe')+opacity
    vf+=','+title('EIGHT KINGDOMS',80,51,30,color='0xd6c7a0')
    vf+=','+title('4 VS 4  /  A MIDGAME BATTLE','w-text_w-80',57,22,color='0x99aaa8',font=SANS)
    encode(['-i',str(OUT/'battle-footage.mp4'),'-vf',vf,'-an','-c:v','libx264','-preset','fast','-crf',str(profiles['master']['crf']),'-pix_fmt','yuv420p',str(OUT/'battle-edit.mp4')],'battle-edit.log')
    outro=title('EIGHT KINGDOMS','(w-text_w)/2',325,108)+',drawbox=x=650:y=476:w=620:h=2:color=0xa99a70:t=fill,'+title('96 BATTALIONS. 32 HEAVY UNITS.','(w-text_w)/2',525,28,font=SANS)+','+title('ONE BATTLEFIELD. YOUR WAR.','(w-text_w)/2',597,34,color='0xcbbb93')+','+title('AN EIGHT-PLAYER MAP FOR THE BATTLE FOR MIDDLE-EARTH II','(w-text_w)/2',870,20,color='0x99aaa8',font=SANS)+',fade=t=in:st=0:d=0.5,fade=t=out:st=4.8:d=1.2'
    encode(['-f','lavfi','-i','color=c=0x10191a:s=1920x1080:r=30:d=6','-vf',outro,'-an','-c:v','libx264','-preset','fast','-crf',str(profiles['master']['crf']),'-pix_fmt','yuv420p',str(OUT/'outro.mp4')],'outro-encode.log')
    concat=OUT/'edit-list.txt';concat.write_text("file 'intro.mp4'\nfile 'battle-edit.mp4'\nfile 'outro.mp4'\n")
    encode(['-f','concat','-safe','0','-i',str(concat),'-i',str(OUT/'original-score.wav'),'-map','0:v','-map','1:a',
        '-c:v','copy','-af','loudnorm=I=-18:TP=-2:LRA=9','-c:a','aac','-b:a',str(profiles['master']['audio_kbps'])+'k','-ar','48000','-t',str(duration),'-movflags','+faststart',str(EXPORT/'Eight-Kingdoms-Trailer.mp4')],'trailer-encode.log')
    encode(['-i',str(EXPORT/'Eight-Kingdoms-Trailer.mp4'),'-vf',f"scale={profiles['mobile']['width']}:{profiles['mobile']['height']}:flags=lanczos",
        '-c:v','libx264','-preset','slow','-profile:v','main','-level','3.1',
        '-b:v',str(profiles['mobile']['video_kbps'])+'k','-maxrate','1100k','-bufsize','2200k','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a',str(profiles['mobile']['audio_kbps'])+'k','-ac','2','-movflags','+faststart',str(EXPORT/'Eight-Kingdoms-Mobile.mp4')],'mobile-encode.log')
    for second in [2,9,17,25,33,41,49,57,65,72]:
        encode(['-ss',str(second),'-i',str(EXPORT/'Eight-Kingdoms-Trailer.mp4'),'-frames:v','1',str(OUT/f'frame-{second:02}.jpg')],f'frame-{second:02}.log')
    (EXPORT/'trailer.json').write_text(json.dumps(dict(title='Eight Kingdoms',duration_seconds=duration,width=1920,height=1080,fps=30,
        map_sha256=report['map_sha256'],gameplay='64 seconds of native render-target footage',audio='Original synthesized instrumental score; no game audio capture',
        battle=report['battle'],teams='4 vs 4',staged=True,revision=4,
        field_battle_seconds=16,base_battle_seconds=16,strategic_and_zoom_seconds=32,fronts=plan['front_names']),indent=2)+'\n')
    exports=[]
    for name in ('Eight-Kingdoms-Trailer.mp4','Eight-Kingdoms-Mobile.mp4'):
        limit=profiles['mobile']['max_bytes'] if name.endswith('Mobile.mp4') else None
        exports.append(validate_video(EXPORT/name,expected_frames=expected_frames,expected_duration=duration,max_bytes=limit))
    audio_check=subprocess.run([FFMPEG,'-hide_banner','-i',str(EXPORT/'Eight-Kingdoms-Trailer.mp4'),
        '-af','loudnorm=I=-18:TP=-2:LRA=9:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    audio=json.loads(re.findall(r'\{[^{}]+\}',audio_check.stderr)[-1])
    if float(audio['input_tp'])>-.8 or not -20<float(audio['input_i'])<-16:raise RuntimeError('Audio master outside target')
    (VALIDATION/'export-validation.json').write_text(json.dumps(dict(outcome='pass',revision=4,exports=exports,audio=audio),indent=2)+'\n')
    print(EXPORT/'Eight-Kingdoms-Trailer.mp4')


if __name__=='__main__':main()
