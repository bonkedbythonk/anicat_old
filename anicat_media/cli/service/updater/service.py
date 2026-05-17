import logging
import httpx
from anicat_media.core.constants import VERSION, UPDATE_STATUS_FILE, LAST_COMMIT_FILE

logger = logging.getLogger(__name__)

class UpdaterService:
    def __init__(self, config=None):
        self.config = config
        self.remote_version: str | None = None
        self.remote_hash: str | None = None
        self.local_hash: str | None = "Unknown"
        
        if not self.config:
            try:
                from anicat_media.cli.config import ConfigLoader
                self.config = ConfigLoader().load(allow_setup=False)
            except Exception:
                pass
        
        if LAST_COMMIT_FILE.exists():
            try:
                self.local_hash = LAST_COMMIT_FILE.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        
        # If still unknown and we're in a git repo, try to get it from git
        if self.local_hash == "Unknown":
            try:
                from anicat_media.utils.subprocess import run_cmd

                rc, stdout, _ = run_cmd(["git", "rev-parse", "HEAD"], timeout=2)
                if rc == 0 and stdout:
                    self.local_hash = stdout.strip()
            except Exception:
                pass

    def check_version(self, force: bool = False) -> bool:
        """
        Checks for updates by comparing local version and commit hash with remote.
        If force is True, bypasses cache and performs fresh requests.
        """
        try:
            # Determine target branch
            branch = "main"
            if self.config:
                branch_setting = getattr(self.config.general, "update_branch", "stable")
                if branch_setting == "nightly":
                    try:
                        from anicat_media.utils.subprocess import run_cmd
                        rc, stdout, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=2)
                        if rc == 0 and stdout and stdout.strip() == "testbranch":
                            branch = "testbranch"
                        else:
                            branch = "nightly"
                    except Exception:
                        branch = "nightly"

            # 1. Fetch latest commit hash from GitHub
            commit_url = f"https://api.github.com/repos/bonkedbythonk/anicat/commits/{branch}"
            commit_resp = httpx.get(commit_url, timeout=5.0)
            if commit_resp.status_code == 200:
                self.remote_hash = commit_resp.json().get("sha", "")
            
            # Baseline logic: If no local hash exists, save the current remote hash
            is_baseline = False
            if self.remote_hash and (not LAST_COMMIT_FILE.exists() or not LAST_COMMIT_FILE.read_text().strip()):
                LAST_COMMIT_FILE.write_text(self.remote_hash, encoding="utf-8")
                self.local_hash = self.remote_hash
                is_baseline = True

            # 2. Fetch latest version from pyproject.toml
            repo_pyproject_url = f"https://raw.githubusercontent.com/bonkedbythonk/anicat/{branch}/pyproject.toml"
            pyproject_resp = httpx.get(repo_pyproject_url, timeout=5.0)
            
            if pyproject_resp.status_code == 200:
                import re
                content = pyproject_resp.text
                match = re.search(r'version\s*=\s*"([^"]+)"', content)
                if match:
                    self.remote_version = match.group(1)
                    
                    # If this was a baseline run, we already caught up to the latest hash
                    if is_baseline:
                        UPDATE_STATUS_FILE.write_text("0", encoding="utf-8")
                        return False

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
