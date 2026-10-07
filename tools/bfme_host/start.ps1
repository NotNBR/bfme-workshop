param([switch]$Window, [switch]$DryRun, [switch]$Test, [switch]$ZoomCheck, [switch]$StrategicCheck, [switch]$CameraTrace, [switch]$NoStrategic, [switch]$Menu, [string]$Map='', [ValidateSet('','orcs-elves')][string]$Battle='')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\native\python.ps1')
$pythonExe=Find-BfxPython
$launchArgs=@((Join-Path $PSScriptRoot 'launch.py'))
if ($Window) { $launchArgs+='--window' }
if ($DryRun) { $launchArgs+='--dry-run' }
if ($Test) { $launchArgs+='--test' }
if ($ZoomCheck) { $launchArgs+='--zoom-check' }
if ($StrategicCheck) { $launchArgs+='--strategic-check' }
if ($CameraTrace) { $launchArgs+='--camera-trace' }
if (-not $NoStrategic) { $launchArgs+='--strategic' }
if ($Menu) { $launchArgs+='--menu' }
if ($Map) { $launchArgs+=@('--map',$Map) }
if ($Battle) { $launchArgs+=@('--battle',$Battle) }
& $pythonExe @launchArgs
exit $LASTEXITCODE
