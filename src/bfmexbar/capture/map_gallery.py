"""Photograph distinct places in the running isolated BFME2 game, then restore its camera."""

from bfmexbar.paths import ROOT
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import struct
import time

import pefile
from PIL import Image

OUT=ROOT/'artifacts/ithilien-frontier/gallery'
SHOTS=[('western-ruins',1450,4700,0,1200),
       ('northern-woodland',3500,6400,0,1500),
       ('southern-battle-plain',4100,1800,0,1700),
       ('eastern-escarpment',6900,5400,0,1700)]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pid',type=int,required=True)
    args=p.parse_args()
    k=C.WinDLL('kernel32',use_last_error=True);ps=C.WinDLL('psapi',use_last_error=True)
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
    k.WriteProcessMemory.argtypes=k.ReadProcessMemory.argtypes
    k.CloseHandle.argtypes=[W.HANDLE]
    ps.EnumProcessModulesEx.argtypes=[W.HANDLE,C.POINTER(W.HMODULE),W.DWORD,C.POINTER(W.DWORD),W.DWORD]
    ps.GetModuleFileNameExW.argtypes=[W.HANDLE,W.HMODULE,W.LPWSTR,W.DWORD]
    h=k.OpenProcess(0x438,False,args.pid)
    if not h:raise C.WinError(C.get_last_error())
    def read(addr,n):
        buf=C.create_string_buffer(n);done=C.c_size_t()
        if not k.ReadProcessMemory(h,addr,buf,n,C.byref(done)) or done.value!=n:raise C.WinError(C.get_last_error())
        return buf.raw
    def write(addr,data):
        done=C.c_size_t()
        if not k.WriteProcessMemory(h,addr,data,len(data),C.byref(done)) or done.value!=len(data):raise C.WinError(C.get_last_error())
    photo=None;saved=None;restore=None
    try:
        modules=(W.HMODULE*1024)();needed=W.DWORD()
        if not ps.EnumProcessModulesEx(h,modules,C.sizeof(modules),C.byref(needed),3):raise C.WinError(C.get_last_error())
        paths={}
        for mod in modules[:needed.value//C.sizeof(W.HMODULE)]:
            name=C.create_unicode_buffer(32768)
            if ps.GetModuleFileNameExW(h,mod,name,len(name)):paths[Path(name.value).resolve()]=mod
        expected=(ROOT/'runtime/bfme-host/game/game.dat').resolve()
        dll=(ROOT/'runtime/bfme-host/extension/bfmexbar-strategic.dll').resolve()
        if expected not in paths or dll not in paths:raise RuntimeError('Expected isolated BFME2 and project extension are not loaded')
        with pefile.PE(str(dll)) as pe:
            exports={e.name:paths[dll]+e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols}
        photo=exports[b'bfxPhoto'];capture=exports[b'bfxCapture'];state=exports[b'bfxState']
        saved=read(photo,36)
        if struct.unpack_from('<I',saved)[0]:raise RuntimeError('Another photo operation is active')
        if struct.unpack_from('<I',read(capture,24))[0]:raise RuntimeError('Another capture is active')
        view=struct.unpack('<I',read(paths[expected]+0x9FEA3C,4))[0]
        ox,oy,oz=struct.unpack('<3f',read(view+0xC,12))
        oh=struct.unpack('<f',read(view+0x40,4))[0]
        restore=struct.pack('<I8f',2,ox,oy,oz,0,oh,0,0,0)
        OUT.mkdir(parents=True,exist_ok=True);report=[]
        for name,x,y,z,width in SHOTS:
            write(photo,struct.pack('<I8f',2,x,y,z,0,width,0,0,0))
            frame=struct.unpack_from('<I',read(state+80,4))[0]
            deadline=time.monotonic()+15
            while struct.unpack_from('<I',read(state+80,4))[0]<frame+60:
                if time.monotonic()>deadline:raise TimeoutError('Game renderer did not advance')
                time.sleep(.1)
            write(capture,struct.pack('<I',1))
            while True:
                request,status,w,ht,pitch,pixels=struct.unpack('<6I',read(capture,24))
                if not request:break
                if time.monotonic()>deadline:raise TimeoutError('Native screenshot timed out')
                time.sleep(.05)
            if status or not pixels:raise RuntimeError(f'Capture failed: {status:#x}')
            image=Image.frombytes('RGB',(w,ht),read(pixels,pitch*ht),'raw','BGRX',pitch,1)
            image.save(OUT/(name+'.png'))
            report.append(dict(name=name,focus=[x,y,z],camera_height=width,resolution=[w,ht]))
            print(name,flush=True)
        (OUT/'capture.json').write_text(json.dumps(dict(pid=args.pid,shots=report),indent=2))
    finally:
        if photo is not None and restore is not None:
            write(photo,restore);time.sleep(.3)
        if photo is not None and saved is not None:write(photo,saved)
        k.CloseHandle(h)


if __name__=='__main__':main()
