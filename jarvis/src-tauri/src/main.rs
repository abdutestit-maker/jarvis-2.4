mod window_effects;

use std::{fs, net::TcpStream, path::PathBuf, process::{Child, Command}, sync::Mutex, thread, time::Duration};
use serde::Deserialize;
use tauri::{Emitter, Manager, WebviewWindowBuilder, WebviewUrl, menu::{Menu, MenuItem}, tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent}};
use tauri_plugin_global_shortcut::GlobalShortcutExt;

struct BackendProcess(Mutex<Option<Child>>);
#[derive(Clone, Deserialize)] struct SettingsFile { launcher: Option<LauncherSettings> }
#[derive(Clone, Deserialize)] struct LauncherSettings { autostart: Option<bool>, hotkey: Option<String>, backend_command: Option<Vec<String>>, backend_workdir: Option<String> }
impl Default for LauncherSettings { fn default() -> Self { Self { autostart: Some(false), hotkey: Some("Ctrl+Space".into()), backend_command: Some(vec!["python".into(), "-m".into(), "core.ws_server".into()]), backend_workdir: Some(String::new()) } } }

fn project_root() -> PathBuf {
    let compiled = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let mut candidates = vec![compiled, std::env::current_dir().unwrap_or_default()];
    if let Ok(exe) = std::env::current_exe() {
        candidates.extend(exe.ancestors().map(PathBuf::from));
    }
    candidates.into_iter()
        .find(|path| path.join("config/settings.json").is_file() || path.join("config").is_dir())
        .and_then(|path| path.canonicalize().ok())
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."))
}
fn launcher_settings() -> LauncherSettings { fs::read_to_string(project_root().join("config/settings.json")).ok().and_then(|raw| serde_json::from_str::<SettingsFile>(&raw).ok()).and_then(|config| config.launcher).unwrap_or_default() }
fn backend_is_listening() -> bool { TcpStream::connect_timeout(&"127.0.0.1:8771".parse().expect("socket"), Duration::from_millis(150)).is_ok() }
fn resolve_backend_program(program: &str) -> String {
    if !program.eq_ignore_ascii_case("python") && !program.eq_ignore_ascii_case("pythonw") {
        return program.to_string();
    }
    let mut candidates = Vec::new();
    if let Ok(value) = std::env::var("JARVIS_PYTHON") { candidates.push(PathBuf::from(value)); }
    if let Ok(home) = std::env::var("USERPROFILE") {
        let root = PathBuf::from(home);
        candidates.push(root.join("AppData/Local/hermes/hermes-agent/venv/Scripts/pythonw.exe"));
        candidates.push(root.join("AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"));
        candidates.push(root.join("venv/Scripts/pythonw.exe"));
        candidates.push(root.join("venv/Scripts/python.exe"));
    }
    candidates.push(PathBuf::from("pythonw.exe"));
    candidates.push(PathBuf::from("python.exe"));
    candidates.into_iter().find(|candidate| candidate.is_file()).map(|candidate| candidate.to_string_lossy().into_owned()).unwrap_or_else(|| program.to_string())
}
fn spawn_backend(settings: &LauncherSettings) -> Option<Child> {
    if backend_is_listening() { return None; }
    let command = settings.backend_command.clone().unwrap_or_default();
    let (program, args) = command.split_first()?;
    let program = resolve_backend_program(program);
    let dir = settings.backend_workdir.as_deref()
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .filter(|value| value.is_dir())
        .unwrap_or_else(project_root);
    let mut builder = Command::new(program);
    builder.args(args).current_dir(&dir);
    #[cfg(windows)] {
        use std::os::windows::process::CommandExt;
        builder.creation_flags(0x08000000);
    }
    match builder.spawn() {
        Ok(child) => Some(child),
        Err(error) => { eprintln!("JARVIS backend launch failed in {}: {}", dir.display(), error); None }
    }
}
fn manage_backend(app: tauri::AppHandle, settings: LauncherSettings) { thread::spawn(move || loop { let state = app.state::<BackendProcess>(); let mut child = match state.0.lock() { Ok(guard) => guard, Err(_) => break }; let restart = child.as_mut().map(|process| process.try_wait().ok().flatten().is_some()).unwrap_or(!backend_is_listening()); if restart { *child = spawn_backend(&settings); } drop(child); thread::sleep(Duration::from_secs(5)); }); }

