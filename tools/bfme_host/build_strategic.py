"""Build the 32-bit native extension using the reference MSVC 7.1 toolchain."""
from pathlib import Path
import os
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def main():
    compiler_root=ROOT.parent/'openbfme2/reference/open-bfme-1/inputs/toolchains/vs2003/Program Files/Microsoft Visual Studio .NET 2003'
    vc=compiler_root/'Vc7'
    output=ROOT/'runtime/bfme-host/extension'
    output.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env['PATH']=os.pathsep.join(map(str,[vc/'bin',compiler_root/'Common7/IDE',compiler_root.parents[1]]))+os.pathsep+env['PATH']
    env['INCLUDE']=os.pathsep.join(map(str,[vc/'include',vc/'PlatformSDK/Include']))
    env['LIB']=os.pathsep.join(map(str,[vc/'lib',vc/'PlatformSDK/Lib']))
    command=[str(vc/'bin/cl.exe'),'/nologo','/O2','/MD','/LD','/EHsc',
        str(ROOT/'native/host/strategic.cpp'),'/Fe'+str(output/'bfmexbar-strategic.dll'),
        '/Fo'+str(output/'strategic.obj'),'/link','/MACHINE:X86','kernel32.lib']
    subprocess.run(command,env=env,cwd=output,check=True)
    print(output/'bfmexbar-strategic.dll')


if __name__=='__main__':main()
