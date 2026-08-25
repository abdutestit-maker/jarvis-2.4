$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Launch = Join-Path $Root "Start-JARVIS.ps1"
$Python = (Get-Command python -ErrorAction Stop).Source
$Observer = Join-Path $Root "scripts\physical_ws_observer.py"
$Evidence = Join-Path $Root "artifacts\review_20260823\deepseek_native_e2e"
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null

if ([string]::IsNullOrWhiteSpace($env:DEEPINFRA_API_KEY) -and
    [string]::IsNullOrWhiteSpace($env:ATLAS_SECRET_DEEPINFRA_API_KEY)) {
    throw "DEEPINFRA_API_KEY or ATLAS_SECRET_DEEPINFRA_API_KEY is required for the real DeepSeek E2E run."
}

function Stop-ProjectProcesses {
    $pattern = [regex]::Escape($Root)
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            ($_.Name -in @('jarvis-frontend.exe','jarvis-backend.exe','llama-server.exe') -and
                ($_.ExecutablePath -like "$Root*" -or $_.Name -eq 'llama-server.exe')) -or
            ($_.Name -in @('python.exe','pythonw.exe','node.exe','npm.exe','npx.exe','vite.exe') -and
                $_.CommandLine -match $pattern)
        } | ForEach-Object {
            taskkill /PID $_.ProcessId /T /F 2>$null | Out-Null
        }
    Start-Sleep -Seconds 2
}

function Read-JsonLines([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    @(Get-Content -LiteralPath $Path -Encoding UTF8 -ErrorAction SilentlyContinue |
        ForEach-Object { try { $_ | ConvertFrom-Json } catch {} })
}

function Event-Type($record) {
    if ($record.message.type -eq 'event') { return [string]$record.message.event.type }
    return [string]$record.message.type
}

function Event-Payload($record) {
    if ($record.message.type -eq 'event') { return $record.message.event.payload }
    return $record.message
}

function Wait-ProcessByPath([string]$Path, [int]$TimeoutSec) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        $process = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq 'jarvis-frontend.exe' -and $_.ExecutablePath -eq $Path } |
            Select-Object -First 1
        if ($process) { return $process }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    throw "Native GUI did not start: $Path"
}

