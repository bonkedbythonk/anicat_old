"""Small subprocess helper to standardize timeouts and capture behavior.

Keep this minimal and dependency-free: return a simple tuple of
(returncode, stdout, stderr) and never raise on non-zero returncodes.
"""

from __future__ import annotations

import subprocess
from typing import Optional, Tuple, Union


def run_cmd(
    cmd: Union[str, list],
    timeout: int = 10,
    cwd: Optional[str] = None,
    capture_output: bool = True,
    text: bool = True,
    env: Optional[dict] = None,
) -> Tuple[int, str, str]:
    try:
        cp = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=text,
            shell=isinstance(cmd, str),
            env=env,
        )
        return cp.returncode, cp.stdout or "", cp.stderr or ""
    except subprocess.TimeoutExpired as e:
        return 124, getattr(e, "stdout", "") or "", getattr(e, "stderr", "") or str(e)
    except Exception as e:
        return 1, "", str(e)