#[cfg(windows)] fn sync_autostart(enabled: bool) { use winreg::{enums::HKEY_CURRENT_USER, RegKey}; let hkcu = RegKey::predef(HKEY_CURRENT_USER); if let Ok((run, _)) = hkcu.create_subkey("Software\\Microsoft\\Windows\\CurrentVersion\\Run") { if enabled { if let Ok(exe) = std::env::current_exe() { let _ = run.set_value("JARVIS", &format!("\"{}\" --hidden", exe.display())); } } else { let _ = run.delete_value("JARVIS"); } } }
#[cfg(not(windows))] fn sync_autostart(_: bool) {}
fn show_main(app: &tauri::AppHandle) { if let Some(window) = app.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); } }
fn show_overlay(app: &tauri::AppHandle) { if let Some(window) = app.get_webview_window("overlay") { let _ = window.show(); let _ = window.set_focus(); } let _ = app.emit("jarvis://hotkey", ()); }

fn main() {
    let settings = launcher_settings(); let hidden = std::env::args().any(|arg| arg == "--hidden");
    tauri::Builder::default().manage(BackendProcess(Mutex::new(None)))
        .plugin(tauri_plugin_shell::init()).plugin(tauri_plugin_opener::init()).plugin(tauri_plugin_dialog::init()).plugin(tauri_plugin_fs::init()).plugin(tauri_plugin_http::init()).plugin(tauri_plugin_notification::init()).plugin(tauri_plugin_process::init()).plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .setup(move |app| {
            let main = app.get_webview_window("main").expect("main window configured"); window_effects::setup_window_effects(&main); if hidden || settings.autostart.unwrap_or(false) { let _ = main.hide(); }
            WebviewWindowBuilder::new(app, "overlay", WebviewUrl::App("index.html".into())).title("JARVIS").inner_size(480.0, 48.0).center().decorations(false).transparent(true).always_on_top(true).skip_taskbar(true).visible(false).build()?;
            let open = MenuItem::with_id(app, "open", "Открыть", true, None::<&str>)?; let settings_item = MenuItem::with_id(app, "settings", "Настройки", true, None::<&str>)?; let debug = MenuItem::with_id(app, "debug", "Debug", true, None::<&str>)?; let quit = MenuItem::with_id(app, "quit", "Выход", true, None::<&str>)?; let menu = Menu::with_items(app, &[&open, &settings_item, &debug, &quit])?;
            TrayIconBuilder::new().icon(app.default_window_icon().expect("tray icon").clone()).menu(&menu).on_menu_event(|app, event| match event.id().as_ref() { "open" | "settings" | "debug" => show_main(app), "quit" => app.exit(0), _ => {} }).on_tray_icon_event(|tray, event| { if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = event { show_main(tray.app_handle()); } }).build(app)?;
            let shortcut = settings.hotkey.clone().unwrap_or_else(|| "Ctrl+Space".into()); let hotkey_app = app.handle().clone(); app.global_shortcut().on_shortcut(shortcut.as_str(), move |_, _, _| show_overlay(&hotkey_app))?;
            sync_autostart(settings.autostart.unwrap_or(false)); manage_backend(app.handle().clone(), settings.clone());
            // A missing profile is the one deliberate exception to tray-only
            // startup: after two quiet seconds, begin the first-meeting ritual.
            if !project_root().join("data/profile/profile.json").is_file() { let first_launch = app.handle().clone(); thread::spawn(move || { thread::sleep(Duration::from_secs(2)); show_main(&first_launch); }); }
            Ok(())
        })
        .on_window_event(|window, event| { if window.label() == "main" { if let tauri::WindowEvent::CloseRequested { api, .. } = event { api.prevent_close(); let _ = window.hide(); } } })
        .run(tauri::generate_context!()).expect("error while running JARVIS");
}
