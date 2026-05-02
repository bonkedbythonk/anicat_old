import click

from ...utils.lazyloader import LazyGroup
from . import examples

commands = {
    # "trending": "trending.trending",
    # "recent": "recent.recent",
    "search": "search.search",
    "download": "download.download",
    "downloads": "downloads.downloads",
    "stats": "stats.stats",
    "notifications": "notifications.notifications",
}


@click.group(
    cls=LazyGroup,
    name="anilist",
    root="anicat_media.cli.commands.anilist.commands",
    invoke_without_command=True,
    help="A beautiful interface that gives you access to a commplete streaming experience",
    short_help="Access all streaming options",
    lazy_subcommands=commands,
    epilog=examples.main,
)
@click.option(
    "--resume", is_flag=True, help="Resume from the last session (Not yet implemented)."
)
@click.pass_context
def anilist(ctx: click.Context, resume: bool):
    """
    The entry point for the 'anilist' command. If no subcommand is invoked,
    it launches the interactive TUI mode.
    """
    from ...interactive.session import session

    config = ctx.obj

    if ctx.invoked_subcommand is None:
        session.load_menus_from_folder("media")
        session.run(config, resume=resume)
