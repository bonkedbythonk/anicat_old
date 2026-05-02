import subprocess
import logging
from typing import Optional

from ....core.config import StreamConfig
from ..base import BasePlayer
from ..params import PlayerParams
from ..types import PlayerResult

logger = logging.getLogger(__name__)

class IinaPlayer(BasePlayer):
    """
    IINA player implementation using macOS `open` command.
    """

    def __init__(self, config: StreamConfig):
        super().__init__(config)

    def play(self, params: PlayerParams) -> PlayerResult:
        """
        Play the media using IINA by executing it via the macOS open command.
        This call is blocking because it waits for the IINA process to close,
        which allows Anicat's auto_next loop to function natively.
        """
        commands = [
            "open",
            "-W",  # Wait for the application to exit
            "-n",  # Open a new instance of the application
            "-a",
            "IINA",
            "--args",
            params.url
        ]
        
        # Format HTTP headers for IINA
        headers_str = ""
        if params.headers:
            header_list = []
            for k, v in params.headers.items():
                header_list.append(f"{k}: {v}")
            if header_list:
                headers_str = ", ".join(header_list)
                commands.append(f"--http-header-fields={headers_str}")

        logger.info(f"Launching IINA: {' '.join(commands)}")

        try:
            # We run blocking here. When the user quits IINA, it returns.
            subprocess.run(commands, check=False)
            
            # Since IINA doesn't have an IPC returned to us easily, we just return a stub result
            return PlayerResult(
                status="completed",
                last_position="0:00",
                duration="0:00",
                percent_pos=0.0
            )
        except Exception as e:
            logger.error(f"Failed to launch IINA: {e}")
            return PlayerResult(
                status="failed",
                last_position="0:00",
                duration="0:00",
                percent_pos=0.0
            )

    def play_with_ipc(self, params: PlayerParams, socket_path: str) -> subprocess.Popen:
        """
        IINA does not currently support the same IPC tracking pattern used by MPV natively.
        Raises NotImplementedError.
        """
        raise NotImplementedError("IINA does not support IPC through Anicat currently.")
