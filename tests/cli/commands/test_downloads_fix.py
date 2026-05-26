from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from anicat_media.cli.commands.downloads import downloads
from anicat_media.core.config import AppConfig


def test_downloads_list_does_not_shadow_builtin():
    assert downloads.commands["list"].name == "list"
    assert downloads.commands["list"].callback.__name__ == "list_queue"

    runner = CliRunner()
    config = AppConfig()

    with patch("anicat_media.cli.commands.downloads._get_ctx") as mock_get_ctx:
        mock_ctx = MagicMock()
        mock_get_ctx.return_value = mock_ctx
        mock_ctx.media_registry.get_all_media_records.return_value = []

        result = runner.invoke(downloads, ["list"], obj=config)
        assert result.exit_code == 0
        assert "Download queue is empty" in result.output
