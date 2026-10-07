function Find-BfxPython {
    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    $venv = Join-Path $PSScriptRoot '..\..\.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venv) { return (Resolve-Path -LiteralPath $venv).Path }
    if (Test-Path -LiteralPath $bundled) { return $bundled }
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw 'Python 3.11 or later is required to import local BFME assets.'
}
