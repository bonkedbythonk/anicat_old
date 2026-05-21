"""System commands group — worker, stop, completions."""

import click


@click.group(short_help="System admin commands (worker, stop, completions)")
def system():
    """System administration commands for the background service."""
    pass


@system.command(short_help="Run the background worker")
@click.pass_obj
def worker(config):
    """Start the background worker for notifications and downloads."""
    from .worker import worker as _worker
    _worker.invoke(click.get_current_context().parent)


@system.command(short_help="Stop the dashboard server")
def stop():
    """Stop the running Anicat Dashboard server."""
    from .stop import stop as _stop
    _stop.invoke(click.get_current_context().parent)


@system.command(short_help="Generate shell completions")
@click.option("--bash", is_flag=True, help="Print bash completions")
@click.option("--zsh", is_flag=True, help="Print zsh completions")
@click.option("--fish", is_flag=True, help="Print fish completions")
def completions(bash=False, zsh=False, fish=False):
    """Generate shell completion scripts for your terminal."""
    from .completions import completions as _completions
    ctx = click.get_current_context()
    # Build args
    args = []
    if bash: args.append("--bash")
    if zsh: args.append("--zsh")
    if fish: args.append("--fish")
    ctx.invoke(_completions)
