import json
from pathlib import Path
import httpx
import pytest
from unittest.mock import MagicMock, patch

from anicat_media.core.utils.graphql import execute_graphql
from anicat_media.libs.media_api.anilist.api import AniListApi
from anicat_media.core.config import AnilistConfig


def test_execute_graphql_fallback_to_expired_cache(tmp_path):
    """
    Test that execute_graphql returns the cache (even if expired) with the
    'X-Offline-Fallback: true' header when a network error occurs.
    """
    url = "https://graphql.anilist.co"
    graphql_file = tmp_path / "test_query.gql"
    graphql_file.write_text("query { Viewer { id } }")
    variables = {}

    # Mock client that raises connection error
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ConnectError("Connection timed out")

    # Set up some dummy cached data
    cached_payload = {"data": {"Viewer": {"id": 12345}}}

    # Patch the global cache used in execute_graphql
    with patch("anicat_media.core.utils.graphql._cache") as mock_cache:
        # get() returns the cached payload when ignoring TTL (ttl=float('inf'))
        mock_cache.get.side_effect = lambda u, q, v, ttl: cached_payload if ttl == float("inf") else None

        response = execute_graphql(
            url=url,
            httpx_client=mock_client,
            graphql_file=graphql_file,
            variables=variables,
            use_cache=True,
        )

        assert response.status_code == 200
        assert response.headers.get("X-Offline-Fallback") == "true"
        assert response.json() == cached_payload


def test_execute_graphql_no_cache_propagates_exception(tmp_path):
    """
    Test that execute_graphql propagates the connection exception when a network
    error occurs and no cached data is available.
    """
    url = "https://graphql.anilist.co"
    graphql_file = tmp_path / "test_query.gql"
    graphql_file.write_text("query { Viewer { id } }")
    variables = {}

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ConnectError("Unreachable")

    with patch("anicat_media.core.utils.graphql._cache") as mock_cache:
        # No cache exists at all
        mock_cache.get.return_value = None

        with pytest.raises(httpx.ConnectError):
            execute_graphql(
                url=url,
                httpx_client=mock_client,
                graphql_file=graphql_file,
                variables=variables,
                use_cache=True,
            )


def test_execute_graphql_400_does_not_use_offline_cache(tmp_path):
    """HTTP 4xx (e.g. invalid token) should not be treated as offline fallback."""
    url = "https://graphql.anilist.co"
    graphql_file = tmp_path / "test_query.gql"
    graphql_file.write_text("query { Viewer { id } }")
    variables = {}

    req = httpx.Request("POST", url)
    res = httpx.Response(400, request=req, json={"errors": [{"message": "Invalid token"}]})

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = res

    with patch("anicat_media.core.utils.graphql._cache") as mock_cache:
        # No fresh cache hit (normal ttl), and even if expired data exists,
        # 4xx should not use offline fallback.
        mock_cache.get.side_effect = (
            lambda u, q, v, ttl: None
            if ttl != float("inf")
            else {"data": {"Viewer": {"id": 12345}}}
        )

        with pytest.raises(httpx.HTTPStatusError):
            execute_graphql(
                url=url,
                httpx_client=mock_client,
                graphql_file=graphql_file,
                variables=variables,
                use_cache=True,
            )


def test_authenticate_retains_token_on_network_error():
    """
    Test that AniListApi's authenticate method does not erase or reset the token
    if the authentication call fails due to a network connection/timeout error.
    """
    config = AnilistConfig(token="original_secret_token")
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.headers = {}

    api = AniListApi(config=config, client=mock_client)
    api.token = "original_secret_token"

    # Make get_viewer_profile raise a connection error
    with patch.object(api, "get_viewer_profile", side_effect=httpx.ConnectError("Offline")):
        with pytest.raises(httpx.ConnectError):
            api.authenticate("new_token")

        # The token must NOT be erased or rolled back due to connection error; it should be retained!
        assert api.token == "new_token"
        assert api.http_client.headers["Authorization"] == "Bearer new_token"


def test_authenticate_invalid_token_returns_none_without_raising():
    """Invalid token HTTP status should be treated as auth failure, not offline/network."""
    config = AnilistConfig(token="")
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.headers = {}

    api = AniListApi(config=config, client=mock_client)

    req = httpx.Request("POST", "https://graphql.anilist.co")
    res = httpx.Response(400, request=req, json={"errors": [{"message": "Invalid token"}]})
    err = httpx.HTTPStatusError("400 Bad Request", request=req, response=res)

    with patch.object(api, "get_viewer_profile", side_effect=err):
        profile = api.authenticate("bad_token")

    assert profile is None
    assert api.token is None
    assert "Authorization" not in api.http_client.headers
