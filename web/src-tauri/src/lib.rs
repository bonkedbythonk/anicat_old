// UX-01: Full macOS menu bar with standard items + keyboard shortcuts
use tauri::{
    menu::{
        MenuBuilder, MenuItemBuilder, SubmenuBuilder,
        PredefinedMenuItem,
    },
    tray::TrayIconBuilder,
    Manager,
};
use std::sync::{Arc, Mutex};
use std::thread;

// ---------------------------------------------------------------------------
// Shared sidecar state
// ---------------------------------------------------------------------------

struct SidecarState {
    child: Arc<Mutex<Option<std::process::Child>>>,
    restart_count: Arc<Mutex<u32>>,
}

impl SidecarState {
    fn new() -> Self {
        Self {
            child: Arc::new(Mutex::new(None)),
            restart_count: Arc::new(Mutex::new(0)),
        }
    }
}

// ---------------------------------------------------------------------------
// Spawn backend — tries bundled binary first, falls back to dev mode
// ---------------------------------------------------------------------------

fn spawn_backend() -> Option<std::process::Child> {
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()));

    // --- Try bundled sidecar (production .app) ---
    if let Some(ref bin_dir) = exe_dir {
        let sidecar_path = bin_dir.join("anicat-server");
        if sidecar_path.exists() {
            match std::process::Command::new(&sidecar_path)
                .stdout(std::process::Stdio::piped())
                .stderr(std::process::Stdio::piped())
                .spawn()
            {
                Ok(child) => {
                    log::info!("[sidecar] Bundled binary: {}", sidecar_path.display());
                    return Some(child);
                }
                Err(e) => {
                    log::error!("[sidecar] Bundled binary failed: {} — {}", sidecar_path.display(), e);
                }
            }
        }
    }

    // --- Dev fallback: find project root and use uv run uvicorn ---
    let project_dir = find_project_root();
    if let Some(ref root) = project_dir {
        let python_bin = root.join(".venv/bin/python3");
        if python_bin.exists() {
            match std::process::Command::new(&python_bin)
                .args(["-m", "uvicorn", "anicat_media.api.main:create_app", "--host", "127.0.0.1", "--port", "13370", "--factory"])
                .current_dir(root)
                .stdout(std::process::Stdio::piped())
                .stderr(std::process::Stdio::piped())
                .spawn()
            {
                Ok(child) => {
                    log::info!("[sidecar] Dev server started (.venv)");
                    return Some(child);
                }
                Err(e) => log::error!("[sidecar] Dev server failed: {}", e),
            }
        } else {
            match std::process::Command::new("uv")
                .args(["run", "uvicorn", "anicat_media.api.main:create_app", "--host", "127.0.0.1", "--port", "13370", "--factory"])
                .current_dir(root)
                .stdout(std::process::Stdio::piped())
                .stderr(std::process::Stdio::piped())
                .spawn()
            {
                Ok(child) => {
                    log::info!("[sidecar] Dev server started (uv run)");
                    return Some(child);
                }
                Err(e) => log::error!("[sidecar] Dev server (uv run) failed: {}", e),
            }
        }
    } else {
        log::error!("[sidecar] Could not find project root for dev fallback");
    }

    None
}

/// Walk up from the executable to find the project root (pyproject.toml + anicat_media/).
fn find_project_root() -> Option<std::path::PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let mut dir = exe.parent()?.to_path_buf();

    for _ in 0..8 {
        if dir.join("pyproject.toml").exists() && dir.join("anicat_media").is_dir() {
            return Some(dir);
        }
        if !dir.pop() {
            break;
        }
    }

    if let Ok(cwd) = std::env::current_dir() {
        if cwd.join("pyproject.toml").exists() && cwd.join("anicat_media").is_dir() {
            return Some(cwd);
        }
    }

    None
}

// ---------------------------------------------------------------------------
// Existing commands
// ---------------------------------------------------------------------------

#[tauri::command]
async fn open_logs_folder(app: tauri::AppHandle) -> Result<(), String> {
    let log_path = app.path().app_log_dir().map_err(|e| e.to_string())?;
    
    // Create directory if it doesn't exist
    if !log_path.exists() {
        std::fs::create_dir_all(&log_path).map_err(|e| e.to_string())?;
    }
    
    #[cfg(target_os = "macos")]
    std::process::Command::new("open")
        .arg(&log_path)
        .spawn()
        .map_err(|e| e.to_string())?;
        
    #[cfg(target_os = "windows")]
    std::process::Command::new("explorer")
        .arg(&log_path)
        .spawn()
        .map_err(|e| e.to_string())?;

    #[cfg(target_os = "linux")]
    std::process::Command::new("xdg-open")
        .arg(&log_path)
        .spawn()
        .map_err(|e| e.to_string())?;

    Ok(())
}

