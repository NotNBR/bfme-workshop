"""Export the continuous gameplay capture without added text."""
from pathlib import Path
import subprocess
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/showcase'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    with (OUT/'encode.log').open('w') as log:
        subprocess.run([ffmpeg,'-y','-hide_banner','-i','gameplay-raw.mp4',
                        '-vf','fps=30,fade=t=in:st=0:d=0.4,fade=t=out:st=28.4:d=0.6',
                        '-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p',
                        '-t','29','-an','-movflags','+faststart','bfmeXbar-gameplay-showcase.mp4'],cwd=OUT,stdout=log,stderr=log,check=True)
    for second in [2,5,7,12,17,21,26,28]:
        subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-ss',str(second),
                        '-i',str(OUT/'bfmeXbar-gameplay-showcase.mp4'),'-frames:v','1',
                        str(OUT/f'frame-{second:02}.png')],check=True)
    print(OUT/'bfmeXbar-gameplay-showcase.mp4')

if __name__=='__main__':main()
