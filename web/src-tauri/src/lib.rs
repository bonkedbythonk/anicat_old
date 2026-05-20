use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager,
};

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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_log::Builder::default().build())
        .invoke_handler(tauri::generate_handler![open_logs_folder])
        .setup(|app| {
            // Clean up any existing sidecar processes to avoid "Address already in use"
            #[cfg(target_os = "macos")]
            let _ = std::process::Command::new("pkill")
                .arg("-f")
                .arg("anicat-server")
                .output();

            // Setup Tray Menu
            let quit_i = MenuItem::with_id(app, "quit", "Quit Anicat", true, None::<&str>)?;
            let show_i = MenuItem::with_id(app, "show", "Show Dashboard", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_i, &quit_i])?;

            let tray_icon = tauri::image::Image::from_bytes(include_bytes!("../icons/tray-icon.png"))?;
            let _tray = TrayIconBuilder::new()
                .icon(tray_icon)
                .icon_as_template(true)
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "quit" => {
                        app.exit(0);
                    }
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    _ => {}
                })
                .build(app)?;

            // Spawn sidecar directly from the app bundle's MacOS directory.
            // Avoids Tauri v2 sidecar name/triple resolution issues.
            let exe_dir = std::env::current_exe()
                .ok()
                .and_then(|p| p.parent().map(|d| d.to_path_buf()));
            if let Some(bin_dir) = exe_dir {
                let sidecar_path = bin_dir.join("anicat-server");
                if sidecar_path.exists() {
                    match std::process::Command::new(&sidecar_path)
                        .stdout(std::process::Stdio::piped())
                        .stderr(std::process::Stdio::piped())
                        .spawn()
                    {
                        Ok(child) => {
                            app.manage(child);
                            log::info!("Sidecar started from: {}", sidecar_path.display());
                        }
                        Err(e) => {
                            log::error!("Failed to spawn sidecar from {}: {}", sidecar_path.display(), e);
                        }
                    }
                } else {
                    log::error!("Sidecar binary not found at: {}", sidecar_path.display());
                }
            } else {
                log::error!("Could not determine executable directory for sidecar launch");
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
