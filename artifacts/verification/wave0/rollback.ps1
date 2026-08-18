param([string]$Workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path)
$ErrorActionPreference = 'Stop'
Set-Location $Workspace
Write-Host 'Wave 0 rollback is intentionally additive-safe.'
Write-Host 'Review diff.patch, then restore only the files listed in its pre-wave manifest.'
Write-Host 'This script never touches frontend, voice, Browser Bridge, data, or user secrets.'
