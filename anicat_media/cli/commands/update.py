"""Update command for Anicat CLI."""

from typing import TYPE_CHECKING

import click
from rich import print

from ..utils.update import check_for_updates, print_release_json, update_app

if TYPE_CHECKING:
    from ...core.config import AppConfig


@click.command(
    help="Update Anicat to the latest version from the main branch",
    short_help="Update Anicat",
)
@click.pass_obj
def update(config: "AppConfig") -> None:
    """
    Update Anicat to the latest version from GitHub.
    """
    from ...core.updater import perform_update
    perform_update()
