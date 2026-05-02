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
        Play the media using IINA by executing the binary directly if available, 
        or falling back to the macOS open command.
        """
        import os
        iina_binary = "/Applications/IINA.app/Contents/MacOS/IINA"
        use_binary = os.path.exists(iina_binary)

        iina_args = []
        
        # Extract and clean headers
        referer = params.headers.get("Referer", params.headers.get("referer", ""))
        user_agent = params.headers.get("User-Agent", params.headers.get("user-agent", ""))
        
        # Ensure strings and clean newlines
        referer = str(referer).strip().replace("\n", "").replace("\r", "")
        user_agent = str(user_agent).strip().replace("\n", "").replace("\r", "")

        if referer or user_agent:
            # Format according to user request: "Referer: <URL>,User-Agent: <AGENT>"
            # Removed spaces to ensure stricter compatibility with mpv/IINA parser
            header_str = f"Referer:{referer},User-Agent:{user_agent}"
            iina_args.append(f"--http-header-fields={header_str}")

        if params.title:
            iina_args.append(f"--title={params.title}")

        if params.start_time:
            iina_args.append(f"--start={params.start_time}")

        # Construct final command
        if use_binary:
            commands = [iina_binary] + iina_args + [params.url]
        else:
            # Fallback to open -a IINA
            commands = ["open", "-a", "IINA", "--args"] + iina_args + [params.url]

        import shlex
        logger.info(f"Launching IINA: {shlex.join(commands)}")

        try:
            # We run blocking here. When the user quits IINA, it returns.
            subprocess.run(commands, check=False)
            
            # Since IINA doesn't have an IPC returned to us easily, we just return a stub result
            return PlayerResult(
                episode=params.episode,
                stop_time="0:00",
                total_time="0:00"
            )
        except Exception as e:
            logger.error(f"Failed to launch IINA: {e}")
            return PlayerResult(
                episode=params.episode,
                stop_time="0:00",
                total_time="0:00"
            )

    def play_with_ipc(self, params: PlayerParams, socket_path: str) -> subprocess.Popen:
        """
        IINA does not currently support the same IPC tracking pattern used by MPV natively.
        Raises NotImplementedError.
        """
        raise NotImplementedError("IINA does not support IPC through Anicat currently.")
