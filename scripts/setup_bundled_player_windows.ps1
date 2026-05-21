# setup_bundled_player_windows.ps1
# Automates downloading, extracting, and configuring the portable MPV player for AniCat on Windows.
#
# Requirements: PowerShell 5.1+, internet access. 7-Zip is auto-installed if missing.

$ErrorActionPreference = "Stop"

$ResourcesDir = "web\src-tauri\resources"
$ConfigDir = "$ResourcesDir\mpv_config"

# ---------------------------------------------------------------------------
# Helper: ensure 7-Zip is available (auto-install via Chocolatey on CI)
# ---------------------------------------------------------------------------
function Ensure-7Zip {
    $7zPath = Get-Command 7z -ErrorAction SilentlyContinue
    if ($7zPath) {
        Write-Host "7-Zip found at: $($7zPath.Source)"
        return
    }
    # Check common install locations
    $commonPaths = @(
        "${env:ProgramFiles}\7-Zip\7z.exe",
        "${env:ProgramFiles(x86)}\7-Zip\7z.exe"
    )
    foreach ($p in $commonPaths) {
        if (Test-Path $p) {
            $env:Path += ";$(Split-Path $p)"
            Write-Host "7-Zip found at: $p"
            return
        }
    }
    # Try Chocolatey install (works on GitHub Actions Windows runners)
    Write-Host "7-Zip not found. Attempting Chocolatey install..."
    $choco = Get-Command choco -ErrorAction SilentlyContinue
    if ($choco) {
        choco install 7zip -y --no-progress | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        Write-Host "7-Zip installed via Chocolatey."
        return
    }
    throw "7-Zip is required but not found, and Chocolatey is not available to install it."
}

# ---------------------------------------------------------------------------
# Helper: download the MPV portable 7z archive
# ---------------------------------------------------------------------------
function Get-MpvArchive {
    $MpvZip = "$env:TEMP\mpv-windows.7z"
    $ghReleaseUrl = "https://api.github.com/repos/shinchiro/mpv-winbuild/releases/latest"

    # -- Tier 1: GitHub API for latest release --
    try {
        Write-Host "Trying GitHub API: $ghReleaseUrl"
        $ReleaseJson = Invoke-RestMethod -Uri $ghReleaseUrl -TimeoutSec 30 -ErrorAction Stop
        $Asset = $ReleaseJson.assets | Where-Object {
            $_.name -match "mpv-x86_64.*\.7z" -and $_.name -notmatch "installer|setup|symbols|pdbs"
        } | Select-Object -First 1
        if ($Asset) {
            Write-Host "Found: $($Asset.name) ($('{0:N0}' -f $Asset.size) bytes)"
            Write-Host "Downloading..."
            Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $MpvZip -TimeoutSec 180
            return $MpvZip
        }
        Write-Host "GitHub API succeeded but no matching 64-bit portable .7z asset found."
    } catch {
        Write-Host "GitHub API failed: $_"
    }

    # -- Tier 2: Direct download from a known good release (pinned fallback) --
    $fallbackUrl = "https://github.com/shinchiro/mpv-winbuild/releases/download/2025-03-23-release/mpv-x86_64-20250323.7z"
    Write-Host "Trying fallback URL: $fallbackUrl"
    try {
        Invoke-WebRequest -Uri $fallbackUrl -OutFile $MpvZip -TimeoutSec 180 -ErrorAction Stop
        Write-Host "Fallback download complete."
        return $MpvZip
    } catch {
        throw "All download methods failed. Last error: $_"
    }
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

Write-Host "=== 1. Ensuring 7-Zip is available ==="
Ensure-7Zip

Write-Host "=== 2. Downloading Windows MPV portable build ==="
$MpvZip = Get-MpvArchive

# Validate the downloaded archive
if (-not (Test-Path $MpvZip)) {
    throw "Downloaded MPV archive not found at: $MpvZip"
}
$fileInfo = Get-Item $MpvZip
if ($fileInfo.Length -lt 1000000) {
    throw "Downloaded MPV archive is too small ($($fileInfo.Length) bytes) — likely a redirect page or error, not a valid archive."
}
Write-Host "Archive size: $('{0:N0}' -f $fileInfo.Length) bytes"

Write-Host "=== 3. Creating resources directory and extracting MPV ==="
New-Item -ItemType Directory -Force -Path $ResourcesDir | Out-Null

$TmpExtract = "$env:TEMP\mpv_extract"
Remove-Item -Recurse -Force $TmpExtract -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $TmpExtract | Out-Null

# Extract with 7-Zip (capture output for debugging)
$extractOutput = & 7z x "$MpvZip" -o"$TmpExtract" -y 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "7z extraction output:"
    Write-Host ($extractOutput -join "`n")
    throw "7-Zip extraction failed with exit code $LASTEXITCODE"
}
Write-Host "Extraction successful."

# Find the extracted mpv directory (named like "mpv-x86_64-YYYYMMDD")
$MpvDir = Get-ChildItem -Path $TmpExtract -Directory | Select-Object -First 1
if (-not $MpvDir) {
    Write-Host "Contents of extract directory:"
    Get-ChildItem -Path $TmpExtract | ForEach-Object { Write-Host "  $($_.Name)" }
    throw "Could not find extracted MPV directory inside $TmpExtract"
}
Write-Host "Extracted MPV directory: $($MpvDir.Name)"

Write-Host "Copying MPV binary and libraries..."
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
