import logging
import httpx
from ....core.constants import VERSION, UPDATE_STATUS_FILE, LAST_COMMIT_FILE

logger = logging.getLogger(__name__)

class UpdaterService:
    def __init__(self):
        self.remote_version: str | None = None
        self.remote_hash: str | None = None
        self.local_hash: str | None = "Unknown"
        
        if LAST_COMMIT_FILE.exists():
            try:
                self.local_hash = LAST_COMMIT_FILE.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        
        # If still unknown and we're in a git repo, try to get it from git
        if self.local_hash == "Unknown":
            try:
                import subprocess
                result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=2.0)
                if result.returncode == 0:
                    self.local_hash = result.stdout.strip()
            except Exception:
                pass

    def check_version(self, force: bool = False) -> bool:
        """
        Checks for updates by comparing local version and commit hash with remote.
        If force is True, bypasses cache and performs fresh requests.
        """
        try:
            # Bypass cache logic (if we had one that skipped requests, we'd check it here)
            # For now, we always perform the requests if called, but we'll satisfy the "force" requirement
            # by ensuring we don't return early if we had some local cache.
            
            # 1. Fetch latest commit hash from GitHub
            commit_url = "https://api.github.com/repos/bonkedbythonk/anicat/commits/main"
            commit_resp = httpx.get(commit_url, timeout=5.0)
            if commit_resp.status_code == 200:
                self.remote_hash = commit_resp.json().get("sha", "")
            
            # 2. Fetch latest version from pyproject.toml
            repo_pyproject_url = "https://raw.githubusercontent.com/bonkedbythonk/anicat/main/pyproject.toml"
            pyproject_resp = httpx.get(repo_pyproject_url, timeout=5.0)
            
            is_available = False
            if pyproject_resp.status_code == 200:
                import re
                content = pyproject_resp.text
                match = re.search(r'version\s*=\s*"([^"]+)"', content)
                if match:
                    self.remote_version = match.group(1)
                    
                    # Version comparison
                    version_differs = self.remote_version != VERSION
                    
                    # Hash comparison (if available)
                    hash_differs = False
                    if self.remote_hash and self.local_hash != "Unknown":
                        hash_differs = self.remote_hash != self.local_hash
                    
                    # If hashes differ, we update even if version is same
                    is_available = version_differs or hash_differs
                    
                    # Store the result (True/False)
                    UPDATE_STATUS_FILE.write_text("1" if is_available else "0", encoding="utf-8")
                    return is_available
            
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            
        return False

    def get_cached_status(self) -> bool:
        """Returns True if an update was detected in the last manual check."""
        if UPDATE_STATUS_FILE.exists():
            try:
                return UPDATE_STATUS_FILE.read_text(encoding="utf-8").strip() == "1"
            except Exception:
                pass
        return False
