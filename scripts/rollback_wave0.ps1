param([string]$Workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path)
$ErrorActionPreference = 'Stop'
Set-Location $Workspace
Write-Host 'Wave 0 rollback is additive: remove only generated Universal Intelligence files and restore tracked files from the pre-wave patch.'
Write-Host 'Review artifacts/verification/wave0/diff.patch before applying any inverse patch.'
Write-Host 'No frontend, voice, Browser Bridge, or data files are touched by this script.'
