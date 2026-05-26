from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from anicat_media.core.config import AppConfig


@click.command(help="Print out your anilist stats")
@click.pass_obj
def stats(config: "AppConfig"):
    import shutil
    import subprocess

    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    from .....libs.media_api.api import create_api_client
    from ....service.auth import AuthService
    from ....service.feedback import FeedbackService

    console = Console()

    feedback = FeedbackService(config)
    auth = AuthService(config.general.media_api)

    media_api_client = create_api_client(config.general.media_api, config)

    try:
        # Check authentication
        token = auth.resolve_token(config)
        if token:
            if not media_api_client.authenticate(token):
                feedback.error(
                    "Authentication Required",
                    "You are not logged in. Please run 'anicat login' to continue.",
                )
                raise click.Abort()
        else:
            feedback.error(
                "Authentication Required",
                "You are not logged in. Please run 'anicat login' to continue.",
            )
            raise click.Abort()

        profile = auth.get_auth()
        if not profile:
            feedback.error("No saved profile found after authentication.")
            raise click.Abort()

        # Check if kitten is available for image display
        KITTEN_EXECUTABLE = shutil.which("kitten")
        if not KITTEN_EXECUTABLE:
            feedback.warning("Kitten not found - profile image will not be displayed")
        else:
            # Display profile image using kitten icat
            if profile.user_profile.avatar_url:
                console.clear()
                image_x = int(console.size.width * 0.1)
                image_y = int(console.size.height * 0.1)
                img_w = console.size.width // 3
                img_h = console.size.height // 3

                image_process = subprocess.run(
                    [
                        KITTEN_EXECUTABLE,
                        "icat",
                        "--clear",
                        "--place",
                        f"{img_w}x{img_h}@{image_x}x{image_y}",
                        profile.user_profile.avatar_url,
                    ],
                    check=False,
                )

                if image_process.returncode != 0:
                    feedback.warning("Failed to display profile image")

        # Display user information
        about_text = getattr(profile, "about", "") or "No description available"

        console.print(
            Panel(
                Markdown(about_text),
                title=f"📊 {profile.user_profile.name}'s Profile",
            )
        )

        # You can add more stats here if the API provides them
        feedback.success("User profile displayed successfully")

    except Exception as e:
        feedback.error("Unexpected error occurred", str(e))
        raise click.Abort()
