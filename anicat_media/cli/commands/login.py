import click
from rich import print as rprint
from pathlib import Path
import os
import shutil

from ...core.config import AppConfig
from ...core.constants import USER_CONFIG
from ..config.generate import generate_config_toml_from_app_model

@click.command(help="Login to your AniList account")
@click.pass_obj
def login(config: AppConfig):
    """
    Login to AniList by providing an OAuth token.
    """
    rprint("[bold cyan]AniList Login[/]")
    rprint("Please visit this link to generate your token: [link=https://anilist.co/settings/developer]https://anilist.co/settings/developer[/]")
    rprint("[dim](Create a 'New Client' if you haven't, then use the redirect link to get your token)[/]")
    
    token = click.prompt("Paste your token here", hide_input=True).strip()
    
    if not token:
        rprint("[red]Error: Token cannot be empty.[/]")
        return

    # Update config object
    config.anilist.token = token
    
    # Save to config.toml
    try:
        toml_content = generate_config_toml_from_app_model(config)
        USER_CONFIG.write_text(toml_content, encoding="utf-8")
        rprint("[bold green]Login successful![/bold green]")
        rprint("[dim]Your token has been saved to your config.toml[/]")
    except Exception as e:
        rprint(f"[red]Failed to save token to config: {e}[/]")
