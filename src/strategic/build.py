"""Build the 32-bit native extension using the reference MSVC 7.1 toolchain."""

from common.paths import ROOT, local_path
from pathlib import Path
import argparse
import os
import subprocess

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,help='Build separately while the installed DLL is in use')
    parser.add_argument('--self-test',action='store_true',help='Compile and run pure overlay tests without launching BFME2')
    args=parser.parse_args()
    compiler_root=local_path('compiler',ROOT.parent/'openbfme2/reference/open-bfme-1/inputs/toolchains/vs2003/Program Files/Microsoft Visual Studio .NET 2003')
    vc=compiler_root/'Vc7'
    output=(args.output_dir or ROOT/'local/runtime/bfme-host/extension').resolve()
    output.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env['PATH']=os.pathsep.join(map(str,[vc/'bin',compiler_root/'Common7/IDE',compiler_root.parents[1]]))+os.pathsep+env['PATH']
    env['INCLUDE']=os.pathsep.join(map(str,[vc/'include',vc/'PlatformSDK/Include']))
    env['LIB']=os.pathsep.join(map(str,[vc/'lib',vc/'PlatformSDK/Lib']))
    command=[str(vc/'bin/cl.exe'),'/nologo','/O2','/MD','/LD','/EHsc',
        str(ROOT/'mods/strategic/native/strategic.cpp'),'/Fe'+str(output/'strategic.dll'),
        '/Fo'+str(output/'strategic.obj'),'/link','/MACHINE:X86','kernel32.lib','user32.lib']
    subprocess.run(command,env=env,cwd=output,check=True)
    if args.self_test:
        test=output/'symbol-overlay-test.exe'
        subprocess.run([str(vc/'bin/cl.exe'),'/nologo','/O2','/MD','/EHsc',
            str(ROOT/'mods/strategic/native/tests/unit_areas_test.cpp'),'/Fe'+str(test),
            '/Fo'+str(output/'symbol-overlay-test.obj')],env=env,cwd=output,check=True)
        subprocess.run([str(test)],env=env,cwd=output,check=True)
    print(output/'strategic.dll')


if __name__=='__main__':main()
