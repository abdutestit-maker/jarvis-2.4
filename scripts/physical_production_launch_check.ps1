$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Launch = Join-Path $Root "Start-JARVIS.ps1"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$ObserverScript = Join-Path $Root "scripts\physical_ws_observer.py"
$EvidenceDir = Join-Path $Root "artifacts\review_20260822\physical_launch"
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class JarvisWin32 {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  public static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool attach);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);
  public static bool FocusWindow(IntPtr hWnd) {
    uint ignored;
    uint targetThread = GetWindowThreadProcessId(hWnd, out ignored);
    uint foregroundThread = GetWindowThreadProcessId(GetForegroundWindow(), out ignored);
    uint currentThread = GetCurrentThreadId();
    bool attached = false;
    if (foregroundThread != 0 && foregroundThread != currentThread) {
      attached = AttachThreadInput(currentThread, foregroundThread, true);
    }
    ShowWindow(hWnd, 9);
    bool result = BringWindowToTop(hWnd);
    result = SetForegroundWindow(hWnd) || result;
    if (targetThread != 0 && targetThread != currentThread && targetThread != foregroundThread) {
      AttachThreadInput(currentThread, targetThread, true);
      SetForegroundWindow(hWnd);
      AttachThreadInput(currentThread, targetThread, false);
    }
    if (attached) AttachThreadInput(currentThread, foregroundThread, false);
    return result;
  }
}
"@

function Fail([string]$Message) { throw $Message }

function Stop-ProjectProcesses {
    $rootPattern = [regex]::Escape($Root)
    $jarvisIds = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            ($_.Name -in @('jarvis-frontend.exe','jarvis-backend.exe') -and $_.ExecutablePath -like "$Root*")
        } | Select-Object -ExpandProperty ProcessId)
    foreach ($id in $jarvisIds) {
        taskkill /PID $id /T /F 2>$null | Out-Null
    }
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            ($_.Name -in @('python.exe','pythonw.exe','node.exe','npm.exe','npx.exe','vite.exe') -and $_.CommandLine -match $rootPattern)
        } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
    Get-ChildItem -LiteralPath (Join-Path $Root 'runtime-temp') -Directory -Filter '_MEI*' -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

function Get-ProjectGui {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'jarvis-frontend.exe' -and $_.ExecutablePath -eq (Join-Path $Root 'jarvis\src-tauri\target\release\jarvis-frontend.exe') } |
        Select-Object -First 1
}

function Get-ProjectBackend {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'jarvis-backend.exe' -and $_.ExecutablePath -like "$($Root)\*" }
}

function Get-NewBrowserIds($Before) {
    $beforeSet = @{}; foreach ($id in $Before) { $beforeSet[[int]$id] = $true }
    @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {$_.Name -in @('chrome.exe','msedge.exe','firefox.exe')} |
        Where-Object {-not $beforeSet.ContainsKey([int]$_.ProcessId)} |
        Select-Object -ExpandProperty ProcessId)
}

function Read-Events([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    @(Get-Content -LiteralPath $Path -Encoding UTF8 -ErrorAction SilentlyContinue |
        ForEach-Object { try { $_ | ConvertFrom-Json } catch {} })
}

function Set-ClipboardUnicode([string]$Text) {
    $command = "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetText('$Text')"
    $setter = Start-Process -FilePath powershell.exe -WindowStyle Hidden -Wait -PassThru -ArgumentList @('-NoProfile', '-STA', '-Command', $command)
    if ($setter.ExitCode -ne 0) { Fail "Не удалось положить текст в clipboard, code=$($setter.ExitCode)" }
}

function Get-EventType($Record) {
    $message = $Record.message
    if ($message.type -eq 'event') { return [string]$message.event.type }
    return [string]$message.type
}

function Get-EventPayload($Record) {
    if ($Record.message.type -eq 'event') { return $Record.message.event.payload }
    return $Record.message
}

function Wait-ForEnd([string]$Events, [int]$Baseline, [int]$TimeoutSec) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        $records = Read-Events $Events
        $ends = @($records | Where-Object { (Get-EventType $_) -eq 'event:jarvis:end' })
        if ($ends.Count -gt $Baseline) { return @{ Records = $records; End = $ends[-1] } }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    Fail "Timeout ожидания event:jarvis:end. events=$Events baseline=$Baseline"
}

