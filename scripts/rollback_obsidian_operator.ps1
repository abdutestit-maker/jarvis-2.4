param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($ProjectRoot)
$baseline = Join-Path $root 'artifacts\obsidian_operator\baseline'

if (-not (Test-Path -LiteralPath (Join-Path $baseline 'App.tsx'))) {
    throw "Obsidian Operator baseline is missing: $baseline"
}

$restore = @{
    (Join-Path $baseline 'App.tsx') = (Join-Path $root 'jarvis\src\App.tsx')
    (Join-Path $baseline 'presence.css') = (Join-Path $root 'jarvis\src\presence.css')
    (Join-Path $baseline 'package.json') = (Join-Path $root 'jarvis\package.json')
    (Join-Path $baseline 'tauri.conf.json') = (Join-Path $root 'jarvis\src-tauri\tauri.conf.json')
    (Join-Path $baseline 'default.json') = (Join-Path $root 'jarvis\src-tauri\capabilities\default.json')
}

foreach ($entry in $restore.GetEnumerator()) {
    Copy-Item -LiteralPath $entry.Key -Destination $entry.Value -Force
}

$remove = @(
    'jarvis\src\operator\model.ts',
    'jarvis\src\operator\OperatorShell.tsx',
    'jarvis\scripts\operatorModel.test.ts',
    'scripts\capture_obsidian_operator.py',
    '_shots\obsidian-operator\01-compact-live.png',
    '_shots\obsidian-operator\02-command-center-live.png',
    '_shots\obsidian-operator\03-verification-live.png',
    '_shots\obsidian-operator\04-verified-live.png',
    'design\obsidian-operator\mockups\01-compact-presence.png',
    'design\obsidian-operator\mockups\02-command-center.png',
    'design\obsidian-operator\mockups\03-installation-verification.png',
    'design\obsidian-operator\mockups\04-verified-success.png'
)

foreach ($relative in $remove) {
    $target = [System.IO.Path]::GetFullPath((Join-Path $root $relative))
    if (-not $target.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Rollback target escaped project root: $target"
    }
    Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
}

Push-Location (Join-Path $root 'jarvis')
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Restored frontend build failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host 'Obsidian Operator rollback verified.'
