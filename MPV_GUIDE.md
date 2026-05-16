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

The default mpv interface is basic. We highly recommend installing **[ModernX](https://github.com/cyl0/ModernX)** for a premium macOS-native feel.

### Step-by-Step Installation

1.  **Create the Scripts folder**:
    Open your Terminal and run:
    ```bash
    mkdir -p ~/.config/mpv/scripts
    ```
2.  **Download the Skin**:
    Go to the [ModernX Releases](https://github.com/cyl0/ModernX/releases) and download the `modernx.lua` file.
3.  **Place the file**:
    Move `modernx.lua` into the `~/.config/mpv/scripts/` folder you just created.
4.  **Restart MPV**:
    Close any open videos and play a new one. You should see the new sleek interface!

---

## High-Quality Shaders (Anime4K)

Anime4K uses your GPU to upscale anime in real-time, making it look crisp on high-resolution screens.

### Installation

1.  **Create the Shaders folder**:
    Open Terminal and run:
    ```bash
    mkdir -p ~/.config/mpv/shaders
    ```
2.  **Download Shaders**:
    Download the `.glsl` files from the [Anime4K GitHub](https://github.com/bloc97/Anime4K/releases).
3.  **Place the files**:
    Move all the downloaded `.glsl` files into `~/.config/mpv/shaders/`.
4.  **Configure MPV**:
    You need to tell MPV to use these shaders. Create or edit your config file:
    ```bash
    nano ~/.config/mpv/mpv.conf
    ```
    Copy and paste **one** of the following blocks based on your Mac:

### Hardware Settings for mpv.conf

#### Tier 1: Low-End (Base M1/M2/M3, MacBook Air, Intel iGPU)
```conf
# Add to mpv.conf
glsl-shaders="~/.config/mpv/shaders/Anime4K_Upscale_CNN_M_x2_Fast.glsl"
```

#### Tier 2: Mid-Range (M1/M2 Pro, RTX 3060)
```conf
# Add to mpv.conf
glsl-shaders="~/.config/mpv/shaders/Anime4K_Upscale_CNN_L_x2_HQ.glsl;~/.config/mpv/shaders/Anime4K_Auto_Restore_VL.glsl"
```

#### Tier 3: High-End (M1/M2/M3 Max/Ultra, Dedicated GPU)
```conf
# Add to mpv.conf
glsl-shaders="~/.config/mpv/shaders/Anime4K_Upscale_CNN_UL_x2_Thin.glsl;~/.config/mpv/shaders/Anime4K_Restore_CNN_UL.glsl"
```

---

## Folder Structure Reference
When finished, your configuration should look exactly like this:
```text
~/.config/mpv/
├── mpv.conf (your settings)
├── scripts/
│   └── modernx.lua (the skin)
└── shaders/
    └── Anime4K_... .glsl (the shaders)
```


---

## Further Customization
For even deeper customization, refer to the official [mpv manual](https://mpv.io/manual/stable/).
