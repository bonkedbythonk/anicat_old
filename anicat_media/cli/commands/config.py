import click

from anicat_media.core.config import AppConfig


@click.group(
    help="Manage your config with ease",
    short_help="Manage your config",
    invoke_without_command=True,
    epilog="""
\b
\b\bExamples:
  # Edit your config in your default editor 
  # NB: If it opens vim or vi exit with `:q`
  anicat config
\b
  # get the path of the config file
  anicat config path
\b
  # open the config file in your default system editor (macOS)
  anicat config open
\b 
  # view the current contents of your config
  anicat config view
""",
)
@click.pass_context
def config(ctx: click.Context):
    """
    Manage your configuration. If no subcommand is provided, it opens the config in your default terminal editor.
    """
    if ctx.invoked_subcommand is None:
        from anicat_media.core.constants import USER_CONFIG

        click.edit(filename=str(USER_CONFIG))


@config.command(name="path", help="Print the config location and exit")
def config_path():
    from anicat_media.core.constants import USER_CONFIG

    print(USER_CONFIG)


@config.command(name="view", help="View the current contents of your config")
@click.pass_obj
def config_view(user_config: AppConfig):
    from rich.console import Console
    from rich.syntax import Syntax

    from ..config.generate import generate_config_toml_from_app_model

    console = Console()
    config_toml = generate_config_toml_from_app_model(user_config)
    syntax = Syntax(
        config_toml,
        "ini",
        theme=user_config.general.pygment_style,
        line_numbers=True,
        word_wrap=True,
    )
    console.print(syntax)


@config.command(
    name="view-json", help="View the current contents of your config in json format"
)
@click.pass_obj
def config_view_json(user_config: AppConfig):
    import json

    print(json.dumps(user_config.model_dump(mode="json")))




@config.command(
    name="open", help="Open the config file in your default system editor (macOS)"
)
def config_open():
    import sys
    import subprocess

    from anicat_media.core.constants import USER_CONFIG

    print(f"Opening config at: {USER_CONFIG}")
    if sys.platform == "darwin":
        try:
            subprocess.run(["open", "-t", str(USER_CONFIG)], check=True)
        except Exception as e:
            click.echo(f"Failed to open config with 'open -t': {e}. Falling back to 'open'...", err=True)
            try:
                subprocess.run(["open", str(USER_CONFIG)], check=True)
            except Exception as e2:
                click.echo(f"Failed to open config: {e2}", err=True)
    else:
        try:
            # Fallback for non-macOS or if open fails
            click.launch(str(USER_CONFIG))
        except Exception as e:
            click.echo(f"Failed to open config: {e}", err=True)


@config.command(
    name="desktop-entry", help="Generate the desktop entry for anicat (Linux only)"
)
@click.pass_obj
def config_desktop_entry(user_config: AppConfig):
    _generate_desktop_entry(user_config)


@config.command(
    name="update",
    help="Persist all the config options passed to anicat to your config file",
)
@click.pass_obj
def config_update(user_config: AppConfig):
    from anicat_media.core.constants import USER_CONFIG
    from ..config.generate import generate_config_toml_from_app_model

    USER_CONFIG.write_text(
        generate_config_toml_from_app_model(user_config), encoding="utf-8"
    )
    print("Update successful")





def _generate_desktop_entry(config: AppConfig):
    """
    Generates a desktop entry for Anicat.
    """
    import shutil
    import sys
    from pathlib import Path
    from textwrap import dedent

    from rich import print

    from ...libs.selectors.selector import create_selector

    from anicat_media.core.constants import (
        CLI_NAME,
        ICON_PATH,
        PLATFORM,
        USER_APPLICATIONS,
        __version__,
    )

    EXECUTABLE = shutil.which("anicat")
    if EXECUTABLE:
        cmds = f"{EXECUTABLE} --selector rofi anilist"
    else:
        cmds = f"{sys.executable} -m anicat --selector rofi anilist"

    # TODO: Get funs of the other platforms to complete this lol
    if PLATFORM == "win32":
        print(
            "Not implemented; the author thinks its not straight forward so welcomes lovers of windows to try and implement it themselves or to switch to a proper os like arch linux or pray the author gets bored 😜"
        )
    elif PLATFORM == "darwin":
        print(
            "Not implemented; the author thinks its not straight forward so welcomes lovers of mac to try and implement it themselves  or to switch to a proper os like arch linux or pray the author gets bored 😜"
        )
    else:
        desktop_entry = dedent(
            f"""
            [Desktop Entry]
            Name={CLI_NAME.title()}
            Type=Application
            version={__version__}
            Path={Path().home()}
            Comment=Watch anime from your terminal 
            Terminal=false
            Icon={ICON_PATH}
            Exec={cmds}
            Categories=Entertainment
        """
        )
        desktop_entry_path = USER_APPLICATIONS / f"{CLI_NAME}.desktop"
        if desktop_entry_path.exists():
            selector = create_selector(config)
            if not selector.confirm(
                f"The file already exists {desktop_entry_path}; or would you like to rewrite it",
                default=False,
            ):
                return
        with open(desktop_entry_path, "w") as f:
            f.write(desktop_entry)
        with open(desktop_entry_path) as f:
            print(f"Successfully wrote \n{f.read()}")
