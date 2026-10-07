param([string]$BfmePath='', [double]$ZoomFactor=24, [double]$ArmyFactor=4)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\native\python.ps1')
$pythonExe=Find-BfxPython
$projectDir=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$venvPython=Join-Path $projectDir '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $pythonExe -m venv (Join-Path $projectDir '.venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$pythonExe=$venvPython
& $pythonExe -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$buildArgs=@((Join-Path $PSScriptRoot 'build.py'),'--zoom-factor',$ZoomFactor,'--army-factor',$ArmyFactor)
if ($BfmePath) { $buildArgs+=@('--bfme',$BfmePath) }
& $pythonExe @buildArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonExe (Join-Path $PSScriptRoot 'prepare.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonExe (Join-Path $PSScriptRoot 'build_strategic.py')
exit $LASTEXITCODE
