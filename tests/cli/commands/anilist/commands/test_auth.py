from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from anicat_media.cli.commands.anilist.commands.auth import auth


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.user.interactive = True
    return config


@pytest.fixture
def mock_auth_service():
    with patch("anicat_media.cli.service.auth.AuthService") as mock:
        yield mock


@pytest.fixture
def mock_feedback_service():
    with patch("anicat_media.cli.service.feedback.FeedbackService") as mock:
        yield mock


@pytest.fixture
def mock_selector():
    with patch("anicat_media.libs.selectors.selector.create_selector") as mock:
        yield mock


@pytest.fixture
def mock_api_client():
    with patch("anicat_media.libs.media_api.api.create_api_client") as mock:
        yield mock


@pytest.fixture
def mock_webbrowser():
    with patch("anicat_media.cli.commands.anilist.commands.auth.webbrowser") as mock:
        yield mock


def test_auth_with_token_argument(
    runner,
    mock_config,
    mock_auth_service,
    mock_feedback_service,
    mock_api_client,
):
    """Test 'anicat anilist auth <token>' via positional argument."""
    api_client_instance = mock_api_client.return_value
    profile_mock = MagicMock()
    profile_mock.name = "testuser"
    api_client_instance.authenticate.return_value = profile_mock

    auth_service_instance = mock_auth_service.return_value
    auth_service_instance.resolve_token.return_value = "test_token"
    auth_service_instance.get_auth.return_value = None

    result = runner.invoke(auth, ["test_token"], obj=mock_config)

    assert result.exit_code == 0
    auth_service_instance.resolve_token.assert_called_with(explicit_token="test_token")
    api_client_instance.authenticate.assert_called_with("test_token")
    auth_service_instance.save_user_profile.assert_called_with(
        profile_mock, "test_token"
    )


def test_auth_with_token_flag(
    runner,
    mock_config,
    mock_auth_service,
    mock_feedback_service,
    mock_api_client,
):
    """Test 'anicat anilist auth --token <token>' via CLI flag."""
    api_client_instance = mock_api_client.return_value
    profile_mock = MagicMock()
    profile_mock.name = "testuser"
    api_client_instance.authenticate.return_value = profile_mock

    auth_service_instance = mock_auth_service.return_value
    auth_service_instance.resolve_token.return_value = "flag_token"
    auth_service_instance.get_auth.return_value = None

    result = runner.invoke(auth, ["--token", "flag_token"], obj=mock_config)

    assert result.exit_code == 0
    auth_service_instance.resolve_token.assert_called_with(explicit_token="flag_token")
    api_client_instance.authenticate.assert_called_with("flag_token")
    auth_service_instance.save_user_profile.assert_called_with(
        profile_mock, "flag_token"
    )


def test_auth_token_flag_overrides_positional_arg(
    runner,
    mock_config,
    mock_auth_service,
    mock_feedback_service,
    mock_api_client,
):
    """Test that --token flag takes priority over positional argument."""
    api_client_instance = mock_api_client.return_value
    profile_mock = MagicMock()
    profile_mock.name = "testuser"
    api_client_instance.authenticate.return_value = profile_mock

    auth_service_instance = mock_auth_service.return_value
    auth_service_instance.resolve_token.return_value = "flag_token"
    auth_service_instance.get_auth.return_value = None

    result = runner.invoke(
        auth, ["--token", "flag_token", "positional_token"], obj=mock_config
    )

    assert result.exit_code == 0
    # --token flag should take priority over positional arg
    auth_service_instance.resolve_token.assert_called_with(explicit_token="flag_token")


def test_auth_no_token_shows_instructions(
    runner,
    mock_config,
    mock_auth_service,
    mock_feedback_service,
    mock_webbrowser,
):
    """Test 'anicat anilist auth' with no token anywhere shows instructions, no interactive prompt."""
    auth_service_instance = mock_auth_service.return_value
    auth_service_instance.resolve_token.return_value = None

    mock_webbrowser.open.return_value = True

    result = runner.invoke(auth, [], obj=mock_config)

    assert result.exit_code == 0
    # Should open browser
    mock_webbrowser.open.assert_called_once()
    # Should show warning about missing token
    feedback_instance = mock_feedback_service.return_value
    feedback_instance.warning.assert_called_once()


