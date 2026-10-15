"""Tests for the aioseafile client."""

# pylint: disable=protected-access,too-many-arguments,too-many-positional-arguments
import asyncio
import json

import pytest
from aiohttp.web import Request
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from aioseafile import (
    Seafile,
    SeafileAuthenticationError,
    SeafileConnectionError,
    SeafileError,
    SeafileNotFoundError,
    SeafilePermissionError,
    SeafileTimeoutError,
    SeafileTwoFactorRequiredError,
)
from tests import load_fixtures

HOST = "localhost:8000"
JSON = {"Content-Type": "application/json"}


def _json(status: int, text: str, headers: dict[str, str] | None = None) -> object:
    return ResponsesMockServer.Response(status=status, headers={**JSON, **(headers or {})}, text=text)


async def test_internal_session(aresponses: ResponsesMockServer) -> None:
    """Test an internal session is created and closed."""
    aresponses.add(HOST, "/api2/ping/", "GET", _json(200, '"pong"'))
    async with Seafile(api_url="http://localhost:8000") as client:
        assert await client.ping()


async def test_base_path(aresponses: ResponsesMockServer) -> None:
    """Test a server hosted under a sub path."""
    aresponses.add(HOST, "/seafile/api2/auth/ping/", "GET", _json(200, '"pong"'))
    async with Seafile(api_url="http://localhost:8000/seafile/", token="test_token") as client:
        assert await client.auth_ping()


