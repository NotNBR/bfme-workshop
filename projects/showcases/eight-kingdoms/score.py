"""Original instrumental score for the Eight Kingdoms camera sequence."""
from pathlib import Path
import math
import wave
import numpy as np

def score(duration, output):
    """Original D-minor score, with phrase changes aligned to the eight shots."""
    rate=48000;mix=np.zeros((round(rate*duration),2),dtype=np.float64)
    rng=np.random.default_rng(82165);beat=2/3
    def add(start,note,length,gain,pan=0.,style='strings'):
        count=int(length*rate);t=np.arange(count)/rate;hz=440*2**((note-69)/12)
        if style=='strings':
            phase=2*np.pi*hz*t+.035*np.sin(2*np.pi*4.6*t)
            sig=sum(np.sin(phase*h+d*t)/(h*h**.4)
                    for h,d in [(1,-.9),(1,.9),(2,.7),(3,-.8),(4,.3)])*.35
            env=np.minimum(t/.26,1)*np.minimum((length-t)/.6,1)
        elif style=='bell':
            sig=np.sin(2*np.pi*hz*t)+.3*np.sin(2*np.pi*hz*2.01*t)
            env=np.minimum(t/.008,1)*np.exp(-t*2.4)
        elif style=='drum':
            sig=np.sin(2*np.pi*(62*t+52*.045*(1-np.exp(-t/.045))))
            sig+=.3*np.sin(2*np.pi*126*t)*np.exp(-t*12)
            sig+=.16*rng.normal(0,1,count)*np.exp(-t*27)
            env=np.minimum(t/.003,1)*np.exp(-t*5.5)
        else:
            noise=rng.normal(0,1,count)
            sig=noise-np.convolve(noise,np.ones(7)/7,mode='same')
            env=np.minimum(t/.008,1)*np.exp(-t*3)
        sig*=env*gain;offset=int(start*rate);end=min(len(mix),offset+count)
        if end<=offset:return
        sig=sig[:end-offset]
        mix[offset:end,0]+=sig*math.sqrt((1-pan)/2);mix[offset:end,1]+=sig*math.sqrt((1+pan)/2)
    chords=[(50,57,62,65),(46,53,58,62),(48,55,60,64),(45,52,57,61)]
    for start in (0,3):
        for i,note in enumerate(chords[0]):add(start,note,3.7,.075,(i-1.5)/2)
    melody=[74,72,69,65,67,69,72,69]
    for shot in range(8):
        scene=6+shot*8
        intensity=.08 if shot in (0,4,7) else .115
        for bar in range(3):
            start=scene+bar*4*beat;chord=chords[(shot*3+bar)%4]
            for i,note in enumerate(chord):add(start,note,3.1,intensity,(i-1.5)/2)
            add(start,chord[0]-12,3.0,.12)
            for n in range(4):
                add(start+n*beat,36,.8,(.3 if n%2==0 else .14)*(1 if shot not in (0,7) else .65),style='drum')
                if shot in (2,3,5,6):add(start+n*beat,chord[n]+12,1.25,.045,(-1 if n%2 else 1)*.45,'bell')
        for n in range(4):add(scene+n*2,melody[(shot+n)%8],2.5,.055,.25,'strings')
        add(scene,36,1.5,.07,-.2,'cymbal')
    for i,note in enumerate(chords[0]):add(duration-6,note,6,.085,(i-1.5)/2)
    # A quiet stereo tail gives the generated instruments a shared room.
    dry=mix.copy()
    for delay,gain in ((.113,.12),(.229,.08),(.367,.055)):
        offset=int(delay*rate);mix[offset:]+=dry[:-offset,::-1]*gain
    envelope=np.minimum(np.arange(len(mix))/rate/2,1)*np.minimum((duration-np.arange(len(mix))/rate)/3,1)
    mix=np.tanh(mix*1.2)*envelope[:,None];mix*=.83/max(float(np.abs(mix).max()),.001)
    with wave.open(str(Path(output)/'original-score.wav'),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate);w.writeframes((mix*32767).astype('<i2').tobytes())
