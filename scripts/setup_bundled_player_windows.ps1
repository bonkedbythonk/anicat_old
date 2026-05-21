# setup_bundled_player_windows.ps1
# Automates downloading, extracting, and configuring the portable MPV player for AniCat on Windows.
#
# MPV is obtained via Chocolatey (pre-installed on CI), Winget, or SourceForge fallback.
# 7-Zip is only needed for the SourceForge fallback path.

$ErrorActionPreference = "Stop"

$ResourcesDir = "web\src-tauri\resources"
$ConfigDir = "$ResourcesDir\mpv_config"

# ---------------------------------------------------------------------------
# Helper: ensure 7-Zip is available (non-fatal — only needed for SourceForge path)
# ---------------------------------------------------------------------------
function Ensure-7Zip {
    $script:_7zAvailable = $false
    $7zPath = Get-Command 7z -ErrorAction SilentlyContinue
    if ($7zPath) {
        Write-Host "7-Zip found at: $($7zPath.Source)"
        $script:_7zAvailable = $true
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
            $script:_7zAvailable = $true
            return
        }
    }
    # Try Chocolatey install
    Write-Host "7-Zip not found. Attempting Chocolatey install..."
    $choco = Get-Command choco -ErrorAction SilentlyContinue
    if ($choco) {
        choco install 7zip -y --no-progress | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $script:_7zAvailable = $true
        Write-Host "7-Zip installed via Chocolatey."
        return
    }
    Write-Host "WARNING: 7-Zip not available. SourceForge fallback will not work if needed."

# ---------------------------------------------------------------------------
# Helper: get MPV binary + DLLs (Chocolatey → Winget → SourceForge fallback)
# ---------------------------------------------------------------------------
function Get-MpvBinaries {
    param([string]$DestDir)

    # -- Tier 1: Check if mpv is already installed in PATH --
    $existing = Get-Command mpv -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "mpv already installed: $($existing.Source)"
        $srcDir = Split-Path $existing.Source -Parent
        Copy-Item "$srcDir\mpv.exe" -Destination "$DestDir\mpv.exe" -Force
        Get-ChildItem "$srcDir\*.dll" | ForEach-Object {
            Copy-Item $_.FullName -Destination "$DestDir\" -Force
        }
        Write-Host "Copied mpv.exe + DLLs from existing install."
        return
    }

    # -- Tier 2: Chocolatey (pre-installed on GitHub Actions Windows runners) --
    $choco = Get-Command choco -ErrorAction SilentlyContinue
    if ($choco) {
        Write-Host "Installing MPV via Chocolatey..."
        choco install mpv -y --no-progress --limit-output 2>&1 | Out-Null
        # Refresh PATH so we can find mpv
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $mpvExe = Get-Command mpv -ErrorAction SilentlyContinue
        if ($mpvExe) {
            $srcDir = Split-Path $mpvExe.Source -Parent
            Copy-Item "$srcDir\mpv.exe" -Destination "$DestDir\mpv.exe" -Force
            Get-ChildItem "$srcDir\*.dll" | ForEach-Object {
                Copy-Item $_.FullName -Destination "$DestDir\" -Force
            }
            Write-Host "MPV installed and copied via Chocolatey."
            return
        }
        Write-Host "Chocolatey install completed but mpv.exe not found on PATH."
    }

    # -- Tier 3: Winget (built into Windows 10/11) --
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "Installing MPV via Winget..."
        winget install --id=mpv.net --exact --silent --accept-source-agreements 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            # Try alternative package (mpv.net is a common one, try mpv directly)
            winget install --id=mpv --exact --silent --accept-source-agreements 2>&1 | Out-Null
        }
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $mpvExe = Get-Command mpv -ErrorAction SilentlyContinue
        if ($mpvExe) {
            $srcDir = Split-Path $mpvExe.Source -Parent
            Copy-Item "$srcDir\mpv.exe" -Destination "$DestDir\mpv.exe" -Force
            Get-ChildItem "$srcDir\*.dll" | ForEach-Object {
                Copy-Item $_.FullName -Destination "$DestDir\" -Force
            }
            Write-Host "MPV installed and copied via Winget."
            return
        }
        Write-Host "Winget install completed but mpv.exe not found on PATH."
    }

    # -- Tier 4: Direct SourceForge download (last resort) --
    if (-not $script:_7zAvailable) {
        throw "No package manager available and 7-Zip is not installed. Cannot download MPV from SourceForge. Please install MPV manually (choco install mpv, winget install mpv, or from https://mpv.io)."
    }
    Write-Host "No package manager available. Attempting direct SourceForge download..."
    # SourceForge RSS feed for the project
    try {
        $sfRss = Invoke-RestMethod -Uri "https://sourceforge.net/projects/mpv-player-windows/rss?path=/64bit" -TimeoutSec 30
        # Parse the first file download link from the RSS
        $match = [regex]::Match($sfRss, 'https://sourceforge\.net/projects/mpv-player-windows/files/64bit/[^"]+\.7z/download')
        if ($match.Success) {
            $sfUrl = $match.Value
            Write-Host "SourceForge URL: $sfUrl"
            $tmpZip = "$env:TEMP\mpv-sourceforge.7z"
            Invoke-WebRequest -Uri $sfUrl -OutFile $tmpZip -TimeoutSec 180
            # Extract the .7z
            $extractDir = "$env:TEMP\mpv_sf_extract"
            Remove-Item -Recurse -Force $extractDir -ErrorAction SilentlyContinue
            New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
            & 7z x "$tmpZip" -o"$extractDir" -y 2>&1 | Out-Null
            # Find mpv.exe in the extracted tree
            $extractedMpv = Get-ChildItem -Path $extractDir -Recurse -Filter "mpv.exe" | Select-Object -First 1
            if ($extractedMpv) {
                $extractedDir = Split-Path $extractedMpv.FullName -Parent
                Copy-Item $extractedMpv.FullName -Destination "$DestDir\mpv.exe" -Force
                Get-ChildItem "$extractedDir\*.dll" | ForEach-Object {
                    Copy-Item $_.FullName -Destination "$DestDir\" -Force
                }
                Write-Host "MPV downloaded and extracted from SourceForge."
                Remove-Item -Recurse -Force $extractDir -ErrorAction SilentlyContinue
                Remove-Item -Force $tmpZip -ErrorAction SilentlyContinue
                return
            }
        }
    } catch {
        Write-Host "SourceForge download failed: $_"
    }

    throw "Could not obtain MPV binaries from any source. Please install MPV manually (choco install mpv, winget install mpv, or from https://mpv.io)."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

Write-Host "=== 1. Ensuring 7-Zip is available ==="
Ensure-7Zip

Write-Host "=== 2. Creating resources directory ==="
New-Item -ItemType Directory -Force -Path $ResourcesDir | Out-Null

Write-Host "=== 3. Obtaining MPV binaries ==="
Get-MpvBinaries -DestDir $ResourcesDir

# Verify we have mpv.exe
if (-not (Test-Path "$ResourcesDir\mpv.exe")) {
    throw "mpv.exe not found in $ResourcesDir after Get-MpvBinaries"
}
Write-Host "MPV binary size: $('{0:N0}' -f (Get-Item "$ResourcesDir\mpv.exe").Length) bytes"

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
