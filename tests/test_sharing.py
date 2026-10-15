"""Tests for the share link, upload link and share endpoints."""

# pylint: disable=too-many-arguments,too-many-positional-arguments

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from aiohttp.web import Request
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion
from yarl import URL

from aioseafile import Seafile
from aioseafile.models.sharing import ShareLinkScope, ShareType
from tests import load_fixtures

HOST = "localhost:8000"
REPO = "35124f5c-2850-44c6-88dd-f6478f273d0b"
USER = "b3c300a8ff924480ae27938952f9f90a@auth.local"
TOKEN = "9ea25a8a1e3c44c2a236"
EXPIRY = datetime(2026, 12, 31, 12, tzinfo=UTC)
SUCCESS = '{"success": true}'
PERMS = {"can_edit": False, "can_download": True, "can_upload": False}

type Call = Callable[[Seafile], Awaitable[Any]]


def _json(text: str) -> object:
    return ResponsesMockServer.Response(status=200, headers={"Content-Type": "application/json"}, text=text)


async def _body(request: Request) -> Any:
    """Return the JSON body, or the form fields as (name, value) pairs."""
    if request.content_type == "application/json":
        return await request.json()
    return list((await request.post()).items())


def _fixture(name: str) -> str:
    return load_fixtures(f"sharing/{name}.json")


