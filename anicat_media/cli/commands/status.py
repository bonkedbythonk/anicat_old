import click
import httpx
import sys
import json as _json

from ...core.constants import LOCAL_API_ORIGIN


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for scripting.")
@click.pass_obj
def status(ctx, as_json: bool = False):
    """Check the health and status of the background Anicat service."""
    url = f"{LOCAL_API_ORIGIN}/api/status/health"

    if not as_json:
        click.echo(f"Checking Anicat service at {url}...")

    try:
        response = httpx.get(url, timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            if as_json:
                click.echo(_json.dumps(data, indent=2))
                return
            click.secho("\n✅ Anicat is ONLINE", fg="green", bold=True)
            click.echo(f"  Version: {data.get('current_version', 'unknown')}")
            click.echo(
                f"  AniList: {'Connected' if data.get('api_authenticated') else 'Not Logged In'}"
            )
            click.echo(
                f"  Network: {'Online' if not data.get('is_offline') else 'Offline'}"
            )

            if data.get("update_available"):
                click.secho(
                    "\n✨ An update is available! Install it via the Dashboard.",
                    fg="amber",
                )
        else:
            if as_json:
                click.echo(
                    _json.dumps({"status": "error", "code": response.status_code})
                )
            else:
                click.secho(
                    f"\n⚠️ Service returned error: {response.status_code}", fg="yellow"
                )
    except Exception:
        if as_json:
            click.echo(
                _json.dumps(
                    {"status": "offline", "error": "Background server is not running."}
                )
            )
            sys.exit(1)
        click.secho("\n❌ Anicat is OFFLINE", fg="red", bold=True)
        click.echo("  The background server is not running.")
        click.echo("  Start it with: 'anicat dashboard' or open the Dashboard app.")
        sys.exit(1)
