"""Tests for the library endpoints."""

# pylint: disable=too-many-arguments,too-many-positional-arguments

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl

import pytest
from aiohttp.web import Request
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion
from yarl import URL

from aioseafile.models.libraries import LibraryApiTokenPermission
from tests import load_fixtures

if TYPE_CHECKING:
    from aioseafile import Seafile

HOST = "localhost:8000"
JSON = {"Content-Type": "application/json"}
LIB = "02c7b6ae-5500-4c4a-85c4-4b683447d6c5"
COMMIT = "7c8cb6c57ddc4b941efe6ef1eb96f25a0dfd3a0e"
REPO_TOKEN = "0123456789abcdef0123456789abcdef01234567"
SUCCESS = '{"success": true}'
DELETED = '{"success": true, "commit_id": "abba29336bb4aee6f103964ca4968d518cac4a8c"}'
VIA = "/api/v2.1/via-repo-token/"


def _json(text: str) -> object:
    return ResponsesMockServer.Response(status=200, headers=JSON, text=text)


def _fixture(name: str | None) -> str:
    return load_fixtures(f"libraries/{name}") if name else SUCCESS


def _handler(query: dict[str, str], form: list[tuple[str, str]], text: str, authorization: str = "Token test_token") -> Any:
    async def handler(request: Request) -> object:
        assert request.headers["Authorization"] == authorization
        assert dict(request.query) == query
        assert parse_qsl(await request.text()) == form
        return _json(text)

    return handler


