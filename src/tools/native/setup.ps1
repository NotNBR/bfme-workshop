param([string]$BfmePath = '')
& (Join-Path $PSScriptRoot '..\..\legacy\recoil\tools\setup.ps1') @PSBoundParameters
exit $LASTEXITCODE
