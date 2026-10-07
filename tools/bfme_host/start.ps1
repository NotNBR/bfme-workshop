param([switch]$Window, [switch]$DryRun, [switch]$Test, [switch]$ZoomCheck, [switch]$Menu, [string]$Map='')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\native\python.ps1')
$pythonExe=Find-BfxPython
$launchArgs=@((Join-Path $PSScriptRoot 'launch.py'))
if ($Window) { $launchArgs+='--window' }
if ($DryRun) { $launchArgs+='--dry-run' }
if ($Test) { $launchArgs+='--test' }
if ($ZoomCheck) { $launchArgs+='--zoom-check' }
if ($Menu) { $launchArgs+='--menu' }
if ($Map) { $launchArgs+=@('--map',$Map) }
& $pythonExe @launchArgs
exit $LASTEXITCODE