def _json_handler(body: Any, text: str, authorization: str = "Token test_token") -> Any:
    async def handler(request: Request) -> object:
        assert request.headers["Authorization"] == authorization
        assert await request.json() == body
        return _json(text)

    return handler


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "path", "query", "fixture"),
    [
        pytest.param("get_library_info", (LIB,), {}, f"/api/v2.1/repos/{LIB}/", {}, "library_info.json", id="get_library_info"),
        pytest.param("get_deleted_libraries", (), {}, "/api/v2.1/deleted-repos/", {}, "deleted_libraries.json", id="get_deleted_libraries"),
        pytest.param(
            "get_library_history",
            (LIB,),
            {"page": 1, "per_page": 2},
            f"/api/v2.1/repos/{LIB}/history/",
            {"page": "1", "per_page": "2"},
            "history_page.json",
            id="get_library_history",
        ),
        pytest.param("get_library_commit", (LIB, COMMIT), {}, f"/api/v2.1/repos/{LIB}/commits/{COMMIT}/", {}, "commit.json", id="get_library_commit"),
        pytest.param(
            "get_library_commit_dir",
            (LIB, COMMIT),
            {},
            f"/api/v2.1/repos/{LIB}/commits/{COMMIT}/dir/",
            {"path": "/"},
            "commit_dir.json",
            id="get_library_commit_dir",
        ),
        pytest.param(
            "get_library_trash",
            (LIB,),
            {"path": "/docs", "show_days": 7},
            f"/api/v2.1/repos/{LIB}/trash/",
            {"path": "/docs", "show_days": "7"},
            "trash.json",
            id="get_library_trash",
        ),
        pytest.param(
            "get_library_trash_items",
            (LIB,),
            {},
            f"/api/v2.1/repos/{LIB}/trash2/",
            {"page": "1", "per_page": "100"},
            "trash2.json",
            id="get_library_trash_items",
        ),
        pytest.param(
            "search_library_trash",
            (LIB,),
            {
                "query": "a",
                "users": ["admin@example.com", "user@example.com"],
                "suffixes": ["txt", "md"],
                "time_from": datetime(2026, 10, 1, tzinfo=UTC),
                "time_to": datetime(2026, 10, 16, tzinfo=UTC),
                "per_page": 20,
            },
            f"/api/v2.1/repos/{LIB}/trash2/search/",
            {
                "q": "a",
                "op_users": "admin@example.com,user@example.com",
                "suffixes": "txt,md",
                "time_from": "1790812800",
                "time_to": "1792108800",
                "page": "1",
                "per_page": "20",
            },
            "trash2_search.json",
            id="search_library_trash",
        ),
        pytest.param(
            "search_library_trash",
            (LIB,),
            {},
            f"/api/v2.1/repos/{LIB}/trash2/search/",
            {"page": "1", "per_page": "100"},
            "trash2_search.json",
            id="search_library_trash_all",
        ),
        pytest.param(
            "get_library_api_tokens",
            (LIB,),
            {},
            f"/api/v2.1/repos/{LIB}/repo-api-tokens/",
            {},
            "library_api_tokens.json",
            id="get_library_api_tokens",
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
    query: dict[str, str],
    fixture: str,
) -> None:
    """Test read endpoints send the right query and are parsed into models."""
    aresponses.add(HOST, path, "GET", _handler(query, [], _fixture(fixture)), match_querystring=False)
    assert await getattr(seafile_client, method)(*args, **kwargs) == snapshot


@pytest.mark.parametrize(
    ("method", "args", "path", "text", "expected"),
    [
        pytest.param("get_default_library", (), "/api2/default-repo/", '{"exists": true, "repo_id": "lib"}', "lib", id="default"),
        pytest.param("get_default_library", (), "/api2/default-repo/", '{"exists": false}', None, id="default_missing"),
        pytest.param("get_library_owner", (LIB,), f"/api2/repos/{LIB}/owner/", '{"owner": "admin@example.com"}', "admin@example.com", id="owner"),
        pytest.param("get_library_history_limit", (LIB,), f"/api2/repos/{LIB}/history-limit/", '{"keep_days": -1}', -1, id="history_limit"),
        pytest.param("get_library_auto_delete_days", (LIB,), f"/api/v2.1/repos/{LIB}/auto-delete/", '{"auto_delete_days": 0}', 0, id="auto_delete"),
        pytest.param("get_snapshot_label_names", (), "/api/v2.1/revision-tags/tag-names/", '["libraries-v3"]', ["libraries-v3"], id="label_names"),
    ],
)
async def test_simple_reads(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    method: str,
    args: tuple[Any, ...],
    path: str,
    text: str,
    expected: object,
) -> None:
    """Test read endpoints that return a plain value."""
    aresponses.add(HOST, path, "GET", _json(text))
    assert await getattr(seafile_client, method)(*args) == expected


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "path", "http_method", "query", "form", "fixture"),
    [
        pytest.param(
            "create_library",
            ("libraries-web",),
            {},
            "/api2/repos/",
            "POST",
            {"from": "web"},
            [("name", "libraries-web")],
            "create_library_web.json",
            id="create_library",
        ),
        pytest.param(
            "create_library",
            ("libraries-enc",),
            {"description": "secret", "password": "encpw"},
            "/api2/repos/",
            "POST",
            {"from": "web"},
            [("name", "libraries-enc"), ("desc", "secret"), ("passwd", "encpw")],
            "create_library_encrypted.json",
            id="create_library_encrypted",
        ),
        pytest.param(
            "create_snapshot_labels",
            (LIB, ["libraries-v1", "libraries-v2"]),
            {"commit_id": COMMIT},
            "/api/v2.1/revision-tags/tagged-items/",
            "POST",
            {},
            [("repo_id", LIB), ("tag_names", "libraries-v1,libraries-v2"), ("commit_id", COMMIT)],
            "snapshot_label_create.json",
            id="create_snapshot_labels",
        ),
        pytest.param(
            "set_snapshot_labels",
            (LIB, ["libraries-v3"]),
            {},
            "/api/v2.1/revision-tags/tagged-items/",
            "PUT",
            {},
            [("repo_id", LIB), ("tag_names", "libraries-v3")],
            "snapshot_label_update.json",
            id="set_snapshot_labels",
        ),
        pytest.param(
            "restore_library_trash_items",
            (LIB, COMMIT, ["/a.txt", "/missing.txt"]),
            {},
            f"/api/v2.1/repos/{LIB}/trash/revert-dirents/",
            "POST",
            {},
            [("commit_id", COMMIT), ("path", "/a.txt"), ("path", "/missing.txt")],
            "trash_restore.json",
            id="restore_library_trash_items",
        ),
        pytest.param(
            "create_library_api_token",
            (LIB, "libraries-app"),
            {},
            f"/api/v2.1/repos/{LIB}/repo-api-tokens/",
            "POST",
            {},
            [("app_name", "libraries-app"), ("permission", "rw")],
            "library_api_token_create.json",
            id="create_library_api_token",
        ),
        pytest.param(
            "update_library_api_token",
            (LIB, "libraries-app", LibraryApiTokenPermission.READ),
            {},
            f"/api/v2.1/repos/{LIB}/repo-api-tokens/libraries-app/",
            "PUT",
            {},
            [("permission", "r")],
            "library_api_token_update.json",
            id="update_library_api_token",
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
    path: str,
    http_method: str,
    query: dict[str, str],
    form: list[tuple[str, str]],
    fixture: str,
) -> None:
    """Test write endpoints that return a model."""
    aresponses.add(HOST, path, http_method, _handler(query, form, _fixture(fixture)), match_querystring=False)
    assert await getattr(seafile_client, method)(*args, **kwargs) == snapshot


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "path", "http_method", "query", "form", "text", "expected"),
    [
        pytest.param(
            "rename_library",
            (LIB, "new"),
            {"description": "desc"},
            f"/api2/repos/{LIB}/",
            "POST",
            {"op": "rename"},
            [("repo_name", "new"), ("repo_desc", "desc")],
            '"success"',
            None,
            id="rename_library",
        ),
        pytest.param(
            "rename_library",
            (LIB, "new"),
            {},
            f"/api2/repos/{LIB}/",
            "POST",
            {"op": "rename"},
            [("repo_name", "new")],
            '"success"',
            None,
            id="rename_name",
        ),
        pytest.param("delete_library", (LIB,), {}, f"/api/v2.1/repos/{LIB}/", "DELETE", {}, [], '"success"', None, id="delete_library"),
        pytest.param(
            "create_default_library",
            (),
            {},
            "/api2/default-repo/",
            "POST",
            {},
            [],
            '{"exists": true, "repo_id": "lib"}',
            "lib",
            id="create_default_library",
        ),
        pytest.param(
            "transfer_library",
            (LIB, "abc@auth.local"),
            {},
            f"/api2/repos/{LIB}/owner/",
            "PUT",
            {},
            [("owner", "abc@auth.local")],
            SUCCESS,
            None,
            id="transfer_library",
        ),
        pytest.param(
            "transfer_library",
            (LIB, "abc@auth.local"),
            {"reshare": True},
            f"/api2/repos/{LIB}/owner/",
            "PUT",
            {},
            [("owner", "abc@auth.local"), ("reshare", "true")],
            SUCCESS,
            None,
            id="transfer_library_reshare",
        ),
        pytest.param(
            "set_library_password",
            (LIB, "pw"),
            {},
            f"/api/v2.1/repos/{LIB}/set-password/",
            "POST",
            {},
            [("password", "pw")],
            SUCCESS,
            None,
            id="set_library_password",
        ),
        pytest.param(
            "change_library_password",
            (LIB, "old", "new"),
            {},
            f"/api/v2.1/repos/{LIB}/set-password/",
            "PUT",
            {},
            [("operation", "change-password"), ("old_password", "old"), ("new_password", "new")],
            SUCCESS,
            None,
            id="change_library_password",
        ),
        pytest.param(
            "can_reset_library_password",
            (LIB,),
            {},
            f"/api/v2.1/repos/{LIB}/set-password/",
            "PUT",
            {},
            [("operation", "can-reset-password")],
            '{"allowed": true}',
            True,
            id="can_reset_library_password",
        ),
        pytest.param(
            "reset_library_password",
            (LIB, "new"),
            {},
            f"/api/v2.1/repos/{LIB}/set-password/",
            "PUT",
            {},
            [("operation", "reset-password"), ("new_password", "new")],
            SUCCESS,
            None,
            id="reset_library_password",
        ),
        pytest.param(
            "send_new_library_password",
            (LIB,),
            {},
            f"/api/v2.1/repos/{LIB}/send-new-password/",
            "POST",
            {},
            [],
            SUCCESS,
            None,
            id="send_new_library_password",
        ),
        pytest.param(
            "set_library_history_limit",
            (LIB, 30),
            {},
            f"/api2/repos/{LIB}/history-limit/",
            "PUT",
            {},
            [("keep_days", "30")],
            '{"keep_days": 30}',
            30,
            id="set_library_history_limit",
        ),
        pytest.param(
            "set_library_auto_delete_days",
            (LIB, 7),
            {},
            f"/api/v2.1/repos/{LIB}/auto-delete/",
            "PUT",
            {},
            [("auto_delete_days", "7")],
            '{"auto_delete_days": 7}',
            7,
            id="set_library_auto_delete_days",
        ),
        pytest.param(
            "revert_library",
            (LIB, COMMIT),
            {},
            f"/api/v2.1/repos/{LIB}/commits/{COMMIT}/revert/",
            "POST",
            {},
            [],
            SUCCESS,
            None,
            id="revert_library",
        ),
        pytest.param(
            "delete_snapshot_label",
            (LIB, "libraries-v3"),
            {},
            "/api/v2.1/revision-tags/tagged-items/",
            "DELETE",
            {"repo_id": LIB, "tag_name": "libraries-v3"},
            [],
            "",
            None,
            id="delete_snapshot_label",
        ),
        pytest.param(
            "clean_library_trash",
            (LIB,),
            {"keep_days": 3},
            f"/api/v2.1/repos/{LIB}/trash/",
            "DELETE",
            {},
            [("keep_days", "3")],
            SUCCESS,
            None,
            id="clean_library_trash",
        ),
        pytest.param(
            "restore_deleted_library",
            (LIB,),
            {},
            "/api/v2.1/deleted-repos/",
            "POST",
            {},
            [("repo_id", LIB)],
            SUCCESS,
            None,
            id="restore_deleted_library",
        ),
        pytest.param(
            "delete_deleted_library",
            (LIB,),
            {},
            f"/api/v2.1/deleted-repos/{LIB}/",
            "DELETE",
            {},
            [],
            SUCCESS,
            None,
            id="delete_deleted_library",
        ),
        pytest.param("clean_deleted_libraries", (), {}, "/api/v2.1/deleted-repos/", "DELETE", {}, [], SUCCESS, None, id="clean_deleted_libraries"),
        pytest.param(
            "delete_library_api_token",
            (LIB, "libraries-app"),
            {},
            f"/api/v2.1/repos/{LIB}/repo-api-tokens/libraries-app/",
            "DELETE",
            {},
            [],
            SUCCESS,
            None,
            id="delete_library_api_token",
        ),
    ],
)
async def test_actions(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    method: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    path: str,
    http_method: str,
    query: dict[str, str],
    form: list[tuple[str, str]],
    text: str,
    expected: object,
) -> None:
    """Test write endpoints that return nothing or a plain value."""
    aresponses.add(HOST, path, http_method, _handler(query, form, text), match_querystring=False)
    assert await getattr(seafile_client, method)(*args, **kwargs) == expected


