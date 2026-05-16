# MPV Customization Guide

Anicat uses the powerful **mpv** media player for high-performance playback. This guide will help you unlock its full potential with shaders, skins, and power-user shortcuts.

---

## Keyboard Shortcuts

Anicat synchronizes your progress automatically when you use these shortcuts.

| Command | Action |
| :--- | :--- |
| Shift + N | **Play Next Episode** |
| Shift + P | Play Previous Episode |
| Shift + R | Reload Current Episode |
| Shift + A | Toggle Auto-play |
| Shift + T | Toggle Dub / Sub |
| Space | Play / Pause |
| f | Toggle Fullscreen |

---

## Modern UI Skin (Recommended)

The default mpv interface is functional but basic. We highly recommend installing a modern "On-Screen Controller" (OSC).

### [ModernX](https://github.com/cyl0/ModernX)
A sleek, minimal, and feature-rich OSC that matches the Anicat aesthetic perfectly.

### [uosc](https://github.com/tomasklaen/uosc)
A minimalist, proximity-based UI that stays out of your way until you need it.

---

## High-Quality Shaders (Anime4K)

Anime4K is a set of open-source real-time anime upscaling algorithms that significantly improve visual quality.

### Installation
1.  Download the shaders from [Anime4K GitHub](https://github.com/bloc97/Anime4K).
2.  Place the `.glsl` files in `~/.config/mpv/shaders/`.
3.  Configure your `mpv.conf` (~/.config/mpv/mpv.conf) based on your hardware:

### Hardware Tiers

#### Tier 1: Low-End (Base M1/M2/M3, Intel iGPU)
```conf
glsl-shaders="~/.config/mpv/shaders/Anime4K_Upscale_CNN_M_x2_Fast.glsl"
```

#### Tier 2: Mid-Range (M1 Pro/Max, RTX 3060)
```conf
glsl-shaders="~/.config/mpv/shaders/Anime4K_Upscale_CNN_L_x2_HQ.glsl;~/.config/mpv/shaders/Anime4K_Auto_Restore_VL.glsl"
```

#### Tier 3: High-End (M2/M3 Max/Ultra, RTX 4080+)
```conf
glsl-shaders="~/.config/mpv/shaders/Anime4K_Upscale_CNN_UL_x2_Thin.glsl;~/.config/mpv/shaders/Anime4K_Restore_CNN_UL.glsl"
```

---

## Further Customization
For even deeper customization, refer to the official [mpv manual](https://mpv.io/manual/stable/).