CASES = [
    pytest.param(lambda c: c.get_share_link(TOKEN), "GET", f"/api/v2.1/share-links/{TOKEN}/", "share_link", {}, [], id="get_share_link"),
    pytest.param(
        lambda c: c.create_share_link(
            REPO,
            "/notes.md",
            password="Sharing-pw-123",
            expire_days=7,
            description="notes link",
        ),
        "POST",
        "/api/v2.1/share-links/",
        "share_link_create",
        {},
        {"repo_id": REPO, "path": "/notes.md", "permissions": PERMS, "expire_days": 7, "password": "Sharing-pw-123", "description": "notes link"},
        id="create_share_link",
    ),
    pytest.param(
        lambda c: c.create_share_link(REPO, "/photos", user_scope=ShareLinkScope.SPECIFIC_USERS, users=[USER]),
        "POST",
        "/api/v2.1/share-links/",
        "share_link_dir",
        {},
        {"repo_id": REPO, "path": "/photos", "permissions": PERMS, "user_scope": "specific_users", "emails": [USER]},
        id="create_share_link_specific_users",
    ),
    pytest.param(
        lambda c: c.create_share_link(
            REPO,
            "/",
            expiration_time=EXPIRY,
            can_upload=True,
            user_scope=ShareLinkScope.SPECIFIC_EMAILS,
            users=["a@example.com", "b@example.com"],
            allow_multiple=True,
        ),
        "POST",
        "/api/v2.1/multi-share-links/",
        "share_link_multi",
        {},
        {
            "repo_id": REPO,
            "path": "/",
            "permissions": {"can_edit": False, "can_download": True, "can_upload": True},
            "expiration_time": "2026-12-31T12:00:00+00:00",
            "user_scope": "specific_emails",
            "emails": "a@example.com,b@example.com",
        },
        id="create_share_link_multiple_emails",
    ),
    pytest.param(
        lambda c: c.create_share_links(REPO, "/notes.md", 2, auto_generate_password=True, expire_days=3),
        "POST",
        "/api/v2.1/multi-share-links/batch/",
        "share_links_batch",
        {},
        {"repo_id": REPO, "path": "/notes.md", "number": 2, "auto_generate_password": "true", "permissions": PERMS, "expire_days": 3},
        id="create_share_links",
    ),
    pytest.param(
        lambda c: c.update_share_link(TOKEN, can_edit=False, can_download=False, expiration_time=EXPIRY, description="updated"),
        "PUT",
        f"/api/v2.1/share-links/{TOKEN}/",
        "share_link_update",
        {},
        {"expiration_time": "2026-12-31T12:00:00+00:00", "description": "updated", "permissions": {"can_edit": False, "can_download": False}},
        id="update_share_link",
    ),
    pytest.param(
        lambda c: c.update_share_link(TOKEN, user_scope=ShareLinkScope.ALL_USERS),
        "PUT",
        f"/api/v2.1/share-links/{TOKEN}/",
        "share_link",
        {},
        {"user_scope": "all_users"},
        id="update_share_link_scope",
    ),
    pytest.param(lambda c: c.delete_share_link(TOKEN), "DELETE", f"/api/v2.1/share-links/{TOKEN}/", None, {}, [], id="delete_share_link"),
    pytest.param(
        lambda c: c.delete_share_links(["2f11f610ee3649439d93", TOKEN]),
        "DELETE",
        "/api/v2.1/share-links/",
        "links_delete",
        {},
        {"tokens": ["2f11f610ee3649439d93", TOKEN]},
        id="delete_share_links",
    ),
    pytest.param(
        lambda c: c.delete_invalid_share_links(), "DELETE", "/api/v2.1/share-links/clean-invalid/", None, {}, [], id="delete_invalid_share_links"
    ),
    pytest.param(
        lambda c: c.get_share_link_dirents(TOKEN),
        "GET",
        f"/api/v2.1/share-links/{TOKEN}/dirents/",
        "share_link_dirents",
        {"path": "/"},
        [],
        id="get_share_link_dirents",
    ),
    pytest.param(
        lambda c: c.get_share_link_users(TOKEN, "/photos/"),
        "GET",
        f"/api/v2.1/share-links/{TOKEN}/user-auth/",
        "share_link_user_auth_list",
        {"path": "/photos/"},
        [],
        id="get_share_link_users",
    ),
    pytest.param(
        lambda c: c.add_share_link_users(TOKEN, "/photos/", [USER, "nobody@example.com"]),
        "POST",
        f"/api/v2.1/share-links/{TOKEN}/user-auth/",
        "share_link_user_auth_add",
        {"path": "/photos/"},
        {"emails": [USER, "nobody@example.com"]},
        id="add_share_link_users",
    ),
    pytest.param(
        lambda c: c.delete_share_link_users(TOKEN, "/photos/", [USER]),
        "DELETE",
        f"/api/v2.1/share-links/{TOKEN}/user-auth/",
        None,
        {"path": "/photos/"},
        {"emails": [USER]},
        id="delete_share_link_users",
    ),
    pytest.param(
        lambda c: c.get_share_link_emails(TOKEN, "/photos/"),
        "GET",
        f"/api/v2.1/share-links/{TOKEN}/email-auth/",
        "share_link_email_auth_list",
        {"path": "/photos/"},
        [],
        id="get_share_link_emails",
    ),
    pytest.param(
        lambda c: c.add_share_link_emails(TOKEN, "/photos/", ["guest@example.com", "bad"]),
        "POST",
        f"/api/v2.1/share-links/{TOKEN}/email-auth/",
        "share_link_email_auth_add",
        {"path": "/photos/"},
        {"emails": "guest@example.com,bad"},
        id="add_share_link_emails",
    ),
    pytest.param(
        lambda c: c.delete_share_link_emails(TOKEN, "/photos/", ["guest@example.com"]),
        "DELETE",
        f"/api/v2.1/share-links/{TOKEN}/email-auth/",
        None,
        {"path": "/photos/"},
        {"emails": ["guest@example.com"]},
        id="delete_share_link_emails",
    ),
    pytest.param(
        lambda c: c.send_share_link(TOKEN, ["guest@example.com", "bad"], message="hi", send_password_separately=True),
        "POST",
        "/api2/send-share-link/",
        "send_link",
        {},
        [("token", TOKEN), ("email", "guest@example.com,bad"), ("extra_msg", "hi"), ("send_password_separately", "true")],
        id="send_share_link",
    ),
    pytest.param(
        lambda c: c.get_upload_links(REPO, "/photos/"),
        "GET",
        "/api/v2.1/upload-links/",
        "upload_links",
        {"repo_id": REPO, "path": "/photos/"},
        [],
        id="get_upload_links",
    ),
    pytest.param(
        lambda c: c.get_upload_link_details("0fac727091f5427d92dd"),
        "GET",
        "/api/v2.1/upload-links/0fac727091f5427d92dd/",
        "upload_link",
        {},
        [],
        id="get_upload_link_details",
    ),
    pytest.param(
        lambda c: c.create_upload_link(REPO, "/photos/", password="Upload-pw-123", expire_days=5, description="drop"),
        "POST",
        "/api/v2.1/upload-links/",
        "upload_link_create",
        {},
        [("repo_id", REPO), ("path", "/photos/"), ("expire_days", "5"), ("password", "Upload-pw-123"), ("description", "drop")],
        id="create_upload_link",
    ),
    pytest.param(
        lambda c: c.update_upload_link("0fac727091f5427d92dd", expiration_time=EXPIRY),
        "PUT",
        "/api/v2.1/upload-links/0fac727091f5427d92dd/",
        "upload_link_update",
        {},
        [("expiration_time", "2026-12-31T12:00:00+00:00")],
        id="update_upload_link",
    ),
    pytest.param(
        lambda c: c.delete_upload_link("0fac727091f5427d92dd"),
        "DELETE",
        "/api/v2.1/upload-links/0fac727091f5427d92dd/",
        None,
        {},
        [],
        id="delete_upload_link",
    ),
    pytest.param(
        lambda c: c.delete_upload_links(["2f11f610ee3649439d93"]),
        "DELETE",
        "/api/v2.1/upload-links/",
        "links_delete",
        {},
        {"tokens": ["2f11f610ee3649439d93"]},
        id="delete_upload_links",
    ),
    pytest.param(
        lambda c: c.delete_invalid_upload_links(), "DELETE", "/api/v2.1/upload-links/clean-invalid/", None, {}, [], id="delete_invalid_upload_links"
    ),
    pytest.param(
        lambda c: c.send_upload_link("0fac727091f5427d92dd", ["guest@example.com"]),
        "POST",
        "/api2/send-upload-link/",
        "send_link",
        {},
        [("token", "0fac727091f5427d92dd"), ("email", "guest@example.com"), ("extra_msg", ""), ("send_password_separately", "false")],
        id="send_upload_link",
    ),
    pytest.param(
        lambda c: c.delete_library_share_link(REPO, TOKEN),
        "DELETE",
        f"/api/v2.1/repos/{REPO}/share-links/{TOKEN}/",
        None,
        {},
        [],
        id="delete_library_share_link",
    ),
    pytest.param(
        lambda c: c.delete_library_upload_link(REPO, TOKEN),
        "DELETE",
        f"/api/v2.1/repos/{REPO}/upload-links/{TOKEN}/",
        None,
        {},
        [],
        id="delete_library_upload_link",
    ),
    pytest.param(lambda c: c.get_shares(REPO), "GET", f"/api2/repos/{REPO}/dir/shared_items/", "shared_items", {"p": "/"}, [], id="get_shares"),
    pytest.param(
        lambda c: c.get_shares(REPO, "/photos", share_type=ShareType.USER),
        "GET",
        f"/api2/repos/{REPO}/dir/shared_items/",
        "shared_items_folder",
        {"p": "/photos", "share_type": "user"},
        [],
        id="get_shares_folder",
    ),
    pytest.param(
        lambda c: c.share_to_users(REPO, [USER, "nobody@example.com"], path="/photos"),
        "PUT",
        f"/api2/repos/{REPO}/dir/shared_items/",
        "share_dir_to_user",
        {"p": "/photos"},
        [("share_type", "user"), ("permission", "r"), ("username", USER), ("username", "nobody@example.com")],
        id="share_to_users",
    ),
    pytest.param(
        lambda c: c.share_to_groups(REPO, [3], "rw"),
        "PUT",
        f"/api2/repos/{REPO}/dir/shared_items/",
        "share_lib_to_group",
        {"p": "/"},
        [("share_type", "group"), ("permission", "rw"), ("group_id", "3")],
        id="share_to_groups",
    ),
    pytest.param(
        lambda c: c.update_user_share(REPO, USER, "rw"),
        "POST",
        f"/api2/repos/{REPO}/dir/shared_items/",
        None,
        {"p": "/", "share_type": "user", "username": USER},
        [("permission", "rw")],
        id="update_user_share",
    ),
    pytest.param(
        lambda c: c.update_group_share(REPO, 3, "r", path="/photos"),
        "POST",
        f"/api2/repos/{REPO}/dir/shared_items/",
        None,
        {"p": "/photos", "share_type": "group", "group_id": "3"},
        [("permission", "r")],
        id="update_group_share",
    ),
    pytest.param(
        lambda c: c.delete_user_share(REPO, USER),
        "DELETE",
        f"/api2/repos/{REPO}/dir/shared_items/",
        None,
        {"p": "/", "share_type": "user", "username": USER},
        [],
        id="delete_user_share",
    ),
    pytest.param(
        lambda c: c.delete_group_share(REPO, 3, path="/photos"),
        "DELETE",
        f"/api2/repos/{REPO}/dir/shared_items/",
        None,
        {"p": "/photos", "share_type": "group", "group_id": "3"},
        [],
        id="delete_group_share",
    ),
    pytest.param(
        lambda c: c.share_libraries_to_user([REPO], USER, "r"),
        "POST",
        "/api/v2.1/repos/batch/",
        "repos_batch_share",
        {},
        [("operation", "share"), ("share_type", "user"), ("username", USER), ("permission", "r"), ("repo_id", REPO)],
        id="share_libraries_to_user",
    ),
    pytest.param(
        lambda c: c.share_libraries_to_group([REPO, "00000000-0000-0000-0000-000000000000"], 3, "r"),
        "POST",
        "/api/v2.1/repos/batch/",
        "repos_batch_share",
        {},
        [
            ("operation", "share"),
            ("share_type", "group"),
            ("group_id", "3"),
            ("permission", "r"),
            ("repo_id", REPO),
            ("repo_id", "00000000-0000-0000-0000-000000000000"),
        ],
        id="share_libraries_to_group",
    ),
    pytest.param(
        lambda c: c.unshare_libraries_from_user([REPO], USER),
        "POST",
        "/api/v2.1/repos/batch/",
        "repos_batch_unshare",
        {},
        [("operation", "unshare"), ("share_type", "user"), ("username", USER), ("repo_id", REPO)],
        id="unshare_libraries_from_user",
    ),
    pytest.param(
        lambda c: c.unshare_libraries_from_group([REPO], 3),
        "POST",
        "/api/v2.1/repos/batch/",
        "repos_batch_unshare",
        {},
        [("operation", "unshare"), ("share_type", "group"), ("group_id", "3"), ("repo_id", REPO)],
        id="unshare_libraries_from_group",
    ),
    pytest.param(lambda c: c.get_shared_libraries(), "GET", "/api/v2.1/shared-repos/", "shared_repos", {}, [], id="get_shared_libraries"),
    pytest.param(lambda c: c.get_shared_folders(), "GET", "/api/v2.1/shared-folders/", "shared_folders", {}, [], id="get_shared_folders"),
    pytest.param(lambda c: c.get_received_shares(), "GET", "/api2/beshared-repos/", "beshared_repos", {}, [], id="get_received_shares"),
    pytest.param(
        lambda c: c.leave_share(REPO, "admin@example.com"),
        "DELETE",
        f"/api2/beshared-repos/{REPO}/",
        None,
        {"share_type": "personal", "from": "admin@example.com"},
        [],
        id="leave_share",
    ),
    pytest.param(
        lambda c: c.leave_share(REPO, "admin@example.com", group_id=3),
        "DELETE",
        f"/api2/beshared-repos/{REPO}/",
        None,
        {"share_type": "group", "from": "admin@example.com", "group_id": "3"},
        [],
        id="leave_share_group",
    ),
    pytest.param(
        lambda c: c.get_user_folder_permissions(REPO, "/photos"),
        "GET",
        f"/api2/repos/{REPO}/user-folder-perm/",
        "user_folder_permissions",
        {"folder_path": "/photos"},
        [],
        id="get_user_folder_permissions",
    ),
    pytest.param(
        lambda c: c.create_user_folder_permissions(REPO, "/photos", [USER, "nobody@example.com"], "r"),
        "POST",
        f"/api2/repos/{REPO}/user-folder-perm/",
        "user_folder_permissions_create",
        {},
        [("folder_path", "/photos"), ("permission", "r"), ("user_email", USER), ("user_email", "nobody@example.com")],
        id="create_user_folder_permissions",
    ),
    pytest.param(
        lambda c: c.update_user_folder_permission(REPO, "/photos", USER, "rw"),
        "PUT",
        f"/api2/repos/{REPO}/user-folder-perm/",
        "user_folder_permission_update",
        {},
        [("folder_path", "/photos"), ("user_email", USER), ("permission", "rw")],
        id="update_user_folder_permission",
    ),
    pytest.param(
        lambda c: c.delete_user_folder_permission(REPO, "/photos", USER),
        "DELETE",
        f"/api2/repos/{REPO}/user-folder-perm/",
        None,
        {},
        [("folder_path", "/photos"), ("user_email", USER)],
        id="delete_user_folder_permission",
    ),
    pytest.param(
        lambda c: c.get_group_folder_permissions(REPO),
        "GET",
        f"/api2/repos/{REPO}/group-folder-perm/",
        "group_folder_permissions",
        {},
        [],
        id="get_group_folder_permissions",
    ),
    pytest.param(
        lambda c: c.create_group_folder_permissions(REPO, "/photos", [3, 99], "rw"),
        "POST",
        f"/api2/repos/{REPO}/group-folder-perm/",
        "group_folder_permissions_create",
        {},
        [("folder_path", "/photos"), ("permission", "rw"), ("group_id", "3"), ("group_id", "99")],
        id="create_group_folder_permissions",
    ),
    pytest.param(
        lambda c: c.update_group_folder_permission(REPO, "/photos", 3, "r"),
        "PUT",
        f"/api2/repos/{REPO}/group-folder-perm/",
        "group_folder_permission_update",
        {},
        [("folder_path", "/photos"), ("group_id", "3"), ("permission", "r")],
        id="update_group_folder_permission",
    ),
    pytest.param(
        lambda c: c.delete_group_folder_permission(REPO, "/photos", 3),
        "DELETE",
        f"/api2/repos/{REPO}/group-folder-perm/",
        None,
        {},
        [("folder_path", "/photos"), ("group_id", "3")],
        id="delete_group_folder_permission",
    ),
    pytest.param(
        lambda c: c.get_admin_share_link_dirents(TOKEN, "/sub"),
        "GET",
        f"/api/v2.1/admin/share-links/{TOKEN}/dirents/",
        "admin_share_link_dirents",
        {"path": "/sub"},
        [],
        id="get_admin_share_link_dirents",
    ),
    pytest.param(
        lambda c: c.get_admin_shares(REPO, ShareType.USER),
        "GET",
        "/api/v2.1/admin/shares/",
        "admin_shares",
        {"repo_id": REPO, "share_type": "user", "path": "/"},
        [],
        id="get_admin_shares",
    ),
    pytest.param(
        lambda c: c.get_admin_shares(REPO, ShareType.GROUP, path="/photos"),
        "GET",
        "/api/v2.1/admin/shares/",
        "admin_shares_group",
        {"repo_id": REPO, "share_type": "group", "path": "/photos"},
        [],
        id="get_admin_shares_group",
    ),
    pytest.param(
        lambda c: c.create_admin_shares(REPO, ShareType.USER, [USER, "bad"], "r"),
        "POST",
        "/api/v2.1/admin/shares/",
        "admin_share_create",
        {},
        [("repo_id", REPO), ("path", "/"), ("share_type", "user"), ("permission", "r"), ("share_to", USER), ("share_to", "bad")],
        id="create_admin_shares",
    ),
    pytest.param(
        lambda c: c.update_admin_share(REPO, ShareType.USER, USER, "rw"),
        "PUT",
        "/api/v2.1/admin/shares/",
        "admin_share_update",
        {},
        [("repo_id", REPO), ("path", "/"), ("share_type", "user"), ("share_to", USER), ("permission", "rw")],
        id="update_admin_share",
    ),
    pytest.param(
        lambda c: c.delete_admin_share(REPO, ShareType.GROUP, 3, path="/photos"),
        "DELETE",
        "/api/v2.1/admin/shares/",
        None,
        {},
        [("repo_id", REPO), ("path", "/photos"), ("share_type", "group"), ("share_to", "3")],
        id="delete_admin_share",
    ),
    pytest.param(
        lambda c: c.get_admin_user_shared_libraries("admin@example.com"),
        "GET",
        "/api/v2.1/admin/users/admin@example.com/shared-repos/",
        "admin_user_shared_repos",
        {},
        [],
        id="get_admin_user_shared_libraries",
    ),
    pytest.param(
        lambda c: c.get_admin_user_shared_folders("admin@example.com"),
        "GET",
        "/api/v2.1/admin/users/admin@example.com/shared-folders/",
        "admin_user_shared_folders",
        {},
        [],
        id="get_admin_user_shared_folders",
    ),
]


