"""Tests for the admin endpoints."""

# pylint: disable=too-many-positional-arguments

import json
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

import pytest
from aiohttp.web import Request
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from aioseafile.models.admin import AdminDevicePlatform, AdminLibraryStatus
from tests import load_fixtures

if TYPE_CHECKING:
    from aioseafile import Seafile

HOST = "localhost:8000"
SHARE_TOKEN = "129e091b06f9449484a1"
UPLOAD_TOKEN = "6add6885ca2343a99c71"
JSON = {"Content-Type": "application/json"}
ADMIN = "/api/v2.1/admin"
LIBRARY_ID = "6ef89a2f-9a67-416f-b34a-eaaa167275f5"
USER = "77880dad4fce473ebe441ea29f9c01de@auth.local"
SUCCESS = '{"success": true}'
RANGE = "start=2026-10-14+00:00:00&end=2026-10-15+00:00:00"


def _json(status: int, text: str) -> object:
    return ResponsesMockServer.Response(status=status, headers=JSON, text=text)


def _fixture(name: str) -> str:
    return load_fixtures(f"admin/{name}")


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "path", "fixture"),
    [
        pytest.param("get_admin_system_info", (), {}, f"{ADMIN}/sysinfo/", "sysinfo.json", id="system_info"),
        pytest.param(
            "get_admin_total_storage",
            (datetime(2026, 10, 14, tzinfo=UTC), datetime(2026, 10, 15, tzinfo=UTC)),
            {},
            f"{ADMIN}/statistics/total-storage/?{RANGE}",
            "total_storage.json",
            id="total_storage",
        ),
        pytest.param(
            "get_admin_active_users",
            (datetime(2026, 10, 14, tzinfo=UTC), datetime(2026, 10, 15, tzinfo=UTC)),
            {},
            f"{ADMIN}/statistics/active-users/?{RANGE}",
            "active_users.json",
            id="active_users",
        ),
        pytest.param(
            "get_admin_file_operations",
            (datetime(2026, 10, 14, tzinfo=UTC), datetime(2026, 10, 15, tzinfo=UTC)),
            {},
            f"{ADMIN}/statistics/file-operations/?{RANGE}",
            "file_operations.json",
            id="file_operations",
        ),
        pytest.param(
            "get_admin_system_traffic",
            (datetime(2026, 10, 14, tzinfo=UTC), datetime(2026, 10, 15, tzinfo=UTC)),
            {},
            f"{ADMIN}/statistics/system-traffic/?{RANGE}",
            "system_traffic.json",
            id="system_traffic",
        ),
        pytest.param("get_admin_system_metrics", (), {}, f"{ADMIN}/statistics/system-metrics/", "system_metrics.json", id="system_metrics"),
        pytest.param("search_admin_users", ("admin-test",), {}, f"{ADMIN}/search-user/?query=admin-test", "search_user.json", id="search_users"),
        pytest.param("get_admin_user", (USER,), {}, f"{ADMIN}/users/{USER}/", "user.json", id="user"),
        pytest.param(
            "get_admin_libraries",
            (),
            {"order_by": "size"},
            f"{ADMIN}/libraries/?order_by=size&page=1&per_page=100",
            "libraries.json",
            id="libraries_order_by",
        ),
        pytest.param(
            "search_admin_libraries",
            (),
            {"name": "lib", "owner": "admin@example.com"},
            f"{ADMIN}/libraries/?name=lib&owner=admin@example.com",
            "libraries_search.json",
            id="search_libraries",
        ),
        pytest.param("get_admin_library", (LIBRARY_ID,), {}, f"{ADMIN}/libraries/{LIBRARY_ID}/", "library.json", id="library"),
        pytest.param(
            "get_admin_library_history",
            (LIBRARY_ID,),
            {"page": 2, "per_page": 2},
            f"{ADMIN}/libraries/{LIBRARY_ID}/history/?page=2&per_page=2",
            "library_history.json",
            id="library_history",
        ),
        pytest.param(
            "get_admin_trash_libraries",
            (),
            {},
            f"{ADMIN}/trash-libraries/?page=1&per_page=100",
            "trash_libraries.json",
            id="trash_libraries",
        ),
        pytest.param(
            "get_admin_trash_libraries",
            (),
            {"owner": USER},
            f"{ADMIN}/trash-libraries/?owner={USER}",
            "trash_libraries.json",
            id="trash_libraries_owner",
        ),
        pytest.param(
            "get_admin_devices",
            (),
            {"platform": AdminDevicePlatform.DESKTOP},
            f"{ADMIN}/devices/?platform=desktop&page=1&per_page=50",
            "devices.json",
            id="devices",
        ),
        pytest.param("get_admin_device_errors", (), {}, f"{ADMIN}/device-errors/?page=1&per_page=100", "device_errors.json", id="device_errors"),
        pytest.param(
            "get_admin_upload_links",
            (),
            {"order_by": "view_cnt", "direction": "asc"},
            f"{ADMIN}/upload-links/?order_by=view_cnt&direction=asc&page=1&per_page=100",
            "upload_links.json",
            id="upload_links",
        ),
        pytest.param("get_admin_share_link", (SHARE_TOKEN,), {}, f"{ADMIN}/share-links/{SHARE_TOKEN}/", "share_link.json", id="share_link"),
        pytest.param(
            "get_admin_upload_link",
            (UPLOAD_TOKEN,),
            {},
            f"{ADMIN}/upload-links/{UPLOAD_TOKEN}/",
            "upload_link.json",
            id="upload_link",
        ),
        pytest.param("search_admin_groups", ("admin",), {}, f"{ADMIN}/groups/?name=admin", "groups.json", id="search_groups"),
        pytest.param(
            "get_admin_login_logs",
            (),
            {"emails": ["admin@example.com", "user@example.com"]},
            f"{ADMIN}/logs/login-logs/?email=admin@example.com&email=user@example.com&page=1&per_page=100",
            "login_logs.json",
            id="login_logs",
        ),
        pytest.param(
            "get_admin_file_access_logs",
            (),
            {"library_ids": [LIBRARY_ID], "page": 2, "per_page": 10},
            f"{ADMIN}/logs/file-access-logs/?repo={LIBRARY_ID}&page=2&per_page=10",
            "file_access_logs.json",
            id="file_access_logs",
        ),
        pytest.param(
            "get_admin_file_update_logs",
            (),
            {"emails": ["admin@example.com"]},
            f"{ADMIN}/logs/file-update-logs/?email=admin@example.com&page=1&per_page=100",
            "file_update_logs.json",
            id="file_update_logs",
        ),
        pytest.param(
            "get_admin_share_permission_logs",
            (),
            {"from_emails": ["admin@example.com"], "to_groups": ["3"]},
            f"{ADMIN}/logs/share-permission-logs/?from_email=admin@example.com&to_group=3&page=1&per_page=100",
            "share_permission_logs.json",
            id="share_permission_logs",
        ),
        pytest.param(
            "get_admin_permission_audit",
            (date(2026, 10, 1), date(2026, 10, 15)),
            {},
            f"{ADMIN}/logs/perm-audit/?start=2026-10-01&end=2026-10-15",
            "permission_audit.json",
            id="permission_audit",
        ),
        pytest.param(
            "get_admin_notifications",
            (),
            {"username": "admin@example.com", "per_page": 2},
            f"{ADMIN}/notifications/?username=admin@example.com&page=1&per_page=2",
            "notifications.json",
            id="notifications",
        ),
        pytest.param("get_admin_system_notifications", (), {}, f"{ADMIN}/sys-notifications/", "system_notifications.json", id="system_notifications"),
        pytest.param(
            "get_admin_user_notifications",
            (),
            {},
            f"{ADMIN}/sys-user-notifications/?page=1&per_page=100",
            "user_notifications.json",
            id="user_notifications",
        ),
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
    fixture: str,
) -> None:
    """Test admin reads send the right query and parse the response."""
    aresponses.add(HOST, path, "GET", _json(200, _fixture(fixture)), match_querystring=True)
    assert await getattr(seafile_client, method)(*args, **kwargs) == snapshot


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "http_method", "path", "form", "response"),
    [
        pytest.param(
            "create_admin_user",
            ("admin-test@example.com", "secret"),
            {"name": "Admin Test", "quota_total": 100},
            "POST",
            f"{ADMIN}/users/",
            {
                "email": "admin-test@example.com",
                "password": "secret",
                "name": "Admin Test",
                "is_staff": "false",
                "is_active": "true",
                "quota_total": "100",
            },
            "user_create.json",
            id="create_user",
        ),
        pytest.param(
            "update_admin_user",
            (USER,),
            {"quota_total": 200, "is_active": False, "is_staff": True, "role": "guest"},
            "PUT",
            f"{ADMIN}/users/{USER}/",
            {"is_staff": "true", "is_active": "false", "quota_total": "200", "role": "guest"},
            "user.json",
            id="update_user",
        ),
        pytest.param("delete_admin_user", (USER,), {}, "DELETE", f"{ADMIN}/users/{USER}/", {}, None, id="delete_user"),
        pytest.param(
            "create_admin_library",
            ("admin-lib",),
            {"owner": USER},
            "POST",
            f"{ADMIN}/libraries/",
            {"name": "admin-lib", "owner": USER},
            "library.json",
            id="create_library",
        ),
        pytest.param(
            "update_admin_library",
            (LIBRARY_ID,),
            {"name": "admin-lib2", "owner": USER, "status": AdminLibraryStatus.READ_ONLY},
            "PUT",
            f"{ADMIN}/libraries/{LIBRARY_ID}/",
            {"name": "admin-lib2", "owner": USER, "status": "read-only"},
            "library_transfer.json",
            id="update_library",
        ),
        pytest.param("delete_admin_library", (LIBRARY_ID,), {}, "DELETE", f"{ADMIN}/libraries/{LIBRARY_ID}/", {}, None, id="delete_library"),
        pytest.param(
            "restore_admin_trash_library", (LIBRARY_ID,), {}, "PUT", f"{ADMIN}/trash-libraries/{LIBRARY_ID}/", {}, None, id="restore_trash_library"
        ),
        pytest.param(
            "delete_admin_trash_library", (LIBRARY_ID,), {}, "DELETE", f"{ADMIN}/trash-libraries/{LIBRARY_ID}/", {}, None, id="delete_trash_library"
        ),
        pytest.param("clean_admin_trash_libraries", (), {}, "DELETE", f"{ADMIN}/trash-libraries/", {}, None, id="clean_trash"),
        pytest.param(
            "clean_admin_trash_libraries", (), {"owner": USER}, "DELETE", f"{ADMIN}/trash-libraries/", {"owner": USER}, None, id="clean_trash_owner"
        ),
        pytest.param(
            "delete_admin_device",
            ("admin@example.com", "linux", "0000000000000000000000000000000000000001"),
            {"wipe": True},
            "DELETE",
            f"{ADMIN}/devices/",
            {"user": "admin@example.com", "platform": "linux", "device_id": "0000000000000000000000000000000000000001", "wipe_device": "true"},
            None,
            id="delete_device",
        ),
        pytest.param("delete_admin_device_errors", (), {}, "DELETE", f"{ADMIN}/device-errors/", {}, None, id="delete_device_errors"),
        pytest.param(
            "delete_admin_share_link",
            (SHARE_TOKEN,),
            {},
            "DELETE",
            f"{ADMIN}/share-links/{SHARE_TOKEN}/",
            {},
            None,
            id="delete_share_link",
        ),
        pytest.param(
            "delete_admin_upload_link",
            (UPLOAD_TOKEN,),
            {},
            "DELETE",
            f"{ADMIN}/upload-links/{UPLOAD_TOKEN}/",
            {},
            None,
            id="delete_upload_link",
        ),
        pytest.param(
            "create_admin_group",
            ("admin-group",),
            {"owner": "admin@example.com"},
            "POST",
            f"{ADMIN}/groups/",
            {"group_name": "admin-group", "group_owner": "admin@example.com"},
            "group.json",
            id="create_group",
        ),
        pytest.param(
            "update_admin_group",
            (4,),
            {"name": "admin-group2", "owner": USER, "quota": -2},
            "PUT",
            f"{ADMIN}/groups/4/",
            {"name": "admin-group2", "new_owner": USER, "quota": "-2"},
            "group.json",
            id="update_group",
        ),
        pytest.param("delete_admin_group", (4,), {}, "DELETE", f"{ADMIN}/groups/4/", {}, None, id="delete_group"),
        pytest.param(
            "create_admin_system_notification",
            ("admin-banner test",),
            {},
            "POST",
            f"{ADMIN}/sys-notifications/",
            {"msg": "admin-banner test"},
            "system_notification.json",
            id="create_system_notification",
        ),
        pytest.param(
            "set_admin_current_system_notification",
            (1,),
            {},
            "PUT",
            f"{ADMIN}/sys-notifications/1/",
            {},
            "system_notification_current.json",
            id="set_current_system_notification",
        ),
        pytest.param(
            "delete_admin_system_notification", (1,), {}, "DELETE", f"{ADMIN}/sys-notifications/1/", {}, None, id="delete_system_notification"
        ),
        pytest.param(
            "create_admin_user_notification",
            ("admin announcement", USER),
            {},
            "POST",
            f"{ADMIN}/sys-user-notifications/",
            {"msg": "admin announcement", "username": USER},
            "user_notification.json",
            id="create_user_notification",
        ),
        pytest.param(
            "delete_admin_user_notification", (2,), {}, "DELETE", f"{ADMIN}/sys-user-notifications/2/", {}, None, id="delete_user_notification"
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
    response: str | None,
) -> None:
    """Test admin writes send the right form and parse the response."""

    async def handler(request: Request) -> object:
        assert dict(await request.post()) == form
        return _json(200, _fixture(response) if response else SUCCESS)

    aresponses.add(HOST, path, http_method, handler)
    assert await getattr(seafile_client, method)(*args, **kwargs) == snapshot


@pytest.mark.parametrize(
    ("method", "http_method", "args", "form", "keep_days"),
    [
        pytest.param("get_admin_library_history_limit", "GET", (LIBRARY_ID,), {}, -1, id="get"),
        pytest.param("set_admin_library_history_limit", "PUT", (LIBRARY_ID, 30), {"keep_days": "30"}, 30, id="set"),
    ],
)
async def test_history_limit(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    method: str,
    http_method: str,
    args: tuple[Any, ...],
    form: dict[str, str],
    keep_days: int,
) -> None:
    """Test reading and setting the history limit of a library."""

    async def handler(request: Request) -> object:
        assert dict(await request.post()) == form
        return _json(200, json.dumps({"keep_days": keep_days}))

    aresponses.add(HOST, f"{ADMIN}/libraries/{LIBRARY_ID}/history-limit/", http_method, handler)
    assert await getattr(seafile_client, method)(*args) == keep_days


async def test_users_paginated(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test the extra user each page returns is not duplicated."""
    users = json.loads(_fixture("users.json"))["data"]
    first = {"data": users[:2], "total_count": 3}
    second = {"data": users[1:], "total_count": 3}
    aresponses.add(HOST, f"{ADMIN}/users/?is_active=1&page=1&per_page=1", "GET", _json(200, json.dumps(first)), match_querystring=True)
    aresponses.add(HOST, f"{ADMIN}/users/?is_active=1&page=2&per_page=1", "GET", _json(200, json.dumps(second)), match_querystring=True)
    aresponses.add(
        HOST,
        f"{ADMIN}/users/?is_active=1&page=3&per_page=1",
        "GET",
        _json(200, json.dumps({"data": users[2:], "total_count": 3})),
        match_querystring=True,
    )
    result = await seafile_client.get_admin_users(is_active=True, per_page=1)
    assert [user.contact_email for user in result] == ["admin@example.com", "user@example.com", "admin-test@example.com"]
    assert result == snapshot


async def test_users_empty_page(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test fetching stops on an empty page even if the count says otherwise."""
    aresponses.add(
        HOST, f"{ADMIN}/users/?role=guest&page=1&per_page=100", "GET", _json(200, '{"data": [], "total_count": 5}'), match_querystring=True
    )
    assert await seafile_client.get_admin_users(role="guest") == []


async def test_share_links_paginated(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test all pages of the share link list are fetched."""
    page = json.loads(_fixture("share_links.json"))
    for number in (1, 2, 3):
        body = {"share_link_list": page["share_link_list"][number - 1 : number], "count": 3}
        aresponses.add(HOST, f"{ADMIN}/share-links/?page={number}&per_page=1", "GET", _json(200, json.dumps(body)), match_querystring=True)
    assert await seafile_client.get_admin_share_links(per_page=1) == snapshot


async def test_groups_paginated(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test all pages of the group list are fetched."""
    groups = json.loads(_fixture("groups.json"))["groups"]
    first = {"page_info": {"has_next_page": True, "current_page": 1}, "groups": groups[:2]}
    second = {"page_info": {"has_next_page": False, "current_page": 2}, "groups": groups[2:]}
    aresponses.add(HOST, f"{ADMIN}/groups/?page=1&per_page=2", "GET", _json(200, json.dumps(first)), match_querystring=True)
    aresponses.add(HOST, f"{ADMIN}/groups/?page=2&per_page=2", "GET", _json(200, json.dumps(second)), match_querystring=True)
    assert await seafile_client.get_admin_groups(per_page=2) == snapshot


async def test_user_traffic_paginated(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test all pages of the monthly user traffic are fetched."""
    traffic = json.loads(_fixture("user_traffic.json"))["user_monthly_traffic_list"]
    first = {"user_monthly_traffic_list": traffic[:1], "has_next_page": True}
    second = {"user_monthly_traffic_list": traffic[1:], "has_next_page": False}
    base = f"{ADMIN}/statistics/system-user-traffic/?month=202610&order_by=sync_file_upload_desc&per_page=1"
    aresponses.add(HOST, f"{base}&page=1", "GET", _json(200, json.dumps(first)), match_querystring=True)
    aresponses.add(HOST, f"{base}&page=2", "GET", _json(200, json.dumps(second)), match_querystring=True)
    result = await seafile_client.get_admin_user_traffic(date(2026, 10, 15), order_by="sync_file_upload_desc", per_page=1)
    assert result == snapshot
