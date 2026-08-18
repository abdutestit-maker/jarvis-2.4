$ErrorActionPreference = 'Stop'
$archiveRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\artifacts')).Path
$archiveDir = Join-Path $archiveRoot 'archive'
$stage = Join-Path $archiveDir 'source_snapshots'
New-Item -ItemType Directory -Force -Path $stage | Out-Null
$candidates = @(Get-ChildItem $archiveRoot -Directory -Recurse | Where-Object {
    $_.Name -eq 'core' -and $_.FullName -notmatch '\\original(\\|$)' -and
    $_.FullName -notmatch '\\archive(\\|$)'
})
$manifest = foreach ($src in $candidates) {
    $rel = $src.FullName.Substring($archiveRoot.Length).TrimStart('\')
    $dest = Join-Path $stage $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item -LiteralPath $src.FullName -Destination $dest -Recurse -Force
    [pscustomobject]@{
        source = $src.FullName
        archived = $dest
        files = @(Get-ChildItem $src.FullName -Recurse -File).Count
    }
}
$manifest | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $stage 'manifest.json') -Encoding utf8
$zip = Join-Path $archiveDir 'source_snapshots.zip'
if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -CompressionLevel Optimal
if (-not (Test-Path $zip)) { throw 'archive missing' }
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash
[pscustomobject]@{
    archive = $zip
    sha256 = $hash
    source_core_dirs = $candidates.Count
    source_bytes = (($candidates | ForEach-Object {
        (Get-ChildItem $_.FullName -Recurse -File | Measure-Object Length -Sum).Sum
    } | Measure-Object -Sum).Sum)
} | ConvertTo-Json | Set-Content (Join-Path $archiveDir 'source_snapshots.sha256.json') -Encoding utf8
$stageResolved = (Resolve-Path $stage).Path
if ($stageResolved -notlike "$archiveDir*") { throw 'unsafe stage path' }
Remove-Item -LiteralPath $stage -Recurse -Force
foreach ($item in $candidates) {
    $resolved = (Resolve-Path $item.FullName).Path
    if ($resolved -notlike "$archiveRoot*" -or $resolved -like '*\original\*' -or $resolved -like "$archiveDir*") {
        throw "unsafe source path: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
Write-Output "ARCHIVED=$($candidates.Count) ZIP_BYTES=$((Get-Item $zip).Length) SHA256=$hash"
