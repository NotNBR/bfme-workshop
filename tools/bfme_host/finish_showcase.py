"""Add concise feature captions to the real, unsped-up gameplay capture."""
from pathlib import Path
import subprocess
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/showcase'
CAPTIONS=[
    (0,7,'bfmeXbar','Battle for Middle-earth II at strategic scale'),
    (7,20,'FROM THE BATTLEFIELD...','Native animation, formations and combat'),
    (20,32,'...TO STRATEGIC VIEW','Smooth tilt and orthographic projection'),
    (32,42,'THE WHOLE BATTLEFIELD','Extended zoom | Both bases | Marching reinforcements'),
    (42,57,'READ THE BATTLE AT A GLANCE','Unit roles | One building symbol | Larger hero stars'),
    (57,66,'BACK INTO THE FIGHT','One continuous match. Original BFME2 simulation.'),
    (66,72,'bfmeXbar','Native BFME2 host | Strategic camera extension'),
]


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    def timestamp(seconds):return f'0:{int(seconds)//60:02}:{int(seconds)%60:02}.00'
    ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1440\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Title,Segoe UI,38,&H00D8E8F1,&H00FFFFFF,&H700B1018,&H700B1018,-1,0,0,0,100,100,1,0,3,12,0,7,44,44,34,1\nStyle: Detail,Segoe UI,26,&H00FFFFFF,&H00FFFFFF,&H700B1018,&H700B1018,0,0,0,0,100,100,0,0,3,10,0,7,44,44,91,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    for start,end,title,detail in CAPTIONS:
        for style,text in [('Title',title),('Detail',detail)]:
            ass+=f'Dialogue: 0,{timestamp(start)},{timestamp(end)},{style},,0,0,0,,{{\\fad(350,350)}}{text}\n'
    (OUT/'captions.ass').write_text(ass,encoding='utf-8')
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    with (OUT/'encode.log').open('w') as log:
        subprocess.run([ffmpeg,'-y','-hide_banner','-i','gameplay-raw.mp4',
                        '-vf','ass=captions.ass,fade=t=in:st=0:d=0.6,fade=t=out:st=71:d=1',
                        '-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p',
                        '-an','-movflags','+faststart','bfmeXbar-gameplay-showcase.mp4'],cwd=OUT,stdout=log,stderr=log,check=True)
    for second in [3,14,24,37,48,62]:
        subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-ss',str(second),
                        '-i',str(OUT/'bfmeXbar-gameplay-showcase.mp4'),'-frames:v','1',
                        str(OUT/f'frame-{second:02}.png')],check=True)
    print(OUT/'bfmeXbar-gameplay-showcase.mp4')

if __name__=='__main__':main()
