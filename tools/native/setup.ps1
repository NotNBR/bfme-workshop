param([string]$BfmePath = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'python.ps1')
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $BfmePath) { $BfmePath = Join-Path (Split-Path $root) 'bfme2' }
if (-not (Test-Path -LiteralPath (Join-Path $BfmePath 'W3D.big'))) {
    throw "BFME II W3D.big not found in $BfmePath. Pass -BfmePath to your local installation."
}
$pythonExe = Find-BfxPython
& $pythonExe -c 'import numpy, PIL' 2>$null
if ($LASTEXITCODE -ne 0) {
    & $pythonExe -m venv (Join-Path $root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the local Python environment.' }
    $pythonExe = Find-BfxPython
    & $pythonExe -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
$engine = Join-Path $root 'runtime\engine'
$version = '2026.07.04'
$sha = '2e0a43744115e6b3cbd7db4a36aecc3d28afdef4fb615d07ab01703e4b5525e1'
if (-not (Test-Path -LiteralPath (Join-Path $engine 'spring.exe'))) {
    $archive = Join-Path $root '.cache\recoil.7z'
    New-Item -ItemType Directory -Force (Split-Path $archive), $engine | Out-Null
    if (-not (Test-Path -LiteralPath $archive)) {
        Invoke-WebRequest "https://github.com/beyond-all-reason/RecoilEngine/releases/download/$version/recoil_${version}_amd64-windows.7z" -OutFile $archive
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower() -ne $sha) {
        throw 'Engine archive checksum mismatch. The archive was not extracted.'
    }
    $sevenZip = Join-Path $env:ProgramFiles '7-Zip\7z.exe'
    if (-not (Test-Path -LiteralPath $sevenZip)) { throw 'Install 7-Zip to unpack the pinned Recoil release.' }
    & $sevenZip x $archive "-o$engine" -y | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Engine extraction failed.' }
}
$actualVersion = & (Join-Path $engine 'spring-headless.exe') --sync-version
if ($actualVersion.Trim() -ne $version) { throw "Expected Recoil $version; found $actualVersion" }
& $pythonExe (Join-Path $PSScriptRoot 'build.py') --bfme $BfmePath
if ($LASTEXITCODE -ne 0) { throw 'BFME native content import failed.' }
@{version=$version; sha256=$sha; source='https://github.com/beyond-all-reason/RecoilEngine'} |
    ConvertTo-Json | Set-Content (Join-Path $root 'runtime\engine-version.json')
Write-Host 'Ready. Launch bfmeXbar.cmd starts the native game.'