def test_auth_status_logged_in(
    runner, mock_config, mock_auth_service, mock_feedback_service
):
    """Test 'anicat anilist auth --status' when logged in."""
    auth_service_instance = mock_auth_service.return_value
    user_data_mock = MagicMock()
    user_data_mock.user_profile = "testuser"
    auth_service_instance.get_auth.return_value = user_data_mock

    result = runner.invoke(auth, ["--status"], obj=mock_config)

    assert result.exit_code == 0
    feedback_instance = mock_feedback_service.return_value
    feedback_instance.info.assert_called_with("Logged in as: testuser")


def test_auth_status_logged_out(
    runner, mock_config, mock_auth_service, mock_feedback_service
):
    """Test 'anicat anilist auth --status' when logged out."""
    auth_service_instance = mock_auth_service.return_value
    auth_service_instance.get_auth.return_value = None

    result = runner.invoke(auth, ["--status"], obj=mock_config)

    assert result.exit_code == 0
    feedback_instance = mock_feedback_service.return_value
    feedback_instance.error.assert_called()


def test_auth_logout(
    runner, mock_config, mock_auth_service, mock_feedback_service, mock_selector
):
    """Test 'anicat anilist auth --logout'."""
    selector_instance = mock_selector.return_value
    selector_instance.confirm.return_value = True

    result = runner.invoke(auth, ["--logout"], obj=mock_config)

    assert result.exit_code == 0
    auth_service_instance = mock_auth_service.return_value
    auth_service_instance.clear_user_profile.assert_called_once()
    feedback_instance = mock_feedback_service.return_value
    feedback_instance.info.assert_called_with("You have been logged out.")


def test_auth_logout_cancel(
    runner, mock_config, mock_auth_service, mock_feedback_service, mock_selector
):
    """Test 'anicat anilist auth --logout' when user cancels."""
    selector_instance = mock_selector.return_value
    selector_instance.confirm.return_value = False

    result = runner.invoke(auth, ["--logout"], obj=mock_config)

    assert result.exit_code == 0
    auth_service_instance = mock_auth_service.return_value
    auth_service_instance.clear_user_profile.assert_not_called()


def test_auth_already_logged_in_relogin_yes(
    runner,
    mock_config,
    mock_auth_service,
    mock_feedback_service,
    mock_selector,
    mock_api_client,
):
    """Test 'anicat anilist auth --token <token>' when already logged in and user chooses to re-authenticate."""
    auth_service_instance = mock_auth_service.return_value
    auth_profile_mock = MagicMock()
    auth_profile_mock.user_profile.name = "testuser"
    auth_service_instance.resolve_token.return_value = "new_token"
    auth_service_instance.get_auth.return_value = auth_profile_mock

    selector_instance = mock_selector.return_value
    selector_instance.confirm.return_value = True

    api_client_instance = mock_api_client.return_value
    new_profile_mock = MagicMock()
    new_profile_mock.name = "newuser"
    api_client_instance.authenticate.return_value = new_profile_mock

    result = runner.invoke(auth, ["--token", "new_token"], obj=mock_config)

    assert result.exit_code == 0
    auth_service_instance.save_user_profile.assert_called_with(
        new_profile_mock, "new_token"
    )


def test_auth_already_logged_in_relogin_no(
    runner,
    mock_config,
    mock_auth_service,
    mock_feedback_service,
    mock_selector,
):
    """Test 'anicat anilist auth --token <token>' when already logged in and user declines re-auth."""
    auth_service_instance = mock_auth_service.return_value
    auth_profile_mock = MagicMock()
    auth_profile_mock.user_profile.name = "testuser"
    auth_service_instance.resolve_token.return_value = "new_token"
    auth_service_instance.get_auth.return_value = auth_profile_mock

    selector_instance = mock_selector.return_value
    selector_instance.confirm.return_value = False

    result = runner.invoke(auth, ["--token", "new_token"], obj=mock_config)

    assert result.exit_code == 0
    auth_service_instance.save_user_profile.assert_not_called()


def test_auth_invalid_token(
    runner,
    mock_config,
    mock_auth_service,
    mock_feedback_service,
    mock_api_client,
):
    """Test that an invalid/expired token shows clear error message."""
    auth_service_instance = mock_auth_service.return_value
    auth_service_instance.resolve_token.return_value = "bad_token"
    auth_service_instance.get_auth.return_value = None

    api_client_instance = mock_api_client.return_value
    api_client_instance.authenticate.return_value = None

    result = runner.invoke(auth, ["--token", "bad_token"], obj=mock_config)

    assert result.exit_code == 0
    feedback_instance = mock_feedback_service.return_value
    feedback_instance.error.assert_called_once()
    # Verify the error message mentions the token being invalid
    call_args = feedback_instance.error.call_args
    assert "failed" in call_args[0][0].lower() or "invalid" in str(call_args).lower()
