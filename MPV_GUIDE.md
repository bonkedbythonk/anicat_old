# MPV Customization Guide

Anicat bundles a standalone **mpv** player for high-performance playback with GPU upscaling, modern controls, and automatic skip detection. This guide covers the keyboard shortcuts and how everything works out of the box.

---

## Keyboard Shortcuts

Anicat synchronizes your progress automatically when you use these shortcuts.

| Command | Action |
| :--- | :--- |
| Shift + N | Play Next Episode |
| Shift + P | Play Previous Episode |
| Shift + R | Reload Current Episode |
| Shift + A | Toggle Auto-play |
| Shift + T | Toggle Dub / Sub |
| Ctrl + S | Skip Intro / Active Segment |
| Ctrl + 1 | Enable Upscaling |
| Ctrl + 2 | Disable Upscaling |
| Space | Play / Pause |
| f | Toggle Fullscreen |

---

## Upscaling

Anicat enables lightweight GPU upscaling by default using non-CNN Anime4K shaders. These sharpen edges and reduce blur without the heavy GPU load of neural network shaders.

- **Ctrl+1** — enable upscaling (shows a brief "Upscaling: ON" message)
- **Ctrl+2** — disable upscaling (shows "Upscaling: OFF")

You can change the default behavior in Settings > Player > Visual Quality.

### Manual Shader Override

If you want to use different shaders (e.g., the heavier CNN-based ones for better quality), edit the shader list in:

**Bundle path:** `Anicat.app/Contents/Resources/resources/mpv_config/shaders/`

The shaders loaded by `Ctrl+1` and by default are defined in:
- `web/src-tauri/resources/mpv_config/input.conf` (fallback bindings)
- `web/src-tauri/resources/mpv_config/scripts/anicat_ui/main.lua` (primary bindings)

---

## Skip Intro / Outro

When an OP or ED is detected, a skip button appears. You can also press Ctrl+S to skip immediately. Enable Auto-skip in Settings to skip without the button.

---

## Volume & Language

- **Shift+T** cycles between sub and dub audio tracks.
- Adjust volume with your system volume keys or via the ModernZ on-screen controls.

---

## Compatibility

Anicat's bundled mpv is configured for macOS with hardware decoding (`videotoolbox-copy`), smooth 24fps playback interpolation, and debanding. Everything is pre-configured — no manual mpv.conf editing needed.

If you prefer your own system mpv installation (e.g., from Homebrew), select "External Player - MPV" in Settings > Player. Anicat will route streams to it with the same keyboard shortcuts.


---

## Further Customization
For even deeper customization, refer to the official [mpv manual](https://mpv.io/manual/stable/).
