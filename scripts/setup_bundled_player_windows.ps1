# setup_bundled_player_windows.ps1
# Automates downloading, extracting, and configuring the portable MPV player for AniCat on Windows.
#
# Requires: PowerShell 5.1+, 7z (7-Zip) in PATH

$ErrorActionPreference = "Stop"

$ResourcesDir = "web\src-tauri\resources"
$ConfigDir = "$ResourcesDir\mpv_config"

Write-Host "=== 1. Locating latest Windows MPV portable build ==="

# Use shinchiro's mpv-winbuild releases (the standard Windows MPV distribution)
$MpvReleasesUrl = "https://api.github.com/repos/shinchiro/mpv-winbuild/releases/latest"

try {
    $ReleaseJson = Invoke-RestMethod -Uri $MpvReleasesUrl -TimeoutSec 30
} catch {
    Write-Host "GitHub API failed, trying SourceForge fallback..."
    # Fallback: download from SourceForge
    $SfUrl = "https://sourceforge.net/projects/mpv-player-windows/files/latest/download"
    $MpvZip = "$env:TEMP\mpv-windows.7z"
    Invoke-WebRequest -Uri $SfUrl -OutFile $MpvZip -TimeoutSec 120
    $UseSourceForge = $true
}

if (-not $UseSourceForge) {
    # Find the 64-bit portable 7z asset
    $Asset = $ReleaseJson.assets | Where-Object {
        $_.name -match "mpv-x86_64.*\.7z" -and $_.name -notmatch "installer|setup|symbols|pdbs"
    } | Select-Object -First 1

    if (-not $Asset) {
        Write-Host "ERROR: Could not find a portable MPV 64-bit asset in the release."
        exit 1
    }

    Write-Host "Found: $($Asset.name) ($($Asset.size) bytes)"
    Write-Host "=== 2. Downloading portable MPV ==="
    $MpvZip = "$env:TEMP\mpv-windows.7z"
    Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $MpvZip -TimeoutSec 120
}

Write-Host "=== 3. Creating resources directory and extracting MPV ==="
New-Item -ItemType Directory -Force -Path $ResourcesDir | Out-Null

$TmpExtract = "$env:TEMP\mpv_extract"
Remove-Item -Recurse -Force $TmpExtract -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $TmpExtract | Out-Null

# Extract with 7-Zip
& 7z x "$MpvZip" -o"$TmpExtract" -y | Out-Null

# Find the extracted mpv directory (it'll be something like "mpv-x86_64-20250101")
$MpvDir = Get-ChildItem -Path $TmpExtract -Directory | Select-Object -First 1
if (-not $MpvDir) {
    Write-Host "ERROR: Could not find extracted MPV directory."
    exit 1
}

Write-Host "Copying MPV binary and libraries..."
# Copy mpv.exe and all DLLs
Copy-Item "$($MpvDir.FullName)\mpv.exe" -Destination "$ResourcesDir\mpv.exe" -Force
Get-ChildItem "$($MpvDir.FullName)\*.dll" | ForEach-Object {
    Copy-Item $_.FullName -Destination "$ResourcesDir\" -Force
}

Write-Host "=== 4. Setting up isolated themed configuration directories ==="
New-Item -ItemType Directory -Force -Path "$ConfigDir\scripts" | Out-Null
New-Item -ItemType Directory -Force -Path "$ConfigDir\scripts\anicat_ui" | Out-Null
New-Item -ItemType Directory -Force -Path "$ConfigDir\script-opts" | Out-Null
New-Item -ItemType Directory -Force -Path "$ConfigDir\shaders" | Out-Null

Write-Host "=== 5. Fetching ModernZ On-Screen Controller ==="
$ModernzZip = "$env:TEMP\modernz.zip"
Invoke-WebRequest -Uri "https://github.com/Samillion/ModernZ/archive/refs/heads/main.zip" -OutFile $ModernzZip -TimeoutSec 60
Expand-Archive -Path $ModernzZip -DestinationPath "$env:TEMP\modernz_repo" -Force
Copy-Item "$env:TEMP\modernz_repo\ModernZ-main\modernz.lua" -Destination "$ConfigDir\scripts\modernz.lua" -Force
New-Item -ItemType Directory -Force -Path "$ConfigDir\fonts" | Out-Null
Copy-Item "$env:TEMP\modernz_repo\ModernZ-main\modernz-icons.ttf" -Destination "$ConfigDir\fonts\modernz-icons.ttf" -Force
Remove-Item -Recurse -Force "$env:TEMP\modernz_repo" -ErrorAction SilentlyContinue
Remove-Item -Force $ModernzZip -ErrorAction SilentlyContinue

Write-Host "=== 6. Fetching Anime4K real-time upscaling shaders ==="
$Anime4kZip = "$env:TEMP\anime4k.zip"
Invoke-WebRequest -Uri "https://github.com/bloc97/Anime4K/releases/download/v4.0.1/Anime4K_v4.0.zip" -OutFile $Anime4kZip -TimeoutSec 60
Expand-Archive -Path $Anime4kZip -DestinationPath "$env:TEMP\anime4k_extract" -Force
Get-ChildItem -Path "$env:TEMP\anime4k_extract" -Recurse -Filter "*.glsl" | ForEach-Object {
    Copy-Item $_.FullName -Destination "$ConfigDir\shaders\" -Force
}
Remove-Item -Recurse -Force "$env:TEMP\anime4k_extract" -ErrorAction SilentlyContinue
Remove-Item -Force $Anime4kZip -ErrorAction SilentlyContinue

Write-Host "=== 7. Generating customized mpv.conf styled for AniCat ==="
@"
# Video Quality Settings
vo=gpu
profile=high-quality
hwdec=auto-safe

# Complete Borderless Minimalism
border=no
osc=no
osd-level=1
osd-on-seek=no
osd-bar=no

# Playback
# Show last frame instead of black screen when episode ends
keep-open=yes
# Remember volume, position, and other settings between launches
save-position-on-quit=yes

# Subtitles
sub-auto=fuzzy
sub-font="Segoe UI"
sub-font-size=44
sub-bold=yes
"@ | Out-File -FilePath "$ConfigDir\mpv.conf" -Encoding utf8

Write-Host "=== 8. Copying overlay and keybindings from pre-configured files ==="
if (-not (Test-Path "$ConfigDir\scripts\anicat_ui\main.lua")) {
    Copy-Item "$ResourcesDir\mpv_config\scripts\anicat_ui\main.lua" -Destination "$ConfigDir\scripts\anicat_ui\main.lua" -ErrorAction SilentlyContinue
}
if (-not (Test-Path "$ConfigDir\input.conf")) {
    Copy-Item "$ResourcesDir\mpv_config\input.conf" -Destination "$ConfigDir\input.conf" -ErrorAction SilentlyContinue
}
if (-not (Test-Path "$ConfigDir\script-opts\modernz.conf")) {
    Copy-Item "$ResourcesDir\mpv_config\script-opts\modernz.conf" -Destination "$ConfigDir\script-opts\modernz.conf" -ErrorAction SilentlyContinue
}

Write-Host "=== Cleaning up temporary files ==="
Remove-Item -Recurse -Force $TmpExtract -ErrorAction SilentlyContinue
Remove-Item -Force $MpvZip -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Bundle Setup Complete! ==="
Write-Host "Files are located in: $ResourcesDir"
