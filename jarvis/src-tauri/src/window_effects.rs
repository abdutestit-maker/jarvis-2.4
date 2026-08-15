/**
 * J.A.R.V.I.S. v3.0 — Window Effects (Rust)
 * Acrylic/Mica/Vibrancy for transparent frameless windows
 * Plus window control commands
 */

use tauri::{Manager, Runtime, WebviewWindow};

#[cfg(target_os = "windows")]
use window_vibrancy::{apply_acrylic, apply_mica};
#[cfg(target_os = "macos")]
use window_vibrancy::apply_vibrancy;
#[cfg(target_os = "linux")]
use window_vibrancy::apply_blur;

#[cfg(target_os = "windows")]
fn setup_windows_effects<R: Runtime>(window: &WebviewWindow<R>) {
    // Try Acrylic first (Windows 11), fallback to Mica (Windows 10/11)
    if apply_acrylic(window, None).is_err() {
        let _ = apply_mica(window, None);
    }
}

#[cfg(target_os = "macos")]
fn setup_macos_effects<R: Runtime>(window: &WebviewWindow<R>) {
    let _ = apply_vibrancy(window, None);
}

#[cfg(target_os = "linux")]
fn setup_linux_effects<R: Runtime>(window: &WebviewWindow<R>) {
    let _ = apply_blur(window, None);
}

pub fn setup_window_effects<R: Runtime>(window: &WebviewWindow<R>) {
    #[cfg(target_os = "windows")]
    setup_windows_effects(window);

    #[cfg(target_os = "macos")]
    setup_macos_effects(window);

    #[cfg(target_os = "linux")]
    setup_linux_effects(window);
}

#[tauri::command]
async fn set_window_effect<R: Runtime>(window: WebviewWindow<R>, effect: String) -> Result<(), String> {
    match effect.as_str() {
        "acrylic" => {
            #[cfg(target_os = "windows")]
            return apply_acrylic(&window, None).map_err(|e| e.to_string());
            #[cfg(not(target_os = "windows"))]
            return Err("Acrylic only available on Windows".into());
        }
        "mica" => {
            #[cfg(target_os = "windows")]
            return apply_mica(&window, None).map_err(|e| e.to_string());
            #[cfg(not(target_os = "windows"))]
            return Err("Mica only available on Windows".into());
        }
        "vibrancy" => {
            #[cfg(target_os = "macos")]
            return apply_vibrancy(&window, None).map_err(|e| e.to_string());
            #[cfg(not(target_os = "macos"))]
            return Err("Vibrancy only available on macOS".into());
        }
        "linux-blur" => {
            #[cfg(target_os = "linux")]
            return apply_blur(&window, None).map_err(|e| e.to_string());
            #[cfg(not(target_os = "linux"))]
            return Err("Linux blur only available on Linux".into());
        }
        "none" => Ok(()),
        _ => Err("Unknown effect".into()),
    }
}

#[tauri::command]
async fn window_minimize<R: Runtime>(window: WebviewWindow<R>) -> Result<(), String> {
    window.minimize().map_err(|e| e.to_string())
}

#[tauri::command]
async fn window_maximize<R: Runtime>(window: WebviewWindow<R>) -> Result<(), String> {
    window.maximize().map_err(|e| e.to_string())
}

#[tauri::command]
async fn window_close<R: Runtime>(window: WebviewWindow<R>) -> Result<(), String> {
    window.close().map_err(|e| e.to_string())
}

#[tauri::command]
async fn backend_send_message(text: String, files: Vec<String>) -> Result<(), String> {
    // CONNECT BACKEND HERE: forward to Python/Rust backend
    println!("Backend message: {} files: {:?}", text, files);
    Ok(())
}

#[tauri::command]
async fn backend_interrupt() -> Result<(), String> {
    // CONNECT BACKEND HERE: interrupt running task
    println!("Backend interrupt");
    Ok(())
}

#[tauri::command]
async fn backend_request_vitals() -> Result<(), String> {
    // CONNECT BACKEND HERE: request vitals update
    println!("Backend vitals request");
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            set_window_effect,
            window_minimize,
            window_maximize,
            window_close,
            backend_send_message,
            backend_interrupt,
            backend_request_vitals,
        ])
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                setup_window_effects(&window);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
