import logging
import sys
from typing import TYPE_CHECKING

import click
from click.core import ParameterSource

from anicat_media.core.config import AppConfig
from anicat_media.core.constants import CLI_NAME, USER_CONFIG, __version__
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
    "binge": "extra.binge",
    "discover": "extra.discover",
    "details": "extra.details",
    "track": "extra.track",
    "anilist": "anilist.cmd.anilist",
    "download": "download.download",
    "login": "login.login",
    "registry": "registry.registry",
    "worker": "worker.worker",
    "queue": "queue.queue",
    "completions": "completions.completions",
    "dashboard": "dashboard.dashboard",
    "stop": "stop.stop",
    "status": "status.status",
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


    if ctx.invoked_subcommand is None:
        from .commands.anilist import cmd

        ctx.invoke(cmd.anilist)
