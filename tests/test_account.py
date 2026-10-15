"""Tests for the account endpoints."""

# pylint: disable=too-many-positional-arguments

from typing import Any

import pytest
from aiohttp.web import FileField, Request
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from aioseafile import Seafile, SeafileAuthenticationError
from tests import load_fixtures

HOST = "localhost:8000"
JSON = {"Content-Type": "application/json"}
LIBRARY_ID = "7f8ab5cb-54d0-40d3-bee2-be26ce1806af"
USER_ID = "d6074febe21348149e70779dea1a6ef0@auth.local"
SUCCESS = '{"success": true}'


def _json(status: int, text: str) -> object:
    return ResponsesMockServer.Response(status=status, headers=JSON, text=text)


def _fixture(name: str) -> str:
    return load_fixtures(f"account/{name}")


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "path", "query", "fixture"),
    [
        pytest.param("get_user_profile", (), {}, "/api/v2.1/user/", {}, "user_profile.json", id="get_user_profile"),
        pytest.param(
            "search_users",
            ("account",),
            {"include_self": False},
            "/api2/search-user/",
            {"q": "account", "include_self": "0"},
            "search_users.json",
            id="search_users",
        ),
        pytest.param(
            "get_user_avatar",
            ("account@example.com",),
            {},
            "/api2/avatars/user/account@example.com/resized/80/",
            {},
            "user_avatar.json",
            id="get_user_avatar_default",
        ),
        pytest.param(
            "get_user_avatar",
            (USER_ID, 64),
            {},
            f"/api2/avatars/user/{USER_ID}/resized/64/",
            {},
            "user_avatar_custom.json",
            id="get_user_avatar_custom",
        ),
        pytest.param("get_devices", (), {}, "/api2/devices/", {}, "devices.json", id="get_devices"),
        pytest.param(
            "get_activities",
            (),
            {"page": 2, "per_page": 3, "op_user": "admin@example.com"},
            "/api/v2.1/activities/",
            {"page": "2", "per_page": "3", "op_user": "admin@example.com"},
            "activities.json",
            id="get_activities",
        ),
        pytest.param(
            "get_activities",
            (),
            {},
            "/api/v2.1/activities/",
            {"page": "1", "per_page": "25"},
            "activities.json",
            id="get_activities_default",
        ),
        pytest.param(
            "get_notifications",
            (),
            {},
            "/api/v2.1/notifications/",
            {"page": "1", "per_page": "25"},
            "notifications.json",
            id="get_notifications",
        ),
        pytest.param(
            "get_sdoc_notifications",
            (),
            {"page": 2, "per_page": 10},
            "/api/v2.1/sdoc-notifications/",
            {"page": "2", "per_page": "10"},
            "notifications.json",
            id="get_sdoc_notifications",
        ),
        pytest.param(
            "get_all_notifications",
            (),
            {},
            "/api/v2.1/all-notifications/",
            {"page": "1", "per_page": "25"},
            "all_notifications.json",
            id="get_all_notifications",
        ),
        pytest.param(
            "get_unseen_system_notifications",
            (),
            {},
            "/api/v2.1/sys-user-notifications/unseen/",
            {},
            "system_notifications.json",
            id="get_unseen_system_notifications",
        ),
        pytest.param("get_invitations", (), {}, "/api/v2.1/invitations/", {}, "invitations.json", id="get_invitations"),
        pytest.param("get_invitation", ("3f2a9c1b7e",), {}, "/api/v2.1/invitations/3f2a9c1b7e/", {}, "invitation.json", id="get_invitation"),
    ],
)
async def test_reads(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    snapshot: SnapshotAssertion,
    method: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    path: str,
    query: dict[str, str],
    fixture: str,
) -> None:
    """Test read endpoints send the right query and are parsed into models."""

    async def handler(request: Request) -> object:
        assert dict(request.query) == query
        return _json(200, _fixture(fixture))

    aresponses.add(HOST, path, "GET", handler)
    assert await getattr(seafile_client, method)(*args, **kwargs) == snapshot


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "http_method", "path", "form", "response"),
    [
        pytest.param(
            "update_account_info",
            (),
            {"name": "account-user", "file_updates_email_interval": 3600, "collaborate_email_interval": 0},
            "PUT",
            "/api2/account/info/",
            {"name": "account-user", "file_updates_email_interval": "3600", "collaborate_email_interval": "0"},
            _fixture("account_info_updated.json"),
            id="update_account_info",
        ),
        pytest.param(
            "update_user_profile",
            (),
            {"name": "account-user", "telephone": "0612345678", "list_in_address_book": True},
            "PUT",
            "/api/v2.1/user/",
            {"name": "account-user", "telephone": "0612345678", "list_in_address_book": "true"},
            _fixture("user_profile.json"),
            id="update_user_profile",
        ),
        pytest.param(
            "update_user_profile",
            (),
            {"contact_email": "account@example.com"},
            "PUT",
            "/api/v2.1/user/",
            {"contact_email": "account@example.com"},
            _fixture("user_profile.json"),
            id="update_user_profile_contact_email",
        ),
        pytest.param(
            "change_password",
            ("old-pw", "New-Pw-12345!"),
            {},
            "POST",
            "/api/v2.1/user/reset-password/",
            {"old_password": "old-pw", "new_password": "New-Pw-12345!"},
            SUCCESS,
            id="change_password",
        ),
        pytest.param("get_client_login_token", (), {}, "POST", "/api2/client-login/", {}, _fixture("client_login.json"), id="client_login"),
        pytest.param("get_client_login_token", (), {}, "POST", "/api2/client-login/", {}, "{}", id="client_login_2fa"),
        pytest.param(
            "unlink_device",
            ("linux", "f74fd60f5415e6f3db882c01c069f9313867bd72"),
            {},
            "DELETE",
            "/api2/devices/",
            {"platform": "linux", "device_id": "f74fd60f5415e6f3db882c01c069f9313867bd72", "wipe_device": "false"},
            SUCCESS,
            id="unlink_device",
        ),
        pytest.param(
            "unlink_device",
            ("android", "a1b2c3d4e5f60718"),
            {"wipe": True},
            "DELETE",
            "/api2/devices/",
            {"platform": "android", "device_id": "a1b2c3d4e5f60718", "wipe_device": "true"},
            SUCCESS,
            id="wipe_device",
        ),
        pytest.param("mark_notifications_seen", (), {}, "PUT", "/api/v2.1/notifications/", {}, SUCCESS, id="mark_notifications_seen"),
        pytest.param(
            "mark_notification_seen",
            (5,),
            {},
            "PUT",
            "/api/v2.1/notification/",
            {"notice_id": "5"},
            SUCCESS,
            id="mark_notification_seen",
        ),
        pytest.param("delete_notifications", (), {}, "DELETE", "/api/v2.1/notifications/", {}, SUCCESS, id="delete_notifications"),
        pytest.param(
            "mark_sdoc_notifications_seen",
            (),
            {},
            "PUT",
            "/api/v2.1/sdoc-notifications/",
            {},
            SUCCESS,
            id="mark_sdoc_notifications_seen",
        ),
        pytest.param(
            "mark_sdoc_notification_seen",
            (7,),
            {},
            "PUT",
            "/api/v2.1/sdoc-notification/",
            {"notice_id": "7"},
            SUCCESS,
            id="mark_sdoc_notification_seen",
        ),
        pytest.param(
            "delete_sdoc_notifications",
            (),
            {},
            "DELETE",
            "/api/v2.1/sdoc-notifications/",
            {},
            SUCCESS,
            id="delete_sdoc_notifications",
        ),
        pytest.param(
            "mark_all_notifications_seen",
            (),
            {},
            "PUT",
            "/api/v2.1/all-notifications/",
            {},
            SUCCESS,
            id="mark_all_notifications_seen",
        ),
        pytest.param(
            "mark_system_notification_seen",
            (1,),
            {},
            "PUT",
            "/api/v2.1/sys-user-notifications/1/seen/",
            {},
            _fixture("system_notification_seen.json"),
            id="mark_system_notification_seen",
        ),
        pytest.param(
            "create_invitation",
            ("guest@example.com",),
            {},
            "POST",
            "/api/v2.1/invitations/",
            {"type": "guest", "accepter": "guest@example.com"},
            _fixture("invitation.json"),
            id="create_invitation",
        ),
        pytest.param("delete_invitation", ("3f2a9c1b7e",), {}, "DELETE", "/api/v2.1/invitations/3f2a9c1b7e/", {}, "", id="delete_invitation"),
        pytest.param(
            "revoke_invitation",
            ("8b7c6d5e4f",),
            {},
            "POST",
            "/api/v2.1/invitations/8b7c6d5e4f/revoke/",
            {},
            SUCCESS,
            id="revoke_invitation",
        ),
    ],
)
async def test_writes(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    snapshot: SnapshotAssertion,
    method: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    http_method: str,
    path: str,
    form: dict[str, str],
    response: str,
) -> None:
    """Test write endpoints send the right method and form, and parse the response."""

    async def handler(request: Request) -> object:
        assert request.method == http_method
        assert dict(await request.post()) == form
        return _json(200, response)

    aresponses.add(HOST, path, http_method, handler)
    assert await getattr(seafile_client, method)(*args, **kwargs) == snapshot


