# Forward native launcher flags from the shortcuts in scripts/launchers/.
$ErrorActionPreference = 'Stop'
$gameArguments = @($args)
. (Join-Path $PSScriptRoot 'python.ps1')
$pythonExe = Find-WorkshopPython
& $pythonExe (Join-Path $PSScriptRoot 'workshop.py') play @gameArguments
exit $LASTEXITCODE
