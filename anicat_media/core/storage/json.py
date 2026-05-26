import json
import logging
import shutil
from pathlib import Path
from typing import Any, Union

from ..utils.file import AtomicWriter

logger = logging.getLogger(__name__)


def load_json(path: Union[str, Path], default: Any = None) -> Any:
    """
    Safely load a JSON file. If the file is missing or corrupted,
    moves the corrupted file to '.old' (if it exists) and returns
    the `default` structure (or an empty dict `{}`).
    """
    if default is None:
        default = {}

    path = Path(path)
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON at {path} ({e}). Attempting self-heal.")
        try:
            shutil.move(str(path), f"{path}.old")
        except Exception:
            pass
        return default
    except Exception as e:
        logger.error(f"Failed to read {path} ({e}). Returning default.")
        return default


def save_json(path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """
    Safely save JSON data to a file using an atomic write.
    Ensures that the output file is not left corrupted.
    """
    path = Path(path)
    # Ensure parent directories exist
    path.parent.mkdir(parents=True, exist_ok=True)
    with AtomicWriter(path, mode="w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
