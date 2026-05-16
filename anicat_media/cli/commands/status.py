import click
import httpx
import sys

@click.command()
@click.pass_obj
def status(ctx):
    """Check the health and status of the background Anicat service."""
    host = "127.0.0.1"
    port = 13370
    url = f"http://{host}:{port}/api/status/health"
    
    click.echo(f"Checking Anicat service at {url}...")
    
    try:
        response = httpx.get(url, timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            click.secho("\n✅ Anicat is ONLINE", fg="green", bold=True)
            click.echo(f"  Version: {data.get('current_version', 'unknown')}")
            click.echo(f"  AniList: {'Connected' if data.get('api_authenticated') else 'Not Logged In'}")
            click.echo(f"  Network: {'Local Only (Safe)' if not data.get('is_offline') else 'Offline'}")
            
            if data.get('update_available'):
                click.secho("\n✨ An update is available! Install it via the Dashboard.", fg="amber")
        else:
            click.secho(f"\n⚠️ Service returned error: {response.status_code}", fg="yellow")
    except Exception:
        click.secho("\n❌ Anicat is OFFLINE", fg="red", bold=True)
        click.echo("  The background server is not running.")
        click.echo("  Start it with: 'anicat dashboard' or open the Dashboard app.")
        sys.exit(1)