@pytest.mark.parametrize(("call", "method", "path", "fixture", "query", "body"), CASES)
async def test_endpoints(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    snapshot: SnapshotAssertion,
    call: Call,
    method: str,
    path: str,
    fixture: str | None,
    query: dict[str, str],
    body: Any,
) -> None:
    """Test each endpoint sends the right request and parses the response."""
    requests: list[tuple[dict[str, str], Any]] = []

    async def handler(request: Request) -> object:
        requests.append((dict(request.query), await _body(request)))
        return _json(_fixture(fixture) if fixture else SUCCESS)

    aresponses.add(HOST, path, method, handler)
    assert await call(seafile_client) == snapshot
    assert requests == [(query, body)]


@pytest.mark.parametrize(
    ("call", "path", "fixture"),
    [
        pytest.param(lambda c: c.get_share_links(REPO, per_page=1), "/api/v2.1/share-links/", "share_links", id="get_share_links"),
        pytest.param(
            lambda c: c.get_library_share_links(REPO, per_page=1),
            f"/api/v2.1/repos/{REPO}/share-links/",
            "library_share_links",
            id="get_library_share_links",
        ),
        pytest.param(
            lambda c: c.get_library_upload_links(REPO, per_page=1),
            f"/api/v2.1/repos/{REPO}/upload-links/",
            "library_upload_links",
            id="get_library_upload_links",
        ),
    ],
)
async def test_paginated(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    snapshot: SnapshotAssertion,
    call: Call,
    path: str,
    fixture: str,
) -> None:
    """Test list endpoints fetch pages until a short page."""
    items = json.loads(_fixture(fixture))
    pages: list[dict[str, str]] = []

    async def handler(request: Request) -> object:
        pages.append(dict(request.query))
        page = int(request.query["page"])
        return _json(json.dumps(items[page - 1 : page]))

    for _ in range(len(items) + 1):
        aresponses.add(HOST, path, "GET", handler)
    assert await call(seafile_client) == snapshot
    assert [page["page"] for page in pages] == ["1", "2", "3"]
    assert pages[0]["per_page"] == "1"


