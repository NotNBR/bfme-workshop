param([switch]$Window, [switch]$DryRun, [switch]$Test, [switch]$ZoomCheck, [switch]$StrategicCheck, [switch]$CameraTrace, [switch]$NoStrategic, [switch]$Menu, [string]$Map='', [ValidateSet('','orcs-elves')][string]$Battle='')
& (Join-Path $PSScriptRoot '..\..\..\scripts\start.ps1') @PSBoundParameters
exit $LASTEXITCODE