function Wait-ForPhysicalCommand([string]$Events, [string]$Text, [int]$TimeoutSec) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        $records = Read-Events $Events
        $markerIndex = -1
        for ($i = 0; $i -lt $records.Count; $i++) {
            if ($records[$i].message.type -eq 'physical_command_sent' -and $records[$i].message.text -eq $Text) { $markerIndex = $i }
        }
        if ($markerIndex -ge 0) {
            for ($i = $markerIndex + 1; $i -lt $records.Count; $i++) {
                if ((Get-EventType $records[$i]) -eq 'event:jarvis:end') { return @{ Records = $records; End = $records[$i] } }
            }
        }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    Fail "Timeout физической команды '$Text'. events=$Events"
}

function Send-GuiText([string]$Text, $Gui) {
    Add-Content -LiteralPath $script:TracePath -Value "send.begin $Text"
    $proc = Get-Process -Id $Gui.ProcessId -ErrorAction Stop
    $handle = $proc.MainWindowHandle
    if ($handle -eq [IntPtr]::Zero) { Fail "У native GUI нет MainWindowHandle: pid=$($Gui.ProcessId)" }
    [JarvisWin32]::FocusWindow($handle) | Out-Null
    # The test desktop has multiple monitors and another foreground app. Put
    # the real native window in front before sending keyboard input.
    [JarvisWin32]::SetWindowPos($handle, [JarvisWin32]::HWND_TOPMOST, 0, 0, 0, 0, 0x43) | Out-Null
    [JarvisWin32]::SetForegroundWindow($handle) | Out-Null
    Add-Content -LiteralPath $script:TracePath -Value "send.focus pid=$($Gui.ProcessId) handle=$handle"
    Start-Sleep -Milliseconds 300
    $rect = New-Object 'JarvisWin32+RECT'
    if (-not [JarvisWin32]::GetWindowRect($handle, [ref]$rect)) { Fail "GetWindowRect не сработал" }
    $x = [int](($rect.Left + $rect.Right) / 2)
    $y = [int]($rect.Top + 390)
    [JarvisWin32]::SetCursorPos($x, $y) | Out-Null
    [JarvisWin32]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    [JarvisWin32]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 100
    Set-ClipboardUnicode $Text
    Add-Content -LiteralPath $script:TracePath -Value 'send.clipboard'
    [System.Windows.Forms.SendKeys]::SendWait('^v')
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
    Start-Sleep -Milliseconds 300
    Add-Content -LiteralPath $script:TracePath -Value 'send.end'
}