$commands = @(
    'как дела?',
    'мне скучно, предложи что-нибудь',
    'что именно?',
    'квантовый чайник 7f3a говорит с северным окном',
    'какой сегодня статус системы?',
    'объясни разницу между памятью и контекстом',
    'открой блокнот',
    'поставь музыку',
    'придумай короткую идею для вечера',
    'закрой блокнот'
)
$allRuns = @()
for ($run = 1; $run -le 2; $run++) {
    Stop-ProjectProcesses
    Get-Process -Name notepad -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    $dir = Join-Path $Evidence "run-${run}"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $events = Join-Path $dir 'ws-events.jsonl'
    $ready = Join-Path $dir 'runtime-ready.json'
    $commandsFile = Join-Path $dir 'commands.json'
    $commands | ConvertTo-Json | Set-Content -LiteralPath $commandsFile -Encoding UTF8
    Remove-Item -LiteralPath $events,$ready -Force -ErrorAction SilentlyContinue
    $observer = Start-Process -FilePath $Python -WorkingDirectory $Root -WindowStyle Hidden -PassThru -ArgumentList @(
        $Observer, '--events', $events, '--ready', $ready, '--timeout', '300', '--commands-file', $commandsFile
    )
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launch *>&1 |
        Out-File -LiteralPath (Join-Path $dir 'launcher-output.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw "Start-JARVIS.ps1 failed in run-${run}: $LASTEXITCODE" }
    $gui = Wait-ProcessByPath (Join-Path $Root 'jarvis\src-tauri\target\release\jarvis-frontend.exe') 30
    $node = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @('node.exe','npm.exe','npx.exe','vite.exe') -and $_.CommandLine -match [regex]::Escape($Root) })
    if ($node.Count -gt 0) { throw "Production launch started Node/Vite in run-${run}" }
    $deadline = (Get-Date).AddSeconds(180)
    while (-not (Test-Path -LiteralPath $ready) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 250 }
    if (-not (Test-Path -LiteralPath $ready)) { throw "READY was not received in run-${run}" }
    $readyRecord = (Get-Content $ready -Raw | ConvertFrom-Json).message
    $warmup = $readyRecord.diagnostics
    if ($readyRecord.state -ne 'ready' -or $readyRecord.ready -ne $true) { throw "Runtime is not READY in run-${run}" }
    if ($warmup.runtime.provider -ne 'deepinfra' -or $warmup.runtime.model_probe -ne $true) { throw "DeepInfra readiness probe missing in run-${run}" }
    if ($warmup.model -ne 'deepseek-ai/DeepSeek-V4-Flash-0731') { throw "Wrong brain model in run-${run}" }
    if ($observer.WaitForExit(330000) -eq $false) { throw "Observer timeout in run-${run}" }
    $records = Read-JsonLines $events
    $sent = @($records | Where-Object { $_.message.type -eq 'physical_command_sent' })
    $ends = @($records | Where-Object { (Event-Type $_) -eq 'event:jarvis:end' })
    if ($sent.Count -ne $commands.Count -or $ends.Count -lt $commands.Count) { throw "Not all native GUI/WS commands completed in run-${run}: sent=$($sent.Count), ends=$($ends.Count)" }
    $badModel = @($ends | Where-Object { (Event-Payload $_).model -ne 'deepseek-ai/DeepSeek-V4-Flash-0731' })
    if ($badModel.Count -gt 0) { throw "A production response was not generated by DeepSeek in run-${run}" }
    $forbidden = @('источник временно не ответил', 'канал связи работает', 'готов помочь с задачей')
    foreach ($end in $ends) {
        $content = ([string](Event-Payload $end).content).ToLowerInvariant()
        if ([string]::IsNullOrWhiteSpace($content)) { throw "Empty model response in run-${run}" }
        foreach ($phrase in $forbidden) { if ($content.Contains($phrase)) { throw "Canned response detected in run-${run}: $phrase" } }
    }
    $tool = @($records | Where-Object { (Event-Type $_) -eq 'event:tool' } | ForEach-Object { Event-Payload $_ } | Where-Object { $_.tool -eq 'open_app' })
    $verified = @($records | Where-Object { (Event-Type $_) -eq 'event:result' } | ForEach-Object { Event-Payload $_ } | Where-Object { $_.verified -eq $true })
    if ($tool.Count -eq 0 -or $verified.Count -eq 0) { throw "open_app -> verifier was not observed in run-${run}" }
    if (@(Get-Process -Name notepad -ErrorAction SilentlyContinue).Count -eq 0) { throw "Notepad was not physically started in run-${run}" }
    $guiProc = Get-Process -Id $gui.ProcessId -ErrorAction Stop
    if (-not $guiProc.CloseMainWindow()) { throw "Native GUI close was not accepted in run-${run}" }
    $deadline = (Get-Date).AddSeconds(25)
    while ((Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessId -eq $gui.ProcessId }) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 250 }
    if (Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessId -eq $gui.ProcessId }) { throw "Native GUI remained alive in run-${run}" }
    Start-Sleep -Seconds 3
    $backend = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'jarvis-backend.exe' -and $_.ExecutablePath -like "$Root*" })
    if ($backend.Count -gt 0) { throw "Backend remained after GUI close in run-${run}" }
    $result = [ordered]@{ run=$run; ready=$true; commands=$sent.Count; ends=$ends.Count; deepseek=$true; open_app_verified=$true; gui_closed=$true; backend_closed=($backend.Count -eq 0); events=$events }
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $dir 'result.json') -Encoding UTF8
    $allRuns += [pscustomobject]$result
    Stop-ProjectProcesses
}
$report = [ordered]@{ suite='deepseek_native_gui_e2e'; passed=$true; runs=$allRuns; generated_at=(Get-Date).ToString('o') }
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Evidence 'report.json') -Encoding UTF8
$report | ConvertTo-Json -Depth 12
