import webbrowser

import click

from .....core.config.model import AppConfig
from .....core.constants import ANILIST_AUTH


@click.command(help="Login to your AniList account to enable progress tracking.")
@click.option("--status", "-s", is_flag=True, help="Check current login status.")
@click.option("--logout", "-l", is_flag=True, help="Log out and erase credentials.")
@click.option(
    "--token",
    "-t",
    "token_flag",
    type=str,
    default=None,
    help="AniList access token (raw string or path to a token file).",
)
@click.argument("token_arg", required=False, type=str)
@click.pass_obj
def auth(
    config: AppConfig,
    status: bool,
    logout: bool,
    token_flag: str | None,
    token_arg: str | None,
):
    """
    Handles user authentication and credential management.

    This command allows you to log in to your AniList account to enable
    progress tracking and other features.

    Your token is resolved automatically from multiple sources in this priority:

    \b
    1. --token flag:     anicat anilist auth --token <token>
    2. Positional arg:   anicat anilist auth <token_or_path>
    3. Env variable:     $ANILIST_TOKEN
    4. Token file:       ~/.config/anicat/token.txt
    5. Config file:      'token' key under [anilist] in config.toml
    6. Saved session:    Previously authenticated session (auth.json)

    If no token is found, the browser will open the AniList authorization
    page with instructions on how to set your token.
    """
    from .....libs.media_api.api import create_api_client
    from ....service.auth import AuthService
    from ....service.feedback import FeedbackService
    from .....core.theme import ICONS

    auth_service = AuthService("anilist")
    feedback = FeedbackService(config)

    if status:
        _handle_status(auth_service, feedback)
        return

    if logout:
        _handle_logout(auth_service, feedback, config)
        return

    # --token flag takes priority over the positional argument
    effective_token_input = token_flag or token_arg

    # Resolve from all available sources
    token = auth_service.resolve_token(explicit_token=effective_token_input)

    if not token:
        _show_auth_instructions(feedback)
        return

    # Check if user is already logged in with this token
    existing_profile = auth_service.get_auth()
    if existing_profile:
        from .....libs.selectors.selector import create_selector

        selector = create_selector(config)
        if not selector.confirm(
            f"You are already logged in as {existing_profile.user_profile.name}. "
            "Would you like to re-authenticate?"
        ):
            return

    # Validate the token against the AniList API
    api_client = create_api_client("anilist", config)
    profile = api_client.authenticate(token.strip())

    if profile:
        auth_service.save_user_profile(profile, token.strip())
        feedback.info(f"Successfully logged in as {profile.name}! {ICONS.SPARKLES}")
    else:
        feedback.error(
            "Login failed.",
            "The token may be invalid or expired.\n"
            "Visit the following URL to obtain a new token:\n"
            f"  {ANILIST_AUTH}",
        )


def _handle_status(auth_service, feedback):
    """Display current authentication status."""
    user_data = auth_service.get_auth()
    if user_data:
        feedback.info(f"Logged in as: {user_data.user_profile}")
    else:
        feedback.error(
            "Not logged in.",
            "Run 'anicat anilist auth --token <token>' or set $ANILIST_TOKEN to authenticate.",
        )


def _handle_logout(auth_service, feedback, config):
    """Handle the logout flow."""
    from .....libs.selectors.selector import create_selector

    selector = create_selector(config)
    if selector.confirm("Are you sure you want to log out and erase your token?"):
        auth_service.clear_user_profile()
        feedback.info("You have been logged out.")


def _show_auth_instructions(feedback):
    """Show instructions when no token is found — never prompts for interactive input."""
    feedback.warning("No AniList token found in any source.")

    open_success = webbrowser.open(ANILIST_AUTH, new=2)
    if open_success:
        feedback.info("Your browser has been opened to the AniList authorization page.")
    else:
        feedback.info(f"Open this URL in your browser to authorize:\n  {ANILIST_AUTH}")

    feedback.info(
        "After authorizing, save your token using one of these methods:\n"
        "  • anicat anilist auth --token <token>\n"
        "  • export ANILIST_TOKEN='<token>'\n"
        "  • Save token to ~/.config/anicat/token.txt\n"
        "  • Add 'token = \"<token>\"' under [anilist] in config.toml\n"
        "\n"
        "Then run 'anicat anilist auth' again to complete authentication."
    )