async def test_create_invitations(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test a batch invitation sends every address."""

    async def handler(request: Request) -> object:
        form = await request.post()
        assert form.getall("type") == ["guest"]
        assert form.getall("accepter") == ["guest@example.com", "not-an-email"]
        return _json(200, _fixture("invitations_batch.json"))

    aresponses.add(HOST, "/api/v2.1/invitations/batch/", "POST", handler)
    assert await seafile_client.create_invitations(["guest@example.com", "not-an-email"]) == snapshot


async def test_upload_avatar(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test the avatar is sent as a multipart file."""

    async def handler(request: Request) -> object:
        form = await request.post()
        avatar = form["avatar"]
        assert isinstance(avatar, FileField)
        assert avatar.filename == "me.jpg"
        assert avatar.content_type == "image/jpeg"
        assert avatar.file.read() == b"image-data"
        return _json(200, _fixture("upload_avatar.json"))

    aresponses.add(HOST, "/api/v2.1/user-avatar/", "POST", handler)
    url = await seafile_client.upload_avatar(b"image-data", "me.jpg", content_type="image/jpeg")
    assert url.endswith("/resized/256/32d3ca5e23f4ccf1e4c8660c40e75f33.png")


async def test_logout_device(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test logging out drops the token, so later requests fail locally."""

    async def handler(request: Request) -> object:
        assert request.headers["Authorization"] == "Token test_token"
        return _json(200, "{}")

    aresponses.add(HOST, "/api2/logout-device/", "POST", handler)
    await seafile_client.logout_device()
    with pytest.raises(SeafileAuthenticationError):
        await seafile_client.get_account_info()


async def test_device_token_not_kept(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test the device token in the response is not stored on the model."""
    aresponses.add(HOST, "/api2/devices/", "GET", _json(200, _fixture("devices.json")))
    devices = await seafile_client.get_devices()
    assert all(not hasattr(device, "key") for device in devices)


async def test_ping_and_server_info(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test the reachability checks and the edition and quota helpers."""
    aresponses.add(HOST, "/api2/ping/", "GET", _json(200, '"pong"'))
    aresponses.add(HOST, "/api2/auth/ping/", "GET", _json(200, '"pong"'))
    aresponses.add(HOST, "/api2/server-info/", "GET", _json(200, load_fixtures("server_info.json")))
    aresponses.add(HOST, "/api2/account/info/", "GET", _json(200, _fixture("account_info_updated.json")))
    assert await seafile_client.ping()
    assert await seafile_client.auth_ping()
    assert not (await seafile_client.get_server_info()).is_pro
    account = await seafile_client.get_account_info()
    assert account.quota_unlimited
    assert account.quota_total is None