// ---------------------------------------------------------------------------
// Tauri command: restart the backend sidecar
// ---------------------------------------------------------------------------

#[tauri::command]
fn restart_backend(state: tauri::State<'_, SidecarState>) -> Result<String, String> {
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;
    let mut restart_guard = state.restart_count.lock().map_err(|e| e.to_string())?;

    if let Some(ref mut child) = *child_guard {
        let _ = child.kill();
        let _ = child.wait();
        log::info!("[sidecar] Killed backend for restart");
    }

    *restart_guard = 0;
    *child_guard = None;
    log::info!("[sidecar] Restart requested — watchdog will respawn");
    Ok("Backend restart initiated".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let sidecar_state = SidecarState::new();
    let child_arc = sidecar_state.child.clone();
    let restart_count_arc = sidecar_state.restart_count.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_log::Builder::default().build())
        // UX-03: Global shortcut disabled on macOS 26 — the accessibility API
        // path changed, causing a hard crash. Re-enable once
        // tauri-plugin-global-shortcut supports macOS 26 natively.
        .manage(sidecar_state)
        .invoke_handler(tauri::generate_handler![open_logs_folder, restart_backend])
        .setup(move |app| {
            // --- Clean up stale processes ---
            #[cfg(target_os = "macos")]
            let _ = std::process::Command::new("pkill")
                .arg("-f")
                .arg("anicat-server")
                .output();

            // ── UX-01: Full macOS Menu Bar ──
            let app_menu = SubmenuBuilder::new(app, "Anicat")
                .item(&PredefinedMenuItem::about(app, Some("About Anicat"), None)?)
                .separator()
                .item(&MenuItemBuilder::with_id("preferences", "Preferences...")
                    .accelerator("CmdOrCtrl+,")
                    .build(app)?)
                .separator()
                .item(&PredefinedMenuItem::services(app, None)?)
                .separator()
                .item(&PredefinedMenuItem::hide(app, Some("Hide Anicat"))?)
                .item(&PredefinedMenuItem::hide_others(app, Some("Hide Others"))?)
                .item(&PredefinedMenuItem::show_all(app, Some("Show All"))?)
                .separator()
                .item(&PredefinedMenuItem::quit(app, Some("Quit Anicat"))?)
                .build()?;

            let file_menu = SubmenuBuilder::new(app, "File")
                .item(&MenuItemBuilder::with_id("close_window", "Close Window")
                    .accelerator("CmdOrCtrl+W")
                    .build(app)?)
                .build()?;

            let edit_menu = SubmenuBuilder::new(app, "Edit")
                .item(&PredefinedMenuItem::undo(app, Some("Undo"))?)
                .item(&PredefinedMenuItem::redo(app, Some("Redo"))?)
                .separator()
                .item(&PredefinedMenuItem::cut(app, Some("Cut"))?)
                .item(&PredefinedMenuItem::copy(app, Some("Copy"))?)
                .item(&PredefinedMenuItem::paste(app, Some("Paste"))?)
                .item(&PredefinedMenuItem::select_all(app, Some("Select All"))?)
                .build()?;

            let view_menu = SubmenuBuilder::new(app, "View")
                .item(&MenuItemBuilder::with_id("toggle_fullscreen", "Toggle Full Screen")
                    .accelerator("Ctrl+Cmd+F")
                    .build(app)?)
                .item(&MenuItemBuilder::with_id("toggle_sidebar", "Toggle Sidebar")
                    .accelerator("CmdOrCtrl+B")
                    .build(app)?)
                .separator()
                .item(&MenuItemBuilder::with_id("nav_home", "Home")
                    .accelerator("CmdOrCtrl+1")
                    .build(app)?)
                .item(&MenuItemBuilder::with_id("nav_search", "Search")
                    .accelerator("CmdOrCtrl+K")
                    .build(app)?)
                .item(&MenuItemBuilder::with_id("nav_library", "Library")
                    .accelerator("CmdOrCtrl+2")
                    .build(app)?)
                .item(&MenuItemBuilder::with_id("nav_schedule", "Schedule")
                    .accelerator("CmdOrCtrl+3")
                    .build(app)?)
                .build()?;

            let help_menu = SubmenuBuilder::new(app, "Help")
                .item(&MenuItemBuilder::with_id("keyboard_shortcuts", "Keyboard Shortcuts")
                    .accelerator("CmdOrCtrl+?")
                    .build(app)?)
                .build()?;

            let menu = MenuBuilder::new(app)
                .item(&app_menu)
                .item(&file_menu)
                .item(&edit_menu)
                .item(&view_menu)
                .item(&help_menu)
                .build()?;

            app.set_menu(menu)?;

            // Handle menu events
            let app_handle = app.handle().clone();
            app.on_menu_event(move |_app, event| {
                match event.id().as_ref() {
                    "preferences" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.eval("window.__anicat_navigate__ && window.__anicat_navigate__('settings')");
                        }
                    }
                    "nav_home" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.eval("window.__anicat_navigate__ && window.__anicat_navigate__('home')");
                        }
                    }
                    "nav_search" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.eval("window.__anicat_navigate__ && window.__anicat_navigate__('search')");
                        }
                    }
                    "nav_library" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.eval("window.__anicat_navigate__ && window.__anicat_navigate__('library')");
                        }
                    }
                    "nav_schedule" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.eval("window.__anicat_navigate__ && window.__anicat_navigate__('schedule')");
                        }
                    }
                    "keyboard_shortcuts" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.eval("window.__anicat_toggle_help__ && window.__anicat_toggle_help__()");
                        }
                    }
                    "toggle_fullscreen" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let is_fullscreen = window.is_fullscreen().unwrap_or(false);
                            let _ = window.set_fullscreen(!is_fullscreen);
                        }
                    }
                    "close_window" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.close();
                        }
                    }
                    _ => {}
                }
            });

            // ── UX-03: Global Shortcut disabled on macOS 26 ──
            // The accessibility API path changed in macOS 26, causing
            // a hard crash when initializing the global-shortcut plugin.
            // Quick Pane can still be toggled via the tray menu.
            log::info!("[plugins] Global shortcut disabled on macOS 26. Quick Pane requires manual activation.");

            // ── UX-03: Quick Pane floating window ──
            let qp_config = tauri::WebviewUrl::App("quick-pane.html".into());
            let _quick_pane = tauri::WebviewWindowBuilder::new(
                app,
                "quick-pane",
                qp_config,
            )
            .title("Quick Pane")
            .inner_size(340.0, 480.0)
            .resizable(false)
            .decorations(false)
            .always_on_top(true)
            .visible(false)
            .skip_taskbar(true)
            .build()?;

            // ── Tray Menu ──
            let quit_i = MenuItemBuilder::with_id("quit", "Quit Anicat")
                .build(app)?;
            let show_i = MenuItemBuilder::with_id("show", "Show Dashboard")
                .build(app)?;
            let tray_menu = MenuBuilder::new(app)
                .item(&show_i)
                .item(&quit_i)
                .build()?;

            let tray_icon = tauri::image::Image::from_bytes(include_bytes!("../icons/tray-icon.png"))?;
            let _tray = TrayIconBuilder::new()
                .icon(tray_icon)
                .icon_as_template(true)
                .menu(&tray_menu)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "quit" => app.exit(0),
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    _ => {}
                })
                .build(app)?;

            // --- Spawn backend ---
            if let Some(child) = spawn_backend() {
                *child_arc.lock().unwrap() = Some(child);
                log::info!("[sidecar] Backend started");
            } else {
                log::error!("[sidecar] Failed to start backend");
            }

            // --- Watchdog: monitors and restarts backend on crash ---
            let child_wd = child_arc.clone();
            let restart_wd = restart_count_arc.clone();
            let _app_handle = app.handle().clone();

            thread::spawn(move || loop {
                thread::sleep(std::time::Duration::from_secs(2));

                let should_restart = {
                    let mut guard = child_wd.lock().unwrap();
                    match guard.as_mut() {
                        Some(child) => match child.try_wait() {
                            Ok(Some(status)) => {
                                log::warn!("[sidecar] Backend exited: {:?}", status);
                                *guard = None;
                                true
                            }
                            Ok(None) => false,
                            Err(e) => {
                                log::error!("[sidecar] Error checking backend: {}", e);
                                *guard = None;
                                true
                            }
                        },
                        None => true,
                    }
                };

                if should_restart {
                    let mut rc = restart_wd.lock().unwrap();
                    if *rc >= 5 {
                        log::error!("[sidecar] {} crashes — giving up", *rc);
                        break;
                    }
                    *rc += 1;
                    drop(rc);

                    log::info!("[sidecar] Restarting (attempt {})...", restart_wd.lock().unwrap());
                    if let Some(new_child) = spawn_backend() {
                        *child_wd.lock().unwrap() = Some(new_child);
                        log::info!("[sidecar] Backend restarted");
                    } else {
                        log::error!("[sidecar] Failed to restart");
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