async def test_get_share_links_all(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test listing all share links sends no filters."""

    async def handler(request: Request) -> object:
        assert dict(request.query) == {"page": "1", "per_page": "100"}
        return _json(_fixture("share_links"))

    aresponses.add(HOST, "/api/v2.1/share-links/", "GET", handler)
    links = await seafile_client.get_share_links()
    assert [link.token for link in links] == ["beeb336ef9b64cfe97ca", TOKEN]
    assert links[0].expire_date is None


async def test_get_upload_link_upload_url(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test the upload URL of an upload link is rebased onto the file server."""
    aresponses.add(HOST, "/api/v2.1/upload-links/2a6a5f74bbd84ddc9b8b/upload/", "GET", _json(_fixture("upload_link_upload")))
    url = await seafile_client.get_upload_link_upload_url("2a6a5f74bbd84ddc9b8b")
    assert url == URL("http://localhost:8000/seafhttp/upload-api/b87017fa-fa2e-4e9f-ab0c-9b11d9c1d97b")


async def test_share_link_dirent_properties(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test the path and name helpers of folder and file entries."""
    aresponses.add(HOST, f"/api/v2.1/share-links/{TOKEN}/dirents/", "GET", _json(_fixture("share_link_dirents")))
    dirents = await seafile_client.get_share_link_dirents(TOKEN)
    assert [(dirent.path, dirent.name) for dirent in dirents] == [("/photos/", "photos"), ("/notes.md", "notes.md")]
