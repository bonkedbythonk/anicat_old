import logging
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from ..exceptions import AnicatError, DependencyNotFoundError

try:
    import libtorrent as lt

    LIBTORRENT_AVAILABLE = True
except ImportError:
    LIBTORRENT_AVAILABLE = False
    lt = None  # type: ignore

logger = logging.getLogger(__name__)


class TorrentDownloadError(AnicatError):
    """Raised when torrent download fails."""

    pass


class TorrentDownloader:
    """
    A robust torrent downloader that uses libtorrent when available,
    with fallback to webtorrent CLI.
    """

    def __init__(
        self,
        download_path: Path,
        max_upload_rate: int = -1,  # -1 means unlimited
        max_download_rate: int = -1,  # -1 means unlimited
        max_connections: int = 200,
        listen_port: int = 6881,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize the torrent downloader.

        Args:
            download_path: Directory to download torrents to
            max_upload_rate: Maximum upload rate in KB/s (-1 for unlimited)
            max_download_rate: Maximum download rate in KB/s (-1 for unlimited)
            max_connections: Maximum number of connections
            listen_port: Port to listen on for incoming connections
            progress_callback: Optional callback function for download progress updates
        """
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.max_upload_rate = max_upload_rate
        self.max_download_rate = max_download_rate
        self.max_connections = max_connections
        self.listen_port = listen_port
        self.progress_callback = progress_callback
        self.session: Optional[Any] = None

    def _setup_libtorrent_session(self) -> Any:
        """Setup and configure libtorrent session."""
        if not LIBTORRENT_AVAILABLE or lt is None:
            raise DependencyNotFoundError("libtorrent is not available")

        session = lt.session()  # type: ignore

        # Configure session settings
        settings = {
            "user_agent": "Anicat/1.0",
            "listen_interfaces": f"0.0.0.0:{self.listen_port}",
            "enable_outgoing_utp": True,
            "enable_incoming_utp": True,
            "enable_outgoing_tcp": True,
            "enable_incoming_tcp": True,
            "connections_limit": self.max_connections,
            "dht_bootstrap_nodes": "dht.transmissionbt.com:6881",
        }

        if self.max_upload_rate > 0:
            settings["upload_rate_limit"] = self.max_upload_rate * 1024
        if self.max_download_rate > 0:
            settings["download_rate_limit"] = self.max_download_rate * 1024

        session.apply_settings(settings)

        # Start DHT
        session.start_dht()

        # Add trackers
        session.add_dht_router("router.bittorrent.com", 6881)
        session.add_dht_router("router.utorrent.com", 6881)

        logger.info("Libtorrent session configured successfully")
        return session

    def _get_torrent_info(self, torrent_source: str) -> Any:
        """Get torrent info from magnet link or torrent file."""
        if not LIBTORRENT_AVAILABLE or lt is None:
            raise DependencyNotFoundError("libtorrent is not available")

        if torrent_source.startswith("magnet:"):
            # Parse magnet link
            return lt.parse_magnet_uri(torrent_source)  # type: ignore
        elif torrent_source.startswith(("http://", "https://")):
            # Download torrent file
            import urllib.request

            with tempfile.NamedTemporaryFile(
                suffix=".torrent", delete=False
            ) as tmp_file:
                urllib.request.urlretrieve(torrent_source, tmp_file.name)
                torrent_info = lt.torrent_info(tmp_file.name)  # type: ignore
                Path(tmp_file.name).unlink()  # Clean up temp file
                return {"ti": torrent_info}
        else:
            # Local torrent file
            torrent_path = Path(torrent_source)
            if not torrent_path.exists():
                raise TorrentDownloadError(f"Torrent file not found: {torrent_source}")
            return {"ti": lt.torrent_info(str(torrent_path))}  # type: ignore

    def download_with_libtorrent(
        self, torrent_source: str, timeout: int = 3600, sequential: bool = False
    ) -> Path:
        """
        Download torrent using libtorrent.

        Args:
            torrent_source: Magnet link, torrent file URL, or local torrent file path
            timeout: Download timeout in seconds
            sequential: Whether to download files sequentially

        Returns:
            Path to the downloaded content

        Raises:
            TorrentDownloadError: If download fails
            DependencyNotFoundError: If libtorrent is not available
        """
        if not LIBTORRENT_AVAILABLE or lt is None:
            raise DependencyNotFoundError(
                "libtorrent is not available. Please install python-libtorrent: "
                "pip install python-libtorrent"
            )

        try:
            self.session = self._setup_libtorrent_session()
            torrent_params = self._get_torrent_info(torrent_source)

            # Set save path
            torrent_params["save_path"] = str(self.download_path)

            if sequential and lt is not None:
                torrent_params["flags"] = lt.torrent_flags.sequential_download  # type: ignore

            # Add torrent to session
            if self.session is None:
                raise TorrentDownloadError("Session is not initialized")
            handle = self.session.add_torrent(torrent_params)

            logger.info(f"Starting torrent download: {handle.name()}")

            # Monitor download progress
            start_time = time.time()
            last_log_time = start_time
            while not handle.is_seed():
                current_time = time.time()

                # Check timeout
                if current_time - start_time > timeout:
                    raise TorrentDownloadError(
                        f"Download timeout after {timeout} seconds"
                    )

                status = handle.status()

                # Prepare progress info
                progress_info = {
                    "name": handle.name(),
                    "progress": status.progress * 100,
                    "download_rate": status.download_rate / 1024,  # KB/s
                    "upload_rate": status.upload_rate / 1024,  # KB/s
                    "num_peers": status.num_peers,
                    "total_size": status.total_wanted,
                    "downloaded": status.total_wanted_done,
                    "state": str(status.state),
                }

                # Call progress callback if provided
                if self.progress_callback:
                    self.progress_callback(progress_info)

                # Log progress periodically (every 10 seconds)
                if current_time - last_log_time >= 10:
                    logger.info(
                        f"Download progress: {progress_info['progress']:.1f}% "
                        f"({progress_info['download_rate']:.1f} KB/s) "
                        f"- {progress_info['num_peers']} peers"
                    )
                    last_log_time = current_time

                # Check for errors
                if status.error:
                    raise TorrentDownloadError(f"Torrent error: {status.error}")

                time.sleep(1)

            # Download completed
            download_path = self.download_path / handle.name()
            logger.info(f"Torrent download completed: {download_path}")

            # Remove torrent from session
            if self.session is not None:
                self.session.remove_torrent(handle)

            return download_path

        except Exception as e:
            if isinstance(e, (TorrentDownloadError, DependencyNotFoundError)):
                raise
            raise TorrentDownloadError(f"Failed to download torrent: {str(e)}") from e
        finally:
            if self.session:
                # Clean up session
                self.session = None

    def download_with_webtorrent_cli(self, torrent_source: str) -> Path:
        """
        Download torrent using webtorrent CLI as fallback.

        Args:
            torrent_source: Magnet link, torrent file URL, or local torrent file path

        Returns:
            Path to the downloaded content

        Raises:
            TorrentDownloadError: If download fails
            DependencyNotFoundError: If webtorrent CLI is not available
        """
        webtorrent_cli = shutil.which("webtorrent")
        if not webtorrent_cli:
            raise DependencyNotFoundError(
                "webtorrent CLI is not available. Please install it: npm install -g webtorrent-cli"
            )

        try:
            cmd = [
                webtorrent_cli,
                "download",
                torrent_source,
                "--out",
                str(self.download_path),
            ]
            logger.info(f"Running webtorrent command: {' '.join(cmd)}")

            from ..utils.subprocess import run_cmd

            rc, out, err = run_cmd(cmd, timeout=3600, capture_output=True)

            # Try to determine the download path from the output
            # This is a best-effort approach since webtorrent output format may vary
            output_lines = out.split("\n") if out else []
            for line in output_lines:
                if "Downloaded" in line and "to" in line:
                    # Extract path from output
                    parts = line.split("to")
                    if len(parts) > 1:
                        path_str = parts[-1].strip().strip("\"'")  # Remove quotes
                        download_path = Path(path_str)
                        if download_path.exists():
                            logger.info(f"Successfully downloaded to: {download_path}")
                            return download_path

            # If we can't parse the output, scan the download directory for new files
            logger.warning(
                "Could not parse webtorrent output, scanning download directory"
            )
            download_candidates = list(self.download_path.iterdir())
            if download_candidates:
                # Return the most recently modified item
                newest_path = max(download_candidates, key=lambda p: p.stat().st_mtime)
                logger.info(f"Found downloaded content: {newest_path}")
                return newest_path

            # Fallback: return the download directory
            logger.warning(
                f"No specific download found, returning download directory: {self.download_path}"
            )
            return self.download_path

        except Exception as e:
            # Normalize errors into TorrentDownloadError for upstream handling
            raise TorrentDownloadError(f"webtorrent CLI failed: {e}") from e

    def download(
        self, torrent_source: str, prefer_libtorrent: bool = True, **kwargs
    ) -> Path:
        """
        Download torrent using the best available method.

        Args:
            torrent_source: Magnet link, torrent file URL, or local torrent file path
            prefer_libtorrent: Whether to prefer libtorrent over webtorrent CLI
            **kwargs: Additional arguments passed to the download method

        Returns:
            Path to the downloaded content

        Raises:
            TorrentDownloadError: If all download methods fail
        """
        methods = []

        if prefer_libtorrent and LIBTORRENT_AVAILABLE:
            methods.extend(
                [
                    ("libtorrent", self.download_with_libtorrent),
                    ("webtorrent-cli", self.download_with_webtorrent_cli),
                ]
            )
        else:
            methods.extend(
                [
                    ("webtorrent-cli", self.download_with_webtorrent_cli),
                    ("libtorrent", self.download_with_libtorrent),
                ]
            )

        last_exception = None

        for method_name, method_func in methods:
            try:
                logger.info(f"Attempting download with {method_name}")
                if method_name == "libtorrent":
                    return method_func(torrent_source, **kwargs)
                else:
                    return method_func(torrent_source)
            except DependencyNotFoundError as e:
                logger.warning(f"{method_name} not available: {e}")
                last_exception = e
                continue
            except Exception as e:
                logger.error(f"{method_name} failed: {e}")
                last_exception = e
                continue

        # All methods failed
        raise TorrentDownloadError(
            f"All torrent download methods failed. Last error: {last_exception}"
        ) from last_exception


def download_torrent_with_webtorrent_cli(path: Path, url: str) -> Path:
    """
    Legacy function for backward compatibility.
    Download torrent using webtorrent CLI and return the download path.
    """
    downloader = TorrentDownloader(download_path=path.parent)
    return downloader.download_with_webtorrent_cli(url)
