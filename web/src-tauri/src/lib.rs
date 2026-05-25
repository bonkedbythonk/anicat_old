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

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[allow(unused_mut)]
fn create_command<S: AsRef<std::ffi::OsStr>>(program: S) -> std::process::Command {
    let mut cmd = std::process::Command::new(program);
    #[cfg(target_os = "windows")]
    {
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    cmd
}

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
        let sidecar_filename = if cfg!(windows) {
            "anicat-server.exe"
        } else {
            "anicat-server"
        };
        let sidecar_path = bin_dir.join(sidecar_filename);
        if sidecar_path.exists() {
            match create_command(&sidecar_path)
                .env("PYTHONIOENCODING", "utf-8")
                .env("PYTHONUTF8", "1")
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
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
        let python_bin = if cfg!(windows) {
            root.join(".venv").join("Scripts").join("python.exe")
        } else {
            root.join(".venv").join("bin").join("python3")
        };
        if python_bin.exists() {
            match create_command(&python_bin)
                .args(["-m", "uvicorn", "anicat_media.api.main:create_app", "--host", "127.0.0.1", "--port", "13370", "--factory"])
                .current_dir(root)
                .env("PYTHONIOENCODING", "utf-8")
                .env("PYTHONUTF8", "1")
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
                .spawn()
            {
                Ok(child) => {
                    log::info!("[sidecar] Dev server started (.venv)");
                    return Some(child);
                }
                Err(e) => log::error!("[sidecar] Dev server failed: {}", e),
            }
        } else {
            match create_command("uv")
                .args(["run", "uvicorn", "anicat_media.api.main:create_app", "--host", "127.0.0.1", "--port", "13370", "--factory"])
                .current_dir(root)
                .env("PYTHONIOENCODING", "utf-8")
                .env("PYTHONUTF8", "1")
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
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
    create_command("open")
        .arg(&log_path)
        .spawn()
        .map_err(|e| e.to_string())?;
        
    #[cfg(target_os = "windows")]
    create_command("explorer")
        .arg(&log_path)
        .spawn()
        .map_err(|e| e.to_string())?;

    #[cfg(target_os = "linux")]
    create_command("xdg-open")
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
    std::panic::set_hook(Box::new(|info| {
        eprintln!("--- RUST PANIC DETECTED ---");
        eprintln!("Panic info: {:?}", info);
        if let Some(s) = info.payload().downcast_ref::<&str>() {
            eprintln!("Panic payload (str): {}", s);
        }
        if let Some(s) = info.payload().downcast_ref::<String>() {
            eprintln!("Panic payload (String): {}", s);
        }
        if let Some(loc) = info.location() {
            eprintln!("Panic location: {}:{}:{}", loc.file(), loc.line(), loc.column());
        }
        eprintln!("---------------------------");
    }));

    let sidecar_state = SidecarState::new();
    let child_arc = sidecar_state.child.clone();
    let restart_count_arc = sidecar_state.restart_count.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_log::Builder::default().build())
        // UX-03: Global shortcut disabled on macOS 26 — the accessibility API
        // path changed, causing a hard crash. Re-enable once
        // tauri-plugin-global-shortcut supports macOS 26 natively.
        .manage(sidecar_state)
        .invoke_handler(tauri::generate_handler![open_logs_folder, restart_backend])
        .setup(move |app| {
            let setup_result = (|| -> Result<(), Box<dyn std::error::Error>> {
                // --- Clean up stale processes on port 13370 ---
                #[cfg(target_os = "macos")]
                {
                    // Kill any process holding port 13370 (stale sidecar from previous run)
                    let _ = create_command("sh")
                        .arg("-c")
                        .arg("lsof -ti :13370 | xargs kill -9 2>/dev/null; pkill -9 -f anicat-server 2>/dev/null; true")
                        .output();
                    // Brief pause to let the OS release the port
                    std::thread::sleep(std::time::Duration::from_millis(500));
                }

                #[cfg(target_os = "windows")]
                {
                    // Kill any stale sidecar from previous run using taskkill
                    let _ = create_command("cmd")
                        .args(["/C", "taskkill /F /IM anicat-server.exe /T 2>nul"])
                        .output();
                    std::thread::sleep(std::time::Duration::from_millis(500));
                }

                // ── macOS 26 note: WKWebView may log "web content process terminated"
                //    during startup — this is normal process-pool lifecycle on macOS 26
                //    and does NOT indicate a crash. The webview auto-recovers. ──
                log::info!("[setup] macOS 26 detected — WKWebView process lifecycle messages are normal");

                // ── UX-01: Full macOS Menu Bar ──
                #[cfg(target_os = "macos")]
                {
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
                }

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

                        // Kill any lingering processes on port 13370 before restarting.
                        // The PyInstaller sidecar spawns a child that may outlive the
                        // parent, keeping the port occupied.
                        #[cfg(target_os = "macos")]
                        {
                            let _ = create_command("sh")
                                .arg("-c")
                                .arg("lsof -ti :13370 | xargs kill -9 2>/dev/null; true")
                                .output();
                            std::thread::sleep(std::time::Duration::from_millis(800));
                        }

                        #[cfg(target_os = "windows")]
                        {
                            let _ = create_command("cmd")
                                .args(["/C", "taskkill /F /IM anicat-server.exe /T 2>nul"])
                                .output();
                            std::thread::sleep(std::time::Duration::from_millis(800));
                        }

                        log::info!("[sidecar] Restarting (attempt {})...", restart_wd.lock().unwrap());
                        if let Some(new_child) = spawn_backend() {
                            *child_wd.lock().unwrap() = Some(new_child);
                            log::info!("[sidecar] Backend restarted");
                        } else {
                            log::error!("[sidecar] Failed to restart");
                        }
                    }
                });

                // --- Startup safety net: reload main window if the page failed to load ---
                // On macOS 26, WKWebView may show its built-in error page ("This page
                // couldn't load") if the initial web content process crashes before the
                // auto-recovery handler can act. This delayed reload ensures the app
                // recovers even when the built-in handler misses the event.
                let app_handle_reload = app.handle().clone();
                thread::spawn(move || {
                    thread::sleep(std::time::Duration::from_secs(4));
                    if let Some(main_window) = app_handle_reload.get_webview_window("main") {
                        // Try a benign eval to see if our page actually loaded.
                        // If the webview is showing the WKWebView error page, eval
                        // will still succeed but the title won't match.
                        let eval_result = main_window.eval(
                            "document.title === 'anicat' ? 'ok' : 'error-page'"
                        );
                        match eval_result {
                            Ok(_) => {
                                // eval succeeded — the webview is alive. The JS will
                                // have run and we'll get the result back asynchronously.
                                // We rely on the auto-recovery handler for actual recovery;
                                // this is just a safety check.
                            }
                            Err(_) => {
                                log::warn!("[recovery] Main window eval failed — attempting reload");
                                let _ = main_window.eval("location.reload()");
                            }
                        }
                    }
                });

                log::info!("Anicat started successfully — frontend + backend are live");
                Ok(())
            })();

            if let Err(ref e) = setup_result {
                eprintln!("[setup] CRITICAL ERROR IN TAURI SETUP: {:?}", e);
                log::error!("[setup] CRITICAL ERROR IN TAURI SETUP: {:?}", e);
            }
            setup_result
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
