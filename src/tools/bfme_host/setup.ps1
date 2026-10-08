param([string]$BfmePath='', [double]$ZoomFactor=24, [double]$ArmyFactor=4)
& (Join-Path $PSScriptRoot '..\..\..\scripts\setup.ps1') @PSBoundParameters
exit $LASTEXITCODE
