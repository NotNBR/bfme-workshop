param([string]$BfmePath='', [double]$ZoomFactor=24, [double]$ArmyFactor=4)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'python.ps1')
$pythonExe=Find-BfxPython
$projectDir=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPython=Join-Path $projectDir '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $pythonExe -m venv (Join-Path $projectDir '.venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$pythonExe=$venvPython
& $pythonExe -m pip install -e "${projectDir}[video]"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$buildArgs=@((Join-Path $PSScriptRoot 'bfx.py'),'host','build','--zoom-factor',$ZoomFactor,'--army-factor',$ArmyFactor)
if ($BfmePath) { $buildArgs+=@('--bfme',$BfmePath) }
& $pythonExe @buildArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Push-Location $projectDir
try {
    & $pythonExe (Join-Path $PSScriptRoot 'bfx.py') map build ithilien-frontier
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $pythonExe (Join-Path $PSScriptRoot 'bfx.py') map build ashen-march
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
& $pythonExe (Join-Path $PSScriptRoot 'bfx.py') host prepare
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonExe (Join-Path $PSScriptRoot 'bfx.py') mod build
exit $LASTEXITCODE