async def test_restore_library_trash(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test restoring trash items from several commits sends JSON."""
    body = {COMMIT: ["/sub", "/a.txt"]}
    aresponses.add(HOST, f"/api/v2.1/repos/{LIB}/trash2/revert/", "POST", _json_handler(body, _fixture("trash2_restore.json")))
    assert await seafile_client.restore_library_trash(LIB, {COMMIT: ("/sub", "/a.txt")}) == snapshot


async def test_library_trash_scan(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test the trash scan follows the scan_stat cursor."""
    trash = json.loads(_fixture("trash.json"))
    first = {"data": trash["data"][:1], "more": True, "scan_stat": "cursor"}
    second = {"data": trash["data"][1:], "more": False, "scan_stat": None}
    path = f"/api/v2.1/repos/{LIB}/trash/"
    aresponses.add(HOST, path, "GET", _handler({"path": "/"}, [], json.dumps(first)))
    aresponses.add(HOST, path, "GET", _handler({"path": "/", "scan_stat": "cursor"}, [], json.dumps(second)))
    items = await seafile_client.get_library_trash(LIB)
    assert [item.name for item in items] == ["sub", "a.txt"]


async def test_library_trash_items_paged(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test all pages of the trash index are fetched."""
    trash = json.loads(_fixture("trash2.json"))
    path = f"/api/v2.1/repos/{LIB}/trash2/"
    for page, items in ((1, trash["items"][:1]), (2, trash["items"][1:])):
        text = json.dumps({"items": items, "total_count": 2, "can_search": True})
        aresponses.add(HOST, f"{path}?page={page}&per_page=1", "GET", _json(text), match_querystring=True)
    items = await seafile_client.get_library_trash_items(LIB, per_page=1)
    assert [item.name for item in items] == ["sub", "a.txt"]


async def test_library_api_token_hidden_from_repr(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test the library API token stays out of the repr."""
    aresponses.add(HOST, f"/api/v2.1/repos/{LIB}/repo-api-tokens/", "GET", _json(_fixture("library_api_tokens.json")))
    tokens = await seafile_client.get_library_api_tokens(LIB)
    assert tokens[0].api_token not in repr(tokens[0])


async def test_library_trash_items_empty_page(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test paging stops on an empty page even if the total says otherwise."""
    aresponses.add(HOST, f"/api/v2.1/repos/{LIB}/trash2/", "GET", _json('{"items": [], "total_count": 5}'))
    assert await seafile_client.get_library_trash_items(LIB) == []


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "path", "http_method", "query", "form", "fixture"),
    [
        pytest.param("get_library_info_via_repo_token", (), {}, "repo-info/", "GET", {}, [], "via_repo_info.json", id="repo_info"),
        pytest.param("get_dir_via_repo_token", (), {}, "dir/", "GET", {"path": "/", "recursive": "0"}, [], "via_dir.json", id="dir"),
        pytest.param(
            "get_dir_via_repo_token",
            ("/docs",),
            {"recursive": True},
            "dir/",
            "GET",
            {"path": "/docs", "recursive": "1"},
            [],
            "via_dir_recursive.json",
            id="dir_recursive",
        ),
        pytest.param(
            "create_dir_via_repo_token",
            ("/docs",),
            {},
            "dir/",
            "POST",
            {"path": "/docs"},
            [("operation", "mkdir")],
            "via_dir_create.json",
            id="mkdir",
        ),
        pytest.param(
            "rename_dir_via_repo_token",
            ("/docs", "docs2"),
            {},
            "dir/",
            "POST",
            {"path": "/docs"},
            [("operation", "rename"), ("newname", "docs2")],
            "via_dir_rename.json",
            id="rename_dir",
        ),
        pytest.param("get_file_via_repo_token", ("/b.txt",), {}, "file/", "GET", {"path": "/b.txt"}, [], "via_file.json", id="file"),
        pytest.param(
            "create_file_via_repo_token",
            ("/docs2/new.md",),
            {},
            "file/",
            "POST",
            {"path": "/docs2/new.md"},
            [("operation", "create")],
            "via_file_create.json",
            id="create_file",
        ),
        pytest.param(
            "rename_file_via_repo_token",
            ("/docs2/new.md", "renamed.md"),
            {},
            "file/",
            "POST",
            {"path": "/docs2/new.md"},
            [("operation", "rename"), ("newname", "renamed.md")],
            "via_file_rename.json",
            id="rename_file",
        ),
        pytest.param(
            "move_file_via_repo_token",
            ("/docs2/renamed.md", "/other"),
            {},
            "file/",
            "POST",
            {"path": "/docs2/renamed.md"},
            [("operation", "move"), ("dst_dir", "/other")],
            "via_file_move.json",
            id="move_file",
        ),
        pytest.param(
            "copy_file_via_repo_token",
            ("/other/renamed.md", "/docs2"),
            {},
            "file/",
            "POST",
            {"path": "/other/renamed.md"},
            [("operation", "copy"), ("dst_dir", "/docs2")],
            "via_file_copy.json",
            id="copy_file",
        ),
        pytest.param(
            "lock_file_via_repo_token",
            ("/b.txt",),
            {"expire": 60},
            "file/",
            "PUT",
            {"path": "/b.txt"},
            [("operation", "lock"), ("expire", "60")],
            "via_file.json",
            id="lock_file",
        ),
        pytest.param(
            "unlock_file_via_repo_token",
            ("/b.txt",),
            {},
            "file/",
            "PUT",
            {"path": "/b.txt"},
            [("operation", "unlock")],
            "via_file.json",
            id="unlock_file",
        ),
        pytest.param(
            "search_files_via_repo_token", ("renamed",), {}, "search-files/", "GET", {"q": "renamed"}, [], "via_search_files.json", id="search"
        ),
        pytest.param(
            "get_recently_deleted_files_via_repo_token",
            (datetime(2026, 10, 1, 2, tzinfo=UTC),),
            {"limit": 10},
            "recently-deleted-files/",
            "GET",
            {"since": "2026-10-01T02:00:00+00:00", "per_page": "10"},
            [],
            "via_recently_deleted.json",
            id="recently_deleted",
        ),
    ],
)
async def test_via_repo_token(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    snapshot: SnapshotAssertion,
    method: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    path: str,
    http_method: str,
    query: dict[str, str],
    form: list[tuple[str, str]],
    fixture: str,
) -> None:
    """Test endpoints that authenticate with a library API token."""
    handler = _handler(query, form, _fixture(fixture), authorization=f"Token {REPO_TOKEN}")
    aresponses.add(HOST, VIA + path, http_method, handler, match_querystring=False)
    assert await getattr(seafile_client, method)(REPO_TOKEN, *args, **kwargs) == snapshot


@pytest.mark.parametrize(
    ("method", "args", "path", "http_method", "query", "form", "text"),
    [
        pytest.param(
            "revert_dir_via_repo_token",
            ("/docs", COMMIT),
            "dir/",
            "POST",
            {"path": "/docs"},
            [("operation", "revert"), ("commit_id", COMMIT)],
            SUCCESS,
            id="revert_dir",
        ),
        pytest.param(
            "delete_dir_via_repo_token",
            ("/docs",),
            "dir/",
            "DELETE",
            {"path": "/docs"},
            [],
            DELETED,
            id="rmdir",
        ),
        pytest.param(
            "revert_file_via_repo_token",
            ("/b.txt", COMMIT),
            "file/",
            "POST",
            {"path": "/b.txt"},
            [("operation", "revert"), ("commit_id", COMMIT)],
            SUCCESS,
            id="revert_file",
        ),
        pytest.param("delete_file_via_repo_token", ("/b.txt",), "file/", "DELETE", {"path": "/b.txt"}, [], SUCCESS, id="delete_file"),
        pytest.param(
            "move_dir_via_repo_token",
            ("/", "other", "/docs2"),
            "move-dir/",
            "POST",
            {},
            [("src_parent_dir", "/"), ("src_dirent_name", "other"), ("dst_parent_dir", "/docs2")],
            SUCCESS,
            id="move_dir",
        ),
    ],
)
async def test_via_repo_token_actions(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    method: str,
    args: tuple[Any, ...],
    path: str,
    http_method: str,
    query: dict[str, str],
    form: list[tuple[str, str]],
    text: str,
) -> None:
    """Test library API token actions that return nothing."""
    aresponses.add(HOST, VIA + path, http_method, _handler(query, form, text, authorization=f"Token {REPO_TOKEN}"), match_querystring=False)
    assert await getattr(seafile_client, method)(REPO_TOKEN, *args) is None


@pytest.mark.parametrize(
    ("method", "args", "path", "http_method", "body"),
    [
        pytest.param(
            "delete_items_via_repo_token",
            ("/docs2", ["renamed.md"]),
            "batch-delete-item/",
            "DELETE",
            {"parent_dir": "/docs2", "dirents": ["renamed.md"]},
            id="batch_delete",
        ),
        pytest.param(
            "move_items_via_repo_token",
            ("/", ("a.md", "b.md"), "/docs2"),
            "sync-batch-move-item/",
            "POST",
            {"src_parent_dir": "/", "src_dirents": ["a.md", "b.md"], "dst_parent_dir": "/docs2"},
            id="batch_move",
        ),
        pytest.param(
            "copy_items_via_repo_token",
            ("/other", ["renamed.md"], "/"),
            "sync-batch-copy-item/",
            "POST",
            {"src_parent_dir": "/other", "src_dirents": ["renamed.md"], "dst_parent_dir": "/"},
            id="batch_copy",
        ),
    ],
)
async def test_via_repo_token_batch(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    method: str,
    args: tuple[Any, ...],
    path: str,
    http_method: str,
    body: dict[str, Any],
) -> None:
    """Test library API token batch operations send JSON."""
    aresponses.add(HOST, VIA + path, http_method, _json_handler(body, SUCCESS, authorization=f"Token {REPO_TOKEN}"))
    assert await getattr(seafile_client, method)(REPO_TOKEN, *args) is None


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "path", "query", "fixture", "expected"),
    [
        pytest.param(
            "get_upload_link_via_repo_token",
            (),
            {"replace": True},
            "upload-link/",
            {"path": "/", "replace": "1"},
            "via_upload_link.json",
            "http://localhost:8000/seafhttp/upload-api/caf0cd47-c783-49dc-a40b-c41f892daea8",
            id="upload_link",
        ),
        pytest.param(
            "get_download_link_via_repo_token",
            ("/b.txt",),
            {},
            "download-link/",
            {"path": "/b.txt"},
            "via_download_link.json",
            "http://localhost:8000/seafhttp/files/aa0f6496-6e23-4e39-af60-84364478939a/b.txt",
            id="download_link",
        ),
    ],
)
async def test_via_repo_token_links(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    method: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    path: str,
    query: dict[str, str],
    fixture: str,
    expected: str,
) -> None:
    """Test file server links from a library API token are rebased onto the client URL."""
    aresponses.add(HOST, VIA + path, "GET", _handler(query, [], _fixture(fixture), authorization=f"Token {REPO_TOKEN}"), match_querystring=False)
    assert await getattr(seafile_client, method)(REPO_TOKEN, *args, **kwargs) == URL(expected)
