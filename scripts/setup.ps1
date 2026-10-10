param([string]$BfmePath='', [double]$ZoomFactor=24, [double]$ArmyFactor=4, [int]$StartingCash=10000, [int]$StartingCommandPoints=1000)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'python.ps1')
$pythonExe=Find-WorkshopPython
$projectDir=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPython=Join-Path $projectDir 'local/venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $pythonExe -m venv (Join-Path $projectDir 'local/venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$pythonExe=$venvPython
& $pythonExe -m pip install -e "${projectDir}[video]"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$buildArgs=@((Join-Path $PSScriptRoot 'workshop.py'),'host','build','--zoom-factor',$ZoomFactor,'--army-factor',$ArmyFactor,'--starting-cash',$StartingCash,'--starting-command-points',$StartingCommandPoints)
if ($BfmePath) { $buildArgs+=@('--bfme',$BfmePath) }
& $pythonExe @buildArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Push-Location $projectDir
try {
    & $pythonExe (Join-Path $PSScriptRoot 'workshop.py') map build ithilien-frontier
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $pythonExe (Join-Path $PSScriptRoot 'workshop.py') map build ashen-march
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
& $pythonExe (Join-Path $PSScriptRoot 'workshop.py') host prepare
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonExe (Join-Path $PSScriptRoot 'workshop.py') mod build
exit $LASTEXITCODE
