import click
import subprocess
import os
import signal

@click.command(help="Stop the Anicat Dashboard server")
def stop():
    """Find and kill any running Anicat Dashboard processes."""
    try:
        # Use pgrep to find processes running uvicorn with 'anicat_media.api.main:create_app'
        # or just look for port 8000
        result = subprocess.run(["lsof", "-ti", ":13370"], capture_output=True, text=True)
        pids = result.stdout.strip().split("\n")
        
        if not pids or not pids[0]:
            click.echo("Anicat Dashboard is not running.")
            return

        click.echo(f"Stopping Anicat Dashboard (PIDs: {', '.join(pids)})...")
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
        
        click.echo("Anicat Dashboard has been stopped.")
    except Exception as e:
        click.echo(f"Error stopping dashboard: {e}")
