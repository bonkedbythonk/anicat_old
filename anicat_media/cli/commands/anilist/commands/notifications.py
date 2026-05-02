import click
from anicat_media.core.config import AppConfig
from rich.console import Console
from rich.table import Table


@click.command(help="Check for new AniList notifications (e.g., for airing episodes).")
@click.pass_obj
def notifications(config: AppConfig):
    """
    Displays unread notifications from AniList.
    Running this command will also mark the notifications as read on the AniList website.
    """
    from anicat_media.cli.service.feedback import FeedbackService
    from anicat_media.libs.media_api.api import create_api_client

    from ....service.auth import AuthService

    feedback = FeedbackService(config)
    console = Console()
    auth = AuthService(config.general.media_api)
    api_client = create_api_client(config.general.media_api, config)

    token = auth.resolve_token(config)
    if token:
        api_client.authenticate(token)

    if not api_client.is_authenticated():
        feedback.error(
            "Authentication Required",
            "You are not logged in. Please run 'anicat login' to continue.",
        )
        return

    with feedback.progress("Fetching notifications..."):
        notifs = api_client.get_notifications()

    if not notifs:
        feedback.success("All caught up!", "You have no new notifications.")
        return

    table = Table(
        title="🔔 AniList Notifications", show_header=True, header_style="bold magenta"
    )
    table.add_column("Date", style="dim", width=12)
    table.add_column("Anime Title", style="cyan")
    table.add_column("Details", style="green")

    for notif in sorted(notifs, key=lambda n: n.created_at, reverse=True):
        title = notif.media.title.english or notif.media.title.romaji or "Unknown"
        date_str = notif.created_at.strftime("%Y-%m-%d")
        details = f"Episode {notif.episode} has aired!"

        table.add_row(date_str, title, details)

    console.print(table)
    feedback.info(
        "Notifications have been marked as read on AniList.",
    )
