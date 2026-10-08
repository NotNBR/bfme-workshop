param([int]$ArmySize=525, [switch]$Test, [switch]$Headless, [switch]$Hidden)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\..\..\scripts\python.ps1')
$pythonExe=Find-BfxPython
$launchArgs=@((Join-Path $PSScriptRoot 'launch.py'),'--army-size', $ArmySize)
if ($Test) { $launchArgs += @('--test','--timeout','180') }
if ($Headless) { $launchArgs += '--headless' }
if ($Hidden) { $launchArgs += '--hidden' }
& $pythonExe @launchArgs
exit $LASTEXITCODE
