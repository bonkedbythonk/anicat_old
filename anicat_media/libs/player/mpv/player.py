"""
MPV player integration for Anicat.

This module provides the MpvPlayer class, which implements the BasePlayer interface for the MPV media player.
"""

import logging
import os
import re
import shutil
import subprocess
import sys
from typing import Optional
from ....utils.subprocess import run_cmd

from ....core.config import MpvConfig
from ....core.exceptions import AnicatError
from ....core.utils import detect
from ..base import BasePlayer
from ..params import PlayerParams
from ..types import PlayerResult

logger = logging.getLogger(__name__)

MPV_AV_TIME_PATTERN = re.compile(r"AV: ([0-9:]*) / ([0-9:]*) \(([0-9]*)%\)")


class MpvPlayer(BasePlayer):
    """
    MPV player implementation for Anicat.

    Provides desktop playback using the MPV media player.
    """

    def __init__(self, config: MpvConfig, player_type: str = "external"):
        """
        Initialize the MpvPlayer with the given MPV configuration.

        Args:
            config: MpvConfig object containing MPV-specific settings.
        """
        self.config = config
        self.executable = None

        # Determine bundled paths:
        app_dir = os.path.dirname(sys.executable)
        bundled_paths = [
            # macOS .app bundle paths
            os.path.abspath(
                os.path.join(app_dir, "..", "Resources", "resources", "mpv")
            ),
            os.path.abspath(os.path.join(app_dir, "..", "Resources", "mpv")),
            # Windows / Linux flat directory paths
            os.path.abspath(os.path.join(app_dir, "resources", "mpv")),
            os.path.abspath(os.path.join(app_dir, "resources", "mpv.exe")),
            # Development fallback relative to this source file
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "..",
                    "..",
                    "web",
                    "src-tauri",
                    "resources",
                    "mpv",
                )
            ),
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "..",
                    "..",
                    "web",
                    "src-tauri",
                    "resources",
                    "mpv.exe",
                )
            ),
        ]

        # Always search for and prioritize the bundled MPV shipped with AniCat to ensure consistent UX/shaders/ModernZ theme.
        for path in bundled_paths:
            if os.path.exists(path):
                self.executable = path
                logger.info(f"Bundled MPV selected: {self.executable}")
                # Try to remove macOS quarantine flag on the bundled resources if present
                if sys.platform == "darwin":
                    try:
                        resources_dir = os.path.dirname(self.executable)
                        subprocess.run(
                            [
                                "xattr",
                                "-r",
                                "-d",
                                "com.apple.quarantine",
                                resources_dir,
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        logger.info("Cleared macOS quarantine on bundled resources.")
                    except Exception as e:
                        logger.warning(f"Could not clear macOS quarantine dynamically: {e}")
                break

        # Only check system-installed MPV locations if no bundled MPV was found (e.g. running in CLI dev mode)
        if not self.executable:
            logger.info(
                "Bundled MPV not found. Checking system-installed MPV for compatibility."
            )
            if sys.platform == "darwin":
                self.executable = shutil.which("mpv")
                if not self.executable:
                    common_paths = [
                        "/opt/homebrew/bin/mpv",
                        "/usr/local/bin/mpv",
                        "/Applications/mpv.app/Contents/MacOS/mpv",
                        os.path.expanduser("~/Applications/mpv.app/Contents/MacOS/mpv"),
                    ]
                    for path in common_paths:
                        if os.path.exists(path):
                            self.executable = path
                            break
                if self.executable:
                    logger.info(
                        f"System-installed MPV discovered at: {self.executable}"
                    )
            elif sys.platform == "win32":
                self.executable = shutil.which("mpv")
                if not self.executable:
                    common_paths = [
                        os.path.expanduser("~\\scoop\\shims\\mpv.exe"),
                        "C:\\Program Files\\mpv\\mpv.exe",
                        "C:\\Program Files (x86)\\mpv\\mpv.exe",
                        os.path.expanduser("~\\AppData\\Local\\mpv\\mpv.exe"),
                    ]
                    for path in common_paths:
                        if os.path.exists(path):
                            self.executable = path
                            break
                if self.executable:
                    logger.info(
                        f"System-installed MPV discovered at: {self.executable}"
                    )
            else:
                # Linux / other Unix — standard PATH lookup
                self.executable = shutil.which("mpv")

        if self.executable:
            logger.info(f"MPV executable resolved to: {self.executable}")
        else:
            logger.warning("MPV executable NOT FOUND on the system.")

    def play(self, params):
        """
        Play the given media using MPV on desktop.

        Args:
            params: PlayerParams object containing playback parameters.

        Returns:
            PlayerResult: Information about the playback session.
        """
        if not self.executable:
            raise AnicatError("MPV executable not found in PATH.")
        return self._stream_on_desktop_with_subprocess(params)

    def _stream_on_desktop_with_subprocess(self, params: PlayerParams) -> PlayerResult:
        """
        Stream media using MPV via subprocess, capturing playback times.

        Args:
            params: PlayerParams object containing playback parameters.

        Returns:
            PlayerResult: Information about the playback session, including stop and total time.
        """
        mpv_args = [self.executable, params.url]

        mpv_args.extend(self._create_mpv_cli_options(params))

        pre_args = self.config.pre_args.split(",") if self.config.pre_args else []

        stop_time = None
        total_time = None

        rc, out, err = run_cmd(
            pre_args + mpv_args,
            timeout=600,
            capture_output=True,
            env=detect.get_clean_env(),
        )
        if out:
            for line in reversed(out.split("\n")):
                match = MPV_AV_TIME_PATTERN.search(line.strip())
                if match:
                    stop_time = match.group(1)
                    total_time = match.group(2)
                    break
        return PlayerResult(
            episode=params.episode, total_time=total_time, stop_time=stop_time
        )

    def play_with_ipc(self, params: PlayerParams, socket_path: str) -> subprocess.Popen:
        """
        Stream using MPV with IPC (Inter-Process Communication) for enhanced features.

        Args:
            params: PlayerParams object containing playback parameters.
            socket_path: Path to the IPC socket for player control.

        Returns:
            subprocess.Popen: The running MPV process.
        """
        if not self.executable:
            raise AnicatError(
                "MPV executable not found in PATH. Please install MPV to use the dashboard."
            )

        mpv_args = [
            self.executable,
            f"--input-ipc-server={socket_path}",
            "--idle=yes",
            "--force-window=yes",
            params.url,
        ]

        # Add custom MPV arguments
        mpv_args.extend(self._create_mpv_cli_options(params))

        # Add pre-args if configured
        pre_args = self.config.pre_args.split(",") if self.config.pre_args else []

        # Set up a dedicated debug log file for MPV output
        if sys.platform == "darwin":
            log_dir = os.path.expanduser("~/Library/Caches/anicat/logs")
        elif sys.platform == "win32":
            log_dir = os.path.expanduser("~/AppData/Local/anicat/logs")
        else:
            log_dir = os.path.expanduser("~/.cache/anicat/logs")

        try:
            os.makedirs(log_dir, exist_ok=True)
            mpv_log_path = os.path.join(log_dir, "mpv.log")
            mpv_log_file = open(mpv_log_path, "w", encoding="utf-8")
            logger.info(f"Redirecting MPV process stdout/stderr to: {mpv_log_path}")
        except Exception as e:
            logger.warning(
                f"Could not create MPV log file: {e}. Falling back to DEVNULL."
            )
            mpv_log_file = subprocess.DEVNULL

        full_cmd = pre_args + mpv_args

        # Isolated standalone Vulkan ICD resolution for Mac out-of-the-box compatibility
        process_env = detect.get_clean_env().copy()

        # In development mode, prioritize the dynamically located resources_dir over sys.executable paths if vk_icd.json exists there
        if sys.platform == "darwin":
            resources_dir = self._find_resources_dir()
            if resources_dir:
                dev_icd = os.path.abspath(
                    os.path.join(resources_dir, "lib", "vk_icd.json")
                )
                if os.path.exists(dev_icd):
                    process_env["VK_ICD_FILENAMES"] = dev_icd
                    process_env["VK_DRIVER_FILES"] = dev_icd

            if process_env.get("VK_ICD_FILENAMES"):
                logger.info(
                    f"Vulkan ICD dynamic loader isolation active: {process_env.get('VK_ICD_FILENAMES')}"
                )

        logger.info(f"Starting MPV with IPC socket: {socket_path}")
        logger.info(f"MPV Command: {' '.join(full_cmd)}")
        logger.info(f"MPV Environment: {process_env}")

        try:
            process = subprocess.Popen(
                full_cmd,
                env=process_env,
                stdout=mpv_log_file,
                stderr=mpv_log_file,
            )
        except Exception as e:
            logger.error(f"Failed to spawn MPV process: {e}", exc_info=True)
            raise AnicatError(f"Failed to spawn MPV player process: {e}")

        return process

    def _create_mpv_cli_options(self, params: PlayerParams) -> list[str]:
        """
        Create a list of MPV CLI options based on playback parameters.

        Args:
            params: PlayerParams object containing playback parameters.

        Returns:
            list[str]: List of MPV CLI arguments.
        """
        mpv_args = []

        if sys.platform == "darwin":
            mpv_args.append("--vo=gpu")

        if getattr(params, "subtitles", None):
            for sub_url in params.subtitles:
                mpv_args.append(f"--sub-file={sub_url}")

        if getattr(params, "fullscreen", False):
            mpv_args.append("--fs")
            logger.info(
                "AniCat is in fullscreen. Requesting MPV to launch in fullscreen mode (--fs)."
            )

        # Dynamically locate isolated configs and shaders from resources, regardless of whether system or bundled MPV is used
        resources_dir = self._find_resources_dir()
        if resources_dir:
            bundled_config = os.path.abspath(os.path.join(resources_dir, "mpv_config"))
            if os.path.exists(bundled_config):
                # Enforce native OSC disable explicitly to override any global/fallback settings
                mpv_args.append("--osc=no")
                # Suppress the built-in MPV OSD progress bar that appears mid-screen on seek
                mpv_args.append("--osd-level=1")
                mpv_args.append("--osd-on-seek=no")
                mpv_args.append("--osd-bar=no")
                # Point config-dir to our isolated, custom-themed settings to load mpv.conf, input.conf, and modernz.lua
                mpv_args.append(f"--config-dir={bundled_config}")

                # Use a writable watch-later directory for saving volume, position, etc.
                # The bundled config-dir is read-only, so MPV can't write watch_later files to it.
                if sys.platform == "darwin":
                    watch_later_dir = os.path.expanduser(
                        "~/Library/Caches/anicat/mpv_watch_later"
                    )
                elif sys.platform == "win32":
                    watch_later_dir = os.path.expanduser(
                        "~/AppData/Local/anicat/mpv_watch_later"
                    )
                else:
                    watch_later_dir = os.path.expanduser(
                        "~/.cache/anicat/mpv_watch_later"
                    )
                os.makedirs(watch_later_dir, exist_ok=True)
                mpv_args.append(f"--watch-later-dir={watch_later_dir}")
                logger.info(
                    f"Using isolated premium MPV configuration from: {bundled_config}"
                )
                # If we ship a custom AniCat UI script, prefer loading it explicitly
                ani_ui = os.path.abspath(
                    os.path.join(bundled_config, "scripts", "anicat_ui", "main.lua")
                )
                if os.path.exists(ani_ui):
                    # Pass script explicitly in case MPV's auto-loading is affected by user settings
                    mpv_args.append(f"--script={ani_ui}")
                    logger.info(f"Injecting AniCat custom UI script: {ani_ui}")

            # Dynamically map and inject real-time upscaling shaders based on user's performance preference
            shader_profile = getattr(params, "shader_profile", "balanced") or "balanced"
            if shader_profile != "off":
                bundled_shaders_dir = os.path.join(bundled_config, "shaders")
                if os.path.exists(bundled_shaders_dir):
                    # Mode A: CNN_L-based upscaling — sharper than DoG, runs well on Apple Silicon
                    clamp_path = os.path.join(
                        bundled_shaders_dir, "Anime4K_Clamp_Highlights.glsl"
                    )
                    restore_path = os.path.join(
                        bundled_shaders_dir, "Anime4K_Restore_CNN_L.glsl"
                    )
                    upscale_path = os.path.join(
                        bundled_shaders_dir, "Anime4K_Upscale_CNN_x2_L.glsl"
                    )
                    downscale_x2 = os.path.join(
                        bundled_shaders_dir, "Anime4K_AutoDownscalePre_x2.glsl"
                    )
                    downscale_x4 = os.path.join(
                        bundled_shaders_dir, "Anime4K_AutoDownscalePre_x4.glsl"
                    )
                    shaders_to_load = []
                    for p in [
                        clamp_path,
                        restore_path,
                        upscale_path,
                        downscale_x2,
                        downscale_x4,
                    ]:
                        if os.path.exists(p):
                            shaders_to_load.append(p)
                    if shaders_to_load:
                        mpv_args.append(f"--glsl-shaders={':'.join(shaders_to_load)}")
                        logger.info("Using Anime4K Mode A (CNN_L) upscaling shaders.")
            else:
                logger.info(
                    "GPU upscaling shaders are disabled (Battery Saver / Low-End profile)."
                )

        # Pass AniSkip skip times to the AniCat UI script if available
        if getattr(params, "skip_times", None):
            try:
                parts = []
                for s in params.skip_times:
                    t = s.get("type")
                    start = int(s.get("start") or 0)
                    end = int(s.get("end") or 0)
                    parts.append(f"{t},{start},{end}")
                encoded = ";".join(parts)
                # MPV's --script-opts uses commas to separate key=value pairs.
                # If a value contains a comma, the comma must be escaped as \,
                encoded_escaped = encoded.replace(",", "\\,")
                mpv_args.append(f"--script-opts=anicat_ui-skip_times={encoded_escaped}")
                logger.debug(f"Injected AniCat skip_times script-opts: {encoded}")
            except Exception:
                logger.debug("Failed to append AniCat skip_times to MPV args")

        if params.headers:
            # mpv prefers no spaces after commas and colons in http-header-fields
            headers_list = []
            for k, v in params.headers.items():
                # Clean value of newlines and extra spaces
                clean_v = v.strip().replace("\n", "").replace("\r", "")
                headers_list.append(f"{k}:{clean_v}")

            header_str = ",".join(headers_list)
            mpv_args.append(f"--http-header-fields={header_str}")

        if params.subtitles:
            for sub in params.subtitles:
                mpv_args.append(f"--sub-file={sub}")

        if params.start_time:
            mpv_args.append(f"--start={params.start_time}")

        if params.title:
            mpv_args.append(f"--title={params.title}")

        if self.config.args:
            mpv_args.extend(self.config.args.split(","))
        return mpv_args

    def _find_resources_dir(self) -> Optional[str]:
        """Locates the application's resources directory dynamically."""
        # Prefer common packaged locations, then fall back to development resources.
        app_dir = os.path.dirname(sys.executable)
        candidate_paths = []
        if sys.platform == "darwin":
            candidate_paths.extend(
                [
                    os.path.abspath(
                        os.path.join(app_dir, "..", "Resources", "resources")
                    ),
                    os.path.abspath(os.path.join(app_dir, "..", "Resources")),
                    os.path.abspath(os.path.join(app_dir, "resources")),
                ]
            )
        else:
            candidate_paths.extend(
                [
                    os.path.abspath(os.path.join(app_dir, "resources")),
                ]
            )

        # Explicit development fallback relative to the package
        dev_fallback = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "..",
                "web",
                "src-tauri",
                "resources",
            )
        )
        candidate_paths.append(dev_fallback)

        # Try to detect a repository root (look for .git or pyproject.toml) and prefer its web/src-tauri/resources
        cur = os.path.abspath(os.path.dirname(__file__))
        for _ in range(6):
            if os.path.exists(os.path.join(cur, ".git")) or os.path.exists(
                os.path.join(cur, "pyproject.toml")
            ):
                repo_resources = os.path.join(cur, "web", "src-tauri", "resources")
                candidate_paths.append(os.path.abspath(repo_resources))
                break
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent

        for p in candidate_paths:
            if p and os.path.exists(p):
                return p
        return None


if __name__ == "__main__":
    from ....core.constants import APP_ASCII_ART

    print(APP_ASCII_ART)
    url = input("Enter the url you would like to stream: ")
    mpv = MpvPlayer(MpvConfig())
    player_result = mpv.play(PlayerParams(episode="", query="", url=url, title=""))
    print(player_result)
