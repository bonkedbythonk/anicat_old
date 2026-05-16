use tauri::Manager;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .plugin(tauri_plugin_log::Builder::default().build())
    .setup(|app| {
      let shell = app.shell();
      let sidecar = shell.sidecar("anicat-server").unwrap();
      
      let (mut rx, child) = sidecar.spawn().expect("Failed to spawn sidecar");
      
      app.manage(child);

      tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
          match event {
            CommandEvent::Stdout(line) => {
              log::info!("sidecar-out: {}", String::from_utf8_lossy(&line).trim());
            }
            CommandEvent::Stderr(line) => {
              log::error!("sidecar-err: {}", String::from_utf8_lossy(&line).trim());
            }
            CommandEvent::Terminated(payload) => {
              log::warn!("sidecar-terminated: {:?}", payload);
            }
            _ => {}
          }
        }
      });

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
