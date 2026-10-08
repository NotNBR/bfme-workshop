"""Contact sheet of installed native terrain assets (read-only BIG access)."""
from pathlib import Path
import io
import re
from PIL import Image, ImageDraw
from tools.import_bfme import BigArchive

ROOT=Path(__file__).resolve().parents[2]


def main():
    text=(ROOT/'runtime/bfme-host/mod/data/ini/terrain.ini').read_text()
    textures=dict(re.findall(r'Terrain\s+(\w+)\s*\n\s*Texture\s*=\s*(\S+)',text,re.I))
    names=['DirtMordor'+str(i).zfill(2) for i in range(1,19)]
    names+=['RockMordor'+str(i).zfill(2) for i in range(1,10)]
    names+=['CliffMordor01','CliffMordor02','CliffMordor05','MorDirt01','GrassMordor01','ConcOsgiliath09']
    archives=[BigArchive(p) for p in (ROOT/'runtime/bfme-host/game').glob('*.big') if p.stem.lower().startswith(('terrain','texture'))]
    index={key.split('/')[-1]:(a,key) for a in archives for key in a.entries}
    im=Image.new('RGB',(7*160,5*184),(25,25,25));d=ImageDraw.Draw(im)
    for i,name in enumerate(names):
        tex=textures[name].lower();entry=index.get(tex) or index.get(tex.replace('.tga','.dds'))
        if not entry:raise ValueError('Missing '+tex)
        a,key=entry;img=Image.open(io.BytesIO(a.read_bytes(key))).convert('RGB');img.thumbnail((152,152))
        im.paste(img,((i%7)*160,(i//7)*184));d.text(((i%7)*160+2,(i//7)*184+155),name,fill='white')
    out=ROOT/'artifacts/ashen-march/texture-study.jpg';out.parent.mkdir(parents=True,exist_ok=True);im.save(out)


if __name__=='__main__':main()
