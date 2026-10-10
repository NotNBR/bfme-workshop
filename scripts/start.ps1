param([switch]$Window, [switch]$DryRun, [switch]$Test, [switch]$ZoomCheck, [switch]$StrategicCheck, [switch]$CameraTrace, [switch]$NoStrategic, [switch]$Menu, [string]$Map='', [ValidateSet('','orcs-elves')][string]$Battle='', [int]$StartingCash=10000, [int]$StartingCommandPoints=1000)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'python.ps1')
$pythonExe=Find-WorkshopPython
$launchArgs=@((Join-Path $PSScriptRoot 'workshop.py'),'play')
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
if ($PSBoundParameters.ContainsKey('StartingCash')) { $launchArgs+=@('--starting-cash',$StartingCash) }
if ($PSBoundParameters.ContainsKey('StartingCommandPoints')) { $launchArgs+=@('--starting-command-points',$StartingCommandPoints) }
& $pythonExe @launchArgs
exit $LASTEXITCODE