$allRuns = @()
for ($run = 1; $run -le 2; $run++) {
    Stop-ProjectProcesses
    Get-Process -Name notepad -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    $runDir = Join-Path $EvidenceDir "run-$run"
    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
    $eventsPath = Join-Path $runDir 'ws-events.jsonl'
    $readyPath = Join-Path $runDir 'runtime-ready.json'
    $commandsPath = Join-Path $runDir 'commands.json'
    $script:TracePath = Join-Path $runDir 'steps.log'
    Set-Content -LiteralPath $script:TracePath -Value "run=$run"
    @('привет', 'открой блокнот') | ConvertTo-Json | Set-Content -LiteralPath $commandsPath -Encoding utf8
    Remove-Item -LiteralPath $eventsPath, $readyPath -Force -ErrorAction SilentlyContinue
    $beforeBrowsers = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {$_.Name -in @('chrome.exe','msedge.exe','firefox.exe')} | Select-Object -ExpandProperty ProcessId)
    $observerProcess = Start-Process -FilePath $Python -WorkingDirectory $Root -WindowStyle Hidden -PassThru -ArgumentList @($ObserverScript, '--events', $eventsPath, '--ready', $readyPath, '--timeout', '240', '--commands-file', $commandsPath)
    $launchOutput = Join-Path $runDir 'launcher-output.txt'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launch *>&1 | Out-File -LiteralPath $launchOutput -Encoding utf8
    if ($LASTEXITCODE -ne 0) { Fail "Start-JARVIS.ps1 завершился с кодом $LASTEXITCODE" }
    $deadline = (Get-Date).AddSeconds(20)
    do { $gui = Get-ProjectGui; if (-not $gui) { Start-Sleep -Milliseconds 250 } } while (-not $gui -and (Get-Date) -lt $deadline)
    if (-not $gui) { Fail "Production native GUI не запустился в run-$run" }
    $newBrowsers = Get-NewBrowserIds $beforeBrowsers
    if ($newBrowsers.Count -gt 0) { Fail "Запущен браузер вместо native GUI: $($newBrowsers -join ',')" }
    $deadline = (Get-Date).AddSeconds(180)
    while (-not (Test-Path -LiteralPath $readyPath) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 250 }
    if (-not (Test-Path -LiteralPath $readyPath)) { Fail "READY от backend+model не получен в run-$run" }
    $backendTree = @(Get-ProjectBackend)
    $backendIds = @($backendTree | ForEach-Object { [int]$_.ProcessId })
    $backendRoots = @($backendTree | Where-Object { $backendIds -notcontains [int]$_.ParentProcessId })
    if ($backendRoots.Count -ne 1) { Fail "Ожидалось одно дерево скрытого backend, фактически roots=$($backendRoots.Count), processes=$($backendTree.Count) в run-$run" }
    $projectNode = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {$_.Name -in @('node.exe','npm.exe','npx.exe','vite.exe') -and $_.CommandLine -match [regex]::Escape($Root)})
    if ($projectNode.Count -gt 0) { Fail "Production запуск поднял Node/Vite: $($projectNode.Name -join ',')" }
    $first = Wait-ForPhysicalCommand $eventsPath 'привет' 120
    Start-Sleep -Seconds 1
    $firstPayload = Get-EventPayload $first.End
    if ([string]::IsNullOrWhiteSpace([string]$firstPayload.content)) { Fail "Пустой ответ на привет в run-$run" }
    if ([string]$firstPayload.model -ne 'local') { Fail "Ответ на привет не помечен local: $($firstPayload | ConvertTo-Json -Compress)" }
    $second = Wait-ForPhysicalCommand $eventsPath 'открой блокнот' 120
    Start-Sleep -Seconds 2
    $second.Records = Read-Events $eventsPath
    $secondPayload = Get-EventPayload $second.End
    $tool = @($second.Records | Where-Object { (Get-EventType $_) -eq 'event:tool' } | ForEach-Object { Get-EventPayload $_ } | Where-Object {$_.tool -eq 'open_app' -or $_.content -eq 'open_app'})
    $result = @($second.Records | Where-Object { (Get-EventType $_) -eq 'event:result' } | ForEach-Object { Get-EventPayload $_ } | Where-Object {$_.verified -eq $true})
    $notepad = @(Get-Process -Name notepad -ErrorAction SilentlyContinue)
    if ([string]::IsNullOrWhiteSpace([string]$secondPayload.content)) { Fail "Пустой ответ на открой блокнот в run-$run" }
    if ($tool.Count -eq 0 -or $result.Count -eq 0) { Fail "open_app/tool/verifier не подтверждены в run-$run" }
    if ($notepad.Count -eq 0 -and ([string]$secondPayload.content -notmatch 'pid=')) { Fail "Notepad не появился и ответ не содержит pid в run-$run" }
    $guiProc = Get-Process -Id $gui.ProcessId -ErrorAction Stop
    $closeSent = $guiProc.CloseMainWindow()
    if (-not $closeSent) { Fail "Native GUI не принял CloseMainWindow в run-$run" }
    $guiDeadline = (Get-Date).AddSeconds(20)
    while ((Get-ProjectGui) -and (Get-Date) -lt $guiDeadline) { Start-Sleep -Milliseconds 250 }
    if (Get-ProjectGui) { Fail "Native GUI не завершился после закрытия в run-$run" }
    Start-Sleep -Seconds 3
    $backendAfterClose = @(Get-ProjectBackend)
    if ($backendAfterClose.Count -ne 0) { Fail "Backend остался после закрытия GUI в run-${run}: $($backendAfterClose.ProcessId -join ',')" }
    $runRecord = [ordered]@{
        run = $run
        native_gui_pid = $gui.ProcessId
        backend_pid = $backendRoots.ProcessId
        backend_process_tree_pids = $backendIds
        runtime_ready = (Get-Content $readyPath -Raw | ConvertFrom-Json).message.diagnostics.runtime.warmup_complete
        greeting = [string]$firstPayload.content
        greeting_model = [string]$firstPayload.model
        open_app = [string]$secondPayload.content
        open_app_tool_verified = ($tool.Count -gt 0 -and $result.Count -gt 0)
        notepad_process_seen = ($notepad.Count -gt 0)
        close_main_window = $closeSent
        backend_gone_after_close = ($backendAfterClose.Count -eq 0)
        event_log = $eventsPath
    }
    $runRecord | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $runDir 'result.json') -Encoding utf8
    $allRuns += [pscustomobject]$runRecord
    Stop-ProjectProcesses
}

$report = [ordered]@{
    suite = 'physical_native_gui_launch_check'
    launcher = $Launch
    runs = $allRuns
    passed = $true
    generated_at = (Get-Date).ToString('o')
}
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $EvidenceDir 'report.json') -Encoding utf8
$report | ConvertTo-Json -Depth 12
