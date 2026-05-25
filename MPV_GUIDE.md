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
| Ctrl + 1 | Upscaling Enabled |
| Ctrl + 2 | Upscaling Disabled |
| Space | Play / Pause |
| f | Toggle Fullscreen |

---

## Upscaling

Anicat uses **Anime4K CNN Mode A** shaders for GPU upscaling. These sharpen edges and reduce blur while running efficiently on Apple Silicon and Windows GPUs.

- **Ctrl+1** -- Enable upscaling (shows "Upscaling Enabled")
- **Ctrl+2** -- Disable upscaling (shows "Upscaling Disabled")

The default preset is applied automatically at playback start. You can change this in Settings > Player > Visual Quality.

### Manual Shader Override

The shaders loaded by **Ctrl+1** and at playback start are defined in:

**Bundle path:** `Anicat.app/Contents/Resources/resources/mpv_config/` (macOS) or `resources/mpv_config/` (Windows)

- `input.conf` -- the Ctrl+1/Ctrl+2 keybindings with the shader chain
- `scripts/anicat_ui/main.lua` -- programmatic `enable_shaders()` function (used by auto-start)

The shader files themselves are in `resources/mpv_config/shaders/`.

---

## Skip Intro / Outro

When an OP or ED is detected, a skip button appears. You can also press Ctrl+S to skip immediately. Enable Auto-skip in Settings to skip without the button.

---

## Volume & Language

- **Shift+T** cycles between sub and dub audio tracks.
- Adjust volume with your system volume keys or via the ModernZ on-screen controls.

---

## Compatibility

Anicat's bundled mpv is configured for macOS (using `videotoolbox-copy` hardware decoding) and Windows (using `d3d11va` hardware decoding), with smooth 24fps playback interpolation, and debanding. Everything is pre-configured — no manual mpv.conf editing needed.

If you prefer your own system mpv installation (e.g., from Homebrew or Chocolatey), select "External Player - MPV" in Settings > Player. Anicat will route streams to it with the same keyboard shortcuts.


---

## Further Customization
For even deeper customization, refer to the official [mpv manual](https://mpv.io/manual/stable/).
