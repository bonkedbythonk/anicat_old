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
| Ctrl + 1 | Upscaling: Mode A (Balanced — light CNN) |
| Ctrl + 2 | Upscaling: OFF |
| Ctrl + 3 | Upscaling: Mode C (HQ + Denoise) |
| Ctrl + 4 | Upscaling: Mode A+A (Maximum sharpness) |
| Ctrl + 0 | Upscaling: OFF (alternate) |
| Space | Play / Pause |
| f | Toggle Fullscreen |

---

## Upscaling

Anicat uses **Anime4K CNN shaders** for high-quality GPU upscaling. Multiple presets let you balance quality and performance.

| Preset | Shortcut | Description |
| :--- | :--- | :--- |
| **Mode A (Balanced)** | Ctrl+1 | Restore_CNN_L + Upscale_CNN_x2_L — light CNN, great for 720p->1080p |
| **Mode C (HQ+Denoise)** | Ctrl+3 | Upscale_Denoise_CNN_x2_VL + Upscale_CNN_x2_M — adds denoising for cleaner output |
| **Mode A+A (Maximum)** | Ctrl+4 | Dual-pass CNN (VL + M) — sharpest quality, heaviest GPU load |
| **OFF** | Ctrl+2 / Ctrl+0 | Clears all shaders |

The default preset applied at playback start is **Mode A (Balanced)**. You can change this in Settings > Player > Visual Quality.

### Manual Shader Override

If you want to use different shaders, the presets are defined in:

**Bundle path:** `Anicat.app/Contents/Resources/resources/mpv_config/`

- `input.conf` — all preset keybindings with their shader chains
- `scripts/anicat_ui/main.lua` — programmatic `enable_shaders()` function (used by auto-start)

The shader files themselves are in `resources/mpv_config/shaders/`. To swap a preset's shaders, edit the `glsl-shaders` list in `input.conf` under the desired Ctrl+N binding.

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