async def test_token_header(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test the token is sent in the Authorization header."""

    async def handler(request: Request) -> object:
        assert request.headers["Authorization"] == "Token test_token"
        return _json(200, '"pong"')

    aresponses.add(HOST, "/api2/auth/ping/", "GET", handler)
    assert await seafile_client.auth_ping()


async def test_no_token() -> None:
    """Test an authenticated request without a token."""
    async with Seafile(api_url="http://localhost:8000") as client:
        with pytest.raises(SeafileAuthenticationError):
            await client.get_account_info()


async def test_timeout(aresponses: ResponsesMockServer) -> None:
    """Test request timeout."""

    async def response_handler(_: Request) -> object:
        await asyncio.sleep(0.2)
        return _json(200, '"pong"')

    aresponses.add(HOST, "/api2/ping/", "GET", response_handler)
    async with Seafile(api_url="http://localhost:8000", request_timeout=0.1, max_retries=0) as client:
        with pytest.raises(SeafileTimeoutError):
            await client.ping()


@pytest.mark.parametrize(
    ("status", "exception"),
    [
        pytest.param(401, SeafileAuthenticationError, id="unauthorized"),
        pytest.param(403, SeafilePermissionError, id="forbidden"),
        pytest.param(404, SeafileNotFoundError, id="not_found"),
        pytest.param(500, SeafileConnectionError, id="server_error"),
    ],
)
async def test_http_errors(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    status: int,
    exception: type[SeafileError],
) -> None:
    """Test HTTP errors are mapped to exceptions."""
    aresponses.add(HOST, "/api2/account/info/", "GET", _json(status, '{"detail": "error"}'))
    with pytest.raises(exception):
        await seafile_client.get_account_info()


async def test_retry_on_server_error(aresponses: ResponsesMockServer) -> None:
    """Test a transient server error is retried."""
    aresponses.add(HOST, "/api2/auth/ping/", "GET", _json(502, "{}"))
    aresponses.add(HOST, "/api2/auth/ping/", "GET", _json(200, '"pong"'))
    async with Seafile(api_url="http://localhost:8000", token="test_token", max_retries=1) as client:
        assert await client.auth_ping()


async def test_unexpected_content_type(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test a non-JSON response."""
    aresponses.add(HOST, "/api2/ping/", "GET", aresponses.Response(status=200, headers={"Content-Type": "text/html"}, text="<html>"))
    with pytest.raises(SeafileError):
        await seafile_client.ping()


async def test_get_auth_token(aresponses: ResponsesMockServer) -> None:
    """Test exchanging credentials for a token."""

    async def handler(request: Request) -> object:
        assert await request.post() == {"username": "user@example.com", "password": "secret"}
        assert request.headers["X-SEAFILE-OTP"] == "123456"
        return _json(200, '{"token": "new_token"}')

    aresponses.add(HOST, "/api2/auth-token/", "POST", handler)
    aresponses.add(HOST, "/api2/auth/ping/", "GET", _json(200, '"pong"'))
    async with Seafile(api_url="http://localhost:8000") as client:
        assert await client.get_auth_token("user@example.com", "secret", otp="123456") == "new_token"
        assert client._token == "new_token"
        assert await client.auth_ping()


@pytest.mark.parametrize(
    ("headers", "exception"),
    [
        pytest.param({}, SeafileAuthenticationError, id="invalid_credentials"),
        pytest.param({"X-Seafile-OTP": "required"}, SeafileTwoFactorRequiredError, id="otp_required"),
    ],
)
async def test_get_auth_token_rejected(
    aresponses: ResponsesMockServer,
    headers: dict[str, str],
    exception: type[SeafileError],
) -> None:
    """Test rejected credentials."""
    body = json.dumps({"non_field_errors": ["Unable to login with provided credentials."]})
    aresponses.add(HOST, "/api2/auth-token/", "POST", _json(400, body, headers))
    async with Seafile(api_url="http://localhost:8000") as client:
        with pytest.raises(exception):
            await client.get_auth_token("user@example.com", "wrong")


async def test_get_auth_token_server_error(aresponses: ResponsesMockServer) -> None:
    """Test an unexpected status from the token endpoint."""
    aresponses.add(HOST, "/api2/auth-token/", "POST", _json(500, "{}"))
    async with Seafile(api_url="http://localhost:8000") as client:
        with pytest.raises(SeafileConnectionError):
            await client.get_auth_token("user@example.com", "secret")


async def test_get_auth_token_timeout(aresponses: ResponsesMockServer) -> None:
    """Test a timeout on the token endpoint."""

    async def response_handler(_: Request) -> object:
        await asyncio.sleep(0.2)
        return _json(200, '{"token": "x"}')

    aresponses.add(HOST, "/api2/auth-token/", "POST", response_handler)
    async with Seafile(api_url="http://localhost:8000", request_timeout=0.1) as client:
        with pytest.raises(SeafileTimeoutError):
            await client.get_auth_token("user@example.com", "secret")


async def test_get_auth_token_invalid_json(aresponses: ResponsesMockServer) -> None:
    """Test a non-JSON body from the token endpoint."""
    aresponses.add(HOST, "/api2/auth-token/", "POST", aresponses.Response(status=200, text="<html>"))
    async with Seafile(api_url="http://localhost:8000") as client:
        with pytest.raises(SeafileConnectionError):
            await client.get_auth_token("user@example.com", "secret")


@pytest.mark.parametrize(
    ("method", "path", "fixture"),
    [
        pytest.param("get_server_info", "/api2/server-info/", "server_info.json", id="get_server_info"),
        pytest.param("get_account_info", "/api2/account/info/", "account_info.json", id="get_account_info"),
        pytest.param("get_account_info", "/api2/account/info/", "account_info_quota.json", id="account_info_quota"),
        pytest.param("get_libraries", "/api2/repos/", "repos.json", id="get_libraries"),
        pytest.param("get_admin_system_info", "/api/v2.1/admin/sysinfo/", "admin_sysinfo.json", id="get_admin_system_info"),
    ],
)
async def test_endpoints(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    snapshot: SnapshotAssertion,
    method: str,
    path: str,
    fixture: str,
) -> None:
    """Test endpoints are parsed into models."""
    aresponses.add(HOST, path, "GET", _json(200, load_fixtures(fixture)))
    assert await getattr(seafile_client, method)() == snapshot


async def test_library(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test the details of one library."""
    aresponses.add(HOST, "/api2/repos/6490a72d-4c26-4020-ad00-1b72fb2c88c9/", "GET", _json(200, load_fixtures("repo.json")))
    assert await seafile_client.get_library("6490a72d-4c26-4020-ad00-1b72fb2c88c9") == snapshot


async def test_admin_libraries_paginated(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test all pages of the admin library list are fetched."""
    page = json.loads(load_fixtures("admin_libraries.json"))
    first = {"page_info": {"has_next_page": True, "current_page": 1}, "repos": page["repos"][:1]}
    second = {"page_info": {"has_next_page": False, "current_page": 2}, "repos": page["repos"][1:]}
    aresponses.add(HOST, "/api/v2.1/admin/libraries/?page=1&per_page=1", "GET", _json(200, json.dumps(first)), match_querystring=True)
    aresponses.add(HOST, "/api/v2.1/admin/libraries/?page=2&per_page=1", "GET", _json(200, json.dumps(second)), match_querystring=True)
    assert await seafile_client.get_admin_libraries(per_page=1) == snapshot


@pytest.mark.parametrize(
    ("fixture", "quota_total", "unlimited"),
    [
        pytest.param("account_info.json", None, True, id="unlimited"),
        pytest.param("account_info_quota.json", 100000000, False, id="limited"),
    ],
)
async def test_account_quota(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    fixture: str,
    quota_total: int | None,
    unlimited: bool,
) -> None:
    """Test the negative total Seafile uses for an unlimited quota."""
    aresponses.add(HOST, "/api2/account/info/", "GET", _json(200, load_fixtures(fixture)))
    account = await seafile_client.get_account_info()
    assert account.quota_total == quota_total
    assert account.quota_unlimited is unlimited


async def test_server_info_pro(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test detecting the Professional edition."""
    aresponses.add(HOST, "/api2/server-info/", "GET", _json(200, '{"version": "14.0.9", "features": ["seafile-basic", "seafile-pro"]}'))
    assert (await seafile_client.get_server_info()).is_pro
