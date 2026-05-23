from anicat_media.libs.player.mpv.player import MpvPlayer
from anicat_media.libs.player.params import PlayerParams
from anicat_media.core.config.infrastructure import MpvConfig


def test_mpv_player_skip_times_brackets():
    config = MpvConfig(args="", pre_args="")
    player = MpvPlayer(config)

    params = PlayerParams(
        url="https://example.com/anime.m3u8",
        title="Test Anime",
        query="Test Anime",
        episode="1",
        skip_times=[
            {"type": "op", "start": 30, "end": 120},
            {"type": "ed", "start": 1200, "end": 1320},
        ],
    )

    args = player._create_mpv_cli_options(params)

    # Assert that the skip_times option was formatted with bracket quoting
    expected_opt = "--script-opts=anicat_ui-skip_times=[op,30,120;ed,1200,1320]"
    assert expected_opt in args
