param([int]$ArmySize=525, [switch]$Test, [switch]$Headless, [switch]$Hidden)
& (Join-Path $PSScriptRoot '..\..\legacy\recoil\tools\start.ps1') @PSBoundParameters
exit $LASTEXITCODE
