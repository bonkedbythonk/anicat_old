import json
import logging
import os
import tomllib
from pathlib import Path
from typing import Optional

from ....core.constants import APP_DATA_DIR
from ....core.utils.file import AtomicWriter, FileLock
from ....libs.media_api.types import UserProfile
from .model import AuthModel, AuthProfile

logger = logging.getLogger(__name__)

AUTH_FILE = APP_DATA_DIR / "auth.json"

# Secondary config location following XDG conventions
_XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
_XDG_TOKEN_FILE = _XDG_CONFIG_HOME / "anicat" / "token.txt"
_XDG_CONFIG_FILE = _XDG_CONFIG_HOME / "anicat" / "config.toml"


class AuthService:
    def __init__(self, media_api: str):
        self.path = AUTH_FILE
        self.media_api = media_api
        _lock_file = APP_DATA_DIR / "auth.lock"
        self._lock = FileLock(_lock_file)

    def resolve_token(self, config: Optional["AppConfig"] = None) -> str | None:
        """
        Resolve an AniList token exclusively from the configuration object.
        """
        if config and config.anilist.token:
            return config.anilist.token
        
        logger.debug("No token found in config.")
        return None

    @staticmethod
    def _read_token_from_path_or_string(value: str) -> str | None:
        """
        Interpret a value as either a file path (reading its contents) or a raw token string.

        Args:
            value: A string that is either a file path or a raw token.

        Returns:
            The token string, or None if the file was empty or unreadable.
        """
        path = Path(value)
        if path.is_file():
            try:
                token = path.read_text(encoding="utf-8").strip()
                if token:
                    return token
                logger.warning(f"Token file is empty: {path}")
                return None
            except Exception as e:
                logger.warning(f"Error reading token from file {path}: {e}")
                return None
        return value.strip() if value.strip() else None

    def get_auth(self) -> Optional[AuthProfile]:
        auth = self._load_auth()
        return auth.profiles.get(self.media_api)

    def save_user_profile(self, profile: UserProfile, token: str) -> None:
        auth = self._load_auth()
        auth.profiles[self.media_api] = AuthProfile(user_profile=profile, token=token)
        self._save_auth(auth)
        logger.info(f"Successfully saved user credentials to {self.path}")

    def clear_user_profile(self) -> None:
        """Deletes the user credentials file."""
        if self.path.exists():
            self.path.unlink()
            logger.info("Cleared user credentials.")

    def _load_auth(self) -> AuthModel:
        if not self.path.exists():
            self._auth = AuthModel()
            self._save_auth(self._auth)
            return self._auth

        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            self._auth = AuthModel.model_validate(data)
            return self._auth

    def _save_auth(self, auth: AuthModel):
        with self._lock:
            with AtomicWriter(self.path) as f:
                json.dump(auth.model_dump(), f, indent=2)
            logger.info(f"Successfully saved user credentials to {self.path}")

