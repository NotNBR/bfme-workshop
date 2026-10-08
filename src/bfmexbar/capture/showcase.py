"""Record only the BFME2 client with FFmpeg; native opt-in camera direction."""

from bfmexbar.paths import ROOT
import json
from pathlib import Path
import struct
import subprocess

OUT=ROOT/'artifacts/showcase'


def observe(game,smoke):
    address=game.res.get('showcase_address')
    if not address:return
    enabled,seconds,finished=struct.unpack('<IfI',game.read(address,12))
    if not enabled or seconds<=0:return
    if not hasattr(game,'showcase_recorder'):
        import imageio_ffmpeg
        windows=[w for w in smoke.boot_smoke.windows_of(game.pid) if w[1][2]-w[1][0]>100]
        if not windows:return
        window=max(windows,key=lambda w:(w[1][2]-w[1][0])*(w[1][3]-w[1][1]))
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'timeline.jsonl').write_text('')
        # The verified process window handle keeps the recording confined to the game.
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner',
                 '-f','gdigrab','-framerate','30','-draw_mouse','0','-i',f'hwnd={window[2]}',
                 '-t','29','-an','-c:v','libx264','-preset','veryfast','-crf','20',
                 '-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'gameplay-raw.mp4')]
        game.showcase_log=(OUT/'recording.log').open('w')
        game.showcase_recorder=subprocess.Popen(command,stdout=game.showcase_log,stderr=subprocess.STDOUT,
                                                creationflags=subprocess.CREATE_NO_WINDOW)
        game.res['showcase']={'video':str(OUT/'gameplay-raw.mp4'),'camera_start_seconds':seconds,
                              'recorder_pid':game.showcase_recorder.pid}
    result=game.showcase_recorder.poll()
    if result is not None and not game.showcase_log.closed:game.showcase_log.close()
    state={**game.res['showcase'],'seconds':seconds,'finished':bool(finished),'recording_exit':result}
    if not game.res.get('showcase_timeline_done'):
        view=game.u32(game.base+0x9FEA3C)
        state['angle']=struct.unpack('<f',game.read(view+0x28,4))[0]
        state['camera']=game.res.get('strategic',{})
        with (OUT/'timeline.jsonl').open('a') as stream:stream.write(json.dumps(state)+'\n')
        if finished:game.res['showcase_timeline_done']=True
    (OUT/'recording.json').write_text(json.dumps(state,indent=2)+'\n')
    if result is not None and result!=0:raise RuntimeError('Showcase recorder failed; see artifacts/showcase/recording.log')
