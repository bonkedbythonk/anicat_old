import logging
import shutil
import sys
from typing import TYPE_CHECKING

import click
from click.core import ParameterSource

from ..core.config import AppConfig
from ..core.constants import CLI_NAME, USER_CONFIG, __version__
from .config import ConfigLoader
from .options import options_from_model
from .utils.exception import setup_exceptions_handler
from .utils.lazyloader import LazyGroup
from .utils.logging import setup_logging

if TYPE_CHECKING:
    from typing import TypedDict

    from typing_extensions import Unpack

    class Options(TypedDict):
        no_config: bool | None
        trace: bool | None
        dev: bool | None
        log: bool | None
        rich_traceback: bool | None
        rich_traceback_theme: str


logger = logging.getLogger(__name__)

commands = {
    "config": "config.config",
    "search": "search.search",
    "anilist": "anilist.anilist",
    "download": "download.download",
    "update": "update.update",
    "registry": "registry.registry",
    "worker": "worker.worker",
    "queue": "queue.queue",
    "completions": "completions.completions",
}


@click.group(
    cls=LazyGroup,
    root="anicat_media.cli.commands",
    invoke_without_command=True,
    lazy_subcommands=commands,
    context_settings=dict(auto_envvar_prefix=CLI_NAME),
)
@click.version_option(__version__, "--version")
@click.option("--no-config", is_flag=True, help="Don't load the user config file.")
@click.option(
    "--trace", is_flag=True, help="Controls Whether to display tracebacks or not"
)
@click.option("--dev", is_flag=True, help="Controls Whether the app is in dev mode")
@click.option("--log", is_flag=True, help="Controls Whether to log")
@click.option(
    "--rich-traceback",
    is_flag=True,
    help="Controls Whether to display a rich traceback",
)
@click.option(
    "--rich-traceback-theme",
    default="github-dark",
    help="Controls Whether to display a rich traceback",
)
@options_from_model(AppConfig)
@click.pass_context
def cli(ctx: click.Context, **options: "Unpack[Options]"):
    """
    The main entry point for the Anicat CLI.
    """
    setup_logging(options["log"])
    setup_exceptions_handler(
        options["trace"],
        options["dev"],
        options["rich_traceback"],
        options["rich_traceback_theme"],
    )
    
    # Silent background update check
    try:
        from ..core.updater import check_for_updates
        import threading
        threading.Thread(target=check_for_updates, args=(True,), daemon=True).start()
    except Exception:
        pass

    logger.info(f"Current Command: {' '.join(sys.argv)}")
    cli_overrides = {}
    param_lookup = {p.name: p for p in ctx.command.params}

    for param_name, param_value in ctx.params.items():
        source = ctx.get_parameter_source(param_name)
        if source in (ParameterSource.ENVIRONMENT, ParameterSource.COMMANDLINE):
            parameter = param_lookup.get(param_name)

            if (
                parameter
                and hasattr(parameter, "model_name")
                and hasattr(parameter, "field_name")
            ):
                model_name = getattr(parameter, "model_name")
                field_name = getattr(parameter, "field_name")

                if model_name not in cli_overrides:
                    cli_overrides[model_name] = {}
                cli_overrides[model_name][field_name] = param_value

    loader = ConfigLoader(config_path=USER_CONFIG)
    config = (
        AppConfig.model_validate(cli_overrides)
        if options["no_config"]
        else loader.load(cli_overrides)
    )
    ctx.obj = config

    if config.general.welcome_screen:
        import time

        from ..core.constants import APP_CACHE_DIR, USER_NAME, SUPPORT_PROJECT_URL

        last_welcomed_at_file = APP_CACHE_DIR / ".last_welcome"
        should_welcome = False
        if last_welcomed_at_file.exists():
            try:
                last_welcomed_at = float(
                    last_welcomed_at_file.read_text(encoding="utf-8")
                )
                # runs once a month
                if (time.time() - last_welcomed_at) > 30 * 24 * 3600:
                    should_welcome = True

            except Exception as e:
                logger.warning(f"Failed to read welcome screen timestamp: {e}")

        else:
            should_welcome = True
        if should_welcome:
            last_welcomed_at_file.write_text(str(time.time()), encoding="utf-8")

            from ..libs.selectors.selector import create_selector

            selector = create_selector(config)
            if selector.confirm(f"""\
[green]How are you, {USER_NAME} 🙂?
If you enjoy the project and would like to support it, you can give it a star at {SUPPORT_PROJECT_URL}.
Would you like to open the project page? Select yes to continue — otherwise, enjoy your terminal-anime browsing experience 😁.[/]
You can disable this message by turning off the welcome_screen option in the config, if you don't disable it, the cli will show it again the next month.
"""):
                from webbrowser import open

                open(SUPPORT_PROJECT_URL)

    if ctx.invoked_subcommand is None:
        from .commands.anilist import cmd

        ctx.invoke(cmd.anilist)
