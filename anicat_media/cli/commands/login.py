import click
from rich import print as rprint

import sys
import subprocess
from anicat_media.core.config import AppConfig
from anicat_media.core.constants import USER_CONFIG
from anicat_media.cli.config.loader import ConfigLoader


@click.command(help="Login to your AniList account")
@click.pass_obj
def login(config: AppConfig):
    """
    Login to AniList by opening the token URL and config file.
    """
    login_flow(config)


def login_flow(config: AppConfig):
    """
    The core logic for the AniList login process.
    """
    from anicat_media.core.constants import ANILIST_AUTH
    from ..config.generate import generate_config_toml_from_app_model

    rprint("[bold cyan]AniList Login[/]")

    # Ensure config file is up to date with all fields (including token placeholder)
    USER_CONFIG.write_text(
        generate_config_toml_from_app_model(config), encoding="utf-8"
    )

    rprint(
        f"Opening your browser for authentication: [link={ANILIST_AUTH}]{ANILIST_AUTH}[/link]"
    )
    click.launch(ANILIST_AUTH)

    rprint("\n[bold yellow]Opening your config file in your text editor...[/]")
    rprint(f"[dim]If it doesn't open, please find it at: {USER_CONFIG}[/]")

    if sys.platform == "darwin":
        try:
            subprocess.run(["open", "-t", str(USER_CONFIG)], check=False)
        except Exception:
            click.launch(str(USER_CONFIG))
    else:
        click.launch(str(USER_CONFIG))

    rprint("\n[bold green]Instructions:[/]")
    rprint("1. Copy the 'access_token' from the URL after authorizing.")
    rprint(
        r"2. Paste it in the file behind [bold white]token = [/] (located under the [bold white]\[anilist][/] section)."
    )
    rprint("3. Save ([bold white]Cmd+S[/]) and close the editor.")

    input("\nPress Enter here once you have saved and closed the file...")

    # Reload config to verify
    try:
        loader = ConfigLoader(config_path=USER_CONFIG)
        new_config = loader.load()

        if new_config.anilist.token:
            rprint("\n[bold green]Login successful! Enjoy Anicat.[/bold green]")
        else:
            rprint(
                "\n[bold red]No token detected in config.toml. Please try the login process again.[/bold red]"
            )

    except Exception as e:
        rprint(f"\n[bold red]Failed to reload config: {e}[/bold red]")
