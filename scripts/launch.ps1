# Forward native launcher flags from the shortcuts in scripts/launchers/.
$ErrorActionPreference = 'Stop'
$gameArguments = @($args)
. (Join-Path $PSScriptRoot 'python.ps1')
$pythonExe = Find-BfxPython
& $pythonExe (Join-Path $PSScriptRoot 'bfx.py') play @gameArguments
exit $LASTEXITCODE
