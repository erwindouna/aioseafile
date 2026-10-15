"""Tests for the group, department and organization endpoints."""

# pylint: disable=too-many-arguments,too-many-positional-arguments

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl

import pytest
from aiohttp.web import Request
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from aioseafile.models.groups import Group
from tests import load_fixtures

if TYPE_CHECKING:
    from aioseafile import Seafile

HOST = "localhost:8000"
JSON = {"Content-Type": "application/json"}
GROUP = 1
LIBRARY = "c9a996fa-b1f8-4158-bdfc-5c6badcae9a2"
DEPARTMENT_LIBRARY = "0f3c9a2e-6b1d-4c8e-9a51-2d7e4b6f8c10"
MEMBER = "4897149ea526449c94491315b118c13e@auth.local"
ORG = 3
ORG_USER = "d4e5f6@auth.local"
SUCCESS = '{"success": true}'


def _json(text: str) -> object:
    return ResponsesMockServer.Response(status=200, headers=JSON, text=text)


def _fixture(name: str | None) -> str:
    return load_fixtures(f"groups/{name}") if name else SUCCESS


def _handler(query: dict[str, str], form: list[tuple[str, str]], text: str) -> Any:
    async def handler(request: Request) -> object:
        assert dict(request.query) == query
        assert parse_qsl(await request.text()) == form
        return _json(text)

    return handler


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "path", "query", "fixture"),
    [
        pytest.param("get_groups", (), {}, "/api/v2.1/groups/", {}, "groups.json", id="get_groups"),
        pytest.param(
            "get_groups",
            (),
            {"with_libraries": True},
            "/api/v2.1/groups/",
            {"with_repos": "1"},
            "groups_with_repos.json",
            id="get_groups_libraries",
        ),
        pytest.param("get_all_groups", (), {}, "/api/v2.1/all-groups/", {}, "groups.json", id="get_all_groups"),
        pytest.param("get_shareable_groups", (), {}, "/api/v2.1/shareable-groups/", {}, "shareable_groups.json", id="get_shareable_groups"),
        pytest.param("search_groups", ("groups",), {}, "/api/v2.1/search-group/", {"q": "groups"}, "search_groups.json", id="search_groups"),
        pytest.param("get_group", (GROUP,), {}, f"/api/v2.1/groups/{GROUP}/", {}, "group.json", id="get_group"),
        pytest.param(
            "get_group_member",
            (GROUP, MEMBER),
            {},
            f"/api/v2.1/groups/{GROUP}/members/{MEMBER}/",
            {},
            "group_member.json",
            id="get_group_member",
        ),
        pytest.param(
            "search_group_members",
            (GROUP, "Groups"),
            {},
            f"/api/v2.1/groups/{GROUP}/search-member/",
            {"q": "Groups"},
            "group_members.json",
            id="search_members",
        ),
        pytest.param(
            "get_group_invite_links",
            (GROUP,),
            {},
            f"/api/v2.1/groups/{GROUP}/invite-links/",
            {},
            "group_invite_links.json",
            id="get_invite_links",
        ),
        pytest.param("get_departments", (), {}, "/api/v2.1/departments/", {"can_admin": "false"}, "departments.json", id="get_departments"),
        pytest.param(
            "get_departments",
            (),
            {"can_admin": True},
            "/api/v2.1/departments/",
            {"can_admin": "true"},
            "departments.json",
            id="get_departments_admin",
        ),
        pytest.param(
            "get_address_book_departments",
            (),
            {},
            "/api/v2.1/address-book/departments/",
            {},
            "address_book_departments.json",
            id="address_book_departments",
        ),
        pytest.param(
            "get_department_members",
            (GROUP,),
            {},
            f"/api/v2.1/address-book/departments/{GROUP}/members/",
            {},
            "department_members.json",
            id="dept_members",
        ),
        pytest.param(
            "get_department_sub_departments",
            (7,),
            {},
            "/api/v2.1/address-book/groups/7/sub-groups/",
            {},
            "department_sub_departments.json",
            id="sub_depts",
        ),
        pytest.param(
            "get_department_library_user_shares",
            (DEPARTMENT_LIBRARY,),
            {},
            f"/api/v2.1/group-owned-libraries/{DEPARTMENT_LIBRARY}/user-share/",
            {"path": "/"},
            "department_library_user_shares.json",
            id="dept_library_user_shares",
        ),
        pytest.param(
            "get_department_library_group_shares",
            (DEPARTMENT_LIBRARY,),
            {"path": "/docs"},
            f"/api/v2.1/group-owned-libraries/{DEPARTMENT_LIBRARY}/group-share/",
            {"path": "/docs"},
            "department_library_group_shares.json",
            id="dept_library_group_shares",
        ),
        pytest.param("get_org_info", (), {}, "/api/v2.1/org/admin/info/", {}, "org_info.json", id="get_org_info"),
        pytest.param("get_org_user", (ORG, ORG_USER), {}, f"/api/v2.1/org/{ORG}/admin/users/{ORG_USER}/", {}, "org_user.json", id="get_org_user"),
        pytest.param(
            "get_org_groups",
            (ORG,),
            {},
            f"/api/v2.1/org/{ORG}/admin/groups/",
            {"page": "1", "per_page": "100"},
            "org_groups.json",
            id="get_org_groups",
        ),
        pytest.param("get_org_group", (ORG, 4), {}, f"/api/v2.1/org/{ORG}/admin/groups/4/", {}, "org_group.json", id="get_org_group"),
        pytest.param(
            "get_org_libraries",
            (ORG,),
            {},
            f"/api/v2.1/org/{ORG}/admin/repos/",
            {"page": "1", "per_page": "100"},
            "org_libraries.json",
            id="get_org_libraries",
        ),
    ],
)
async def test_reads(
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
    aresponses.add(HOST, path, "GET", _handler(query, [], _fixture(fixture)))
    assert await getattr(seafile_client, method)(*args, **kwargs) == snapshot


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "http_method", "path", "form", "fixture"),
    [
        pytest.param("create_group", ("groups-team",), {}, "POST", "/api/v2.1/groups/", [("name", "groups-team")], "group.json", id="create_group"),
        pytest.param(
            "rename_group",
            (GROUP, "renamed"),
            {},
            "PUT",
            f"/api/v2.1/groups/{GROUP}/",
            [("name", "renamed")],
            "group.json",
            id="rename_group",
        ),
        pytest.param(
            "transfer_group",
            (GROUP, MEMBER),
            {},
            "PUT",
            f"/api/v2.1/groups/{GROUP}/",
            [("owner", MEMBER)],
            "group.json",
            id="transfer_group",
        ),
        pytest.param("delete_group", (GROUP,), {}, "DELETE", f"/api/v2.1/groups/{GROUP}/", [], None, id="delete_group"),
        pytest.param(
            "add_group_member",
            (GROUP, MEMBER),
            {},
            "POST",
            f"/api/v2.1/groups/{GROUP}/members/",
            [("email", MEMBER)],
            "group_member.json",
            id="add_group_member",
        ),
        pytest.param(
            "add_group_members",
            (GROUP, ["a@example.com", "b@example.com"]),
            {},
            "POST",
            f"/api/v2.1/groups/{GROUP}/members/bulk/",
            [("emails", "a@example.com,b@example.com")],
            "group_members_bulk.json",
            id="add_group_members",
        ),
        pytest.param(
            "set_group_member_admin",
            (GROUP, MEMBER),
            {"is_admin": True},
            "PUT",
            f"/api/v2.1/groups/{GROUP}/members/{MEMBER}/",
            [("is_admin", "true")],
            "group_member.json",
            id="set_admin",
        ),
        pytest.param(
            "set_group_member_admin",
            (GROUP, MEMBER),
            {"is_admin": False},
            "PUT",
            f"/api/v2.1/groups/{GROUP}/members/{MEMBER}/",
            [("is_admin", "false")],
            "group_member.json",
            id="unset_admin",
        ),
        pytest.param(
            "remove_group_member",
            (GROUP, MEMBER),
            {},
            "DELETE",
            f"/api/v2.1/groups/{GROUP}/members/{MEMBER}/",
            [],
            None,
            id="remove_group_member",
        ),
        pytest.param(
            "create_group_invite_link",
            (GROUP,),
            {},
            "POST",
            f"/api/v2.1/groups/{GROUP}/invite-links/",
            [],
            "group_invite_link.json",
            id="create_invite_link",
        ),
        pytest.param(
            "delete_group_invite_link",
            (GROUP, "7daf6706"),
            {},
            "DELETE",
            f"/api/v2.1/groups/{GROUP}/invite-links/7daf6706/",
            [],
            None,
            id="delete_invite",
        ),
        pytest.param(
            "create_group_library",
            (GROUP, "groups-lib"),
            {},
            "POST",
            f"/api/v2.1/groups/{GROUP}/libraries/",
            [("repo_name", "groups-lib"), ("permission", "rw")],
            "group_library.json",
            id="create_group_library",
        ),
        pytest.param(
            "create_group_library",
            (GROUP, "groups-lib"),
            {"permission": "r", "password": "secret"},
            "POST",
            f"/api/v2.1/groups/{GROUP}/libraries/",
            [("repo_name", "groups-lib"), ("permission", "r"), ("password", "secret")],
            "group_library.json",
            id="create_encrypted_group_library",
        ),
        pytest.param(
            "unshare_group_library",
            (GROUP, LIBRARY),
            {},
            "DELETE",
            f"/api/v2.1/groups/{GROUP}/libraries/{LIBRARY}/",
            [],
            None,
            id="unshare_group_library",
        ),
        pytest.param(
            "create_department_library",
            (7, "engineering-docs"),
            {},
            "POST",
            "/api/v2.1/groups/7/group-owned-libraries/",
            [("name", "engineering-docs"), ("permission", "rw")],
            "department_library.json",
            id="create_department_library",
        ),
        pytest.param(
            "create_department_library",
            (7, "engineering-docs"),
            {"permission": "r", "password": "secret"},
            "POST",
            "/api/v2.1/groups/7/group-owned-libraries/",
            [("name", "engineering-docs"), ("permission", "r"), ("passwd", "secret")],
            "department_library.json",
            id="create_encrypted_department_library",
        ),
        pytest.param(
            "rename_department_library",
            (7, DEPARTMENT_LIBRARY, "renamed"),
            {},
            "PUT",
            f"/api/v2.1/groups/7/group-owned-libraries/{DEPARTMENT_LIBRARY}/",
            [("name", "renamed")],
            "department_library.json",
            id="rename_department_library",
        ),
        pytest.param(
            "transfer_department_library",
            (7, DEPARTMENT_LIBRARY, "user@example.com"),
            {},
            "PUT",
            f"/api/v2.1/groups/7/group-owned-libraries/{DEPARTMENT_LIBRARY}/transfer/",
            [("email", "user@example.com")],
            None,
            id="transfer_department_library",
        ),
        pytest.param(
            "transfer_department_library",
            (7, DEPARTMENT_LIBRARY, "8@seafile_group"),
            {"reshare": True},
            "PUT",
            f"/api/v2.1/groups/7/group-owned-libraries/{DEPARTMENT_LIBRARY}/transfer/",
            [("email", "8@seafile_group"), ("reshare", "true")],
            None,
            id="transfer_department_library_reshare",
        ),
        pytest.param(
            "delete_department_library",
            (7, DEPARTMENT_LIBRARY),
            {},
            "DELETE",
            f"/api/v2.1/groups/7/group-owned-libraries/{DEPARTMENT_LIBRARY}/",
            [],
            None,
            id="delete_department_library",
        ),
        pytest.param(
            "share_department_library_to_users",
            (DEPARTMENT_LIBRARY, ["user@example.com", "nobody@example.com"]),
            {"permission": "rw"},
            "POST",
            f"/api/v2.1/group-owned-libraries/{DEPARTMENT_LIBRARY}/user-share/",
            [("username", "user@example.com"), ("username", "nobody@example.com"), ("permission", "rw"), ("path", "/")],
            "department_library_user_share_result.json",
            id="share_department_library_to_users",
        ),
        pytest.param(
            "update_department_library_user_share",
            (DEPARTMENT_LIBRARY, "user@example.com", "r"),
            {"path": "/docs"},
            "PUT",
            f"/api/v2.1/group-owned-libraries/{DEPARTMENT_LIBRARY}/user-share/",
            [("username", "user@example.com"), ("permission", "r"), ("path", "/docs")],
            None,
            id="update_department_library_user_share",
        ),
        pytest.param(
            "unshare_department_library_from_user",
            (DEPARTMENT_LIBRARY, "user@example.com"),
            {},
            "DELETE",
            f"/api/v2.1/group-owned-libraries/{DEPARTMENT_LIBRARY}/user-share/",
            [("username", "user@example.com"), ("path", "/")],
            None,
            id="unshare_department_library_from_user",
        ),
        pytest.param(
            "share_department_library_to_groups",
            (DEPARTMENT_LIBRARY, [1, 99999]),
            {"permission": "rw"},
            "POST",
            f"/api/v2.1/group-owned-libraries/{DEPARTMENT_LIBRARY}/group-share/",
            [("group_id", "1"), ("group_id", "99999"), ("permission", "rw"), ("path", "/")],
            "department_library_group_share_result.json",
            id="share_department_library_to_groups",
        ),
        pytest.param(
            "update_department_library_group_share",
            (DEPARTMENT_LIBRARY, 1, "r"),
            {},
            "PUT",
            f"/api/v2.1/group-owned-libraries/{DEPARTMENT_LIBRARY}/group-share/",
            [("group_id", "1"), ("permission", "r"), ("path", "/")],
            None,
            id="update_department_library_group_share",
        ),
        pytest.param(
            "unshare_department_library_from_group",
            (DEPARTMENT_LIBRARY, 1),
            {"path": "/docs"},
            "DELETE",
            f"/api/v2.1/group-owned-libraries/{DEPARTMENT_LIBRARY}/group-share/",
            [("group_id", "1"), ("path", "/docs")],
            None,
            id="unshare_department_library_from_group",
        ),
        pytest.param("update_org_info", (), {}, "PUT", "/api/v2.1/org/admin/info/", [], "org_info.json", id="update_org_info_nothing"),
        pytest.param(
            "update_org_info",
            (),
            {"name": "Example Org", "user_default_quota_mb": 1024},
            "PUT",
            "/api/v2.1/org/admin/info/",
            [("org_name", "Example Org"), ("user_default_quota", "1024")],
            "org_info.json",
            id="update_org_info",
        ),
        pytest.param(
            "create_org_user",
            (ORG, ORG_USER, "secret", "Org Member"),
            {},
            "POST",
            f"/api/v2.1/org/{ORG}/admin/users/",
            [("email", ORG_USER), ("password", "secret"), ("name", "Org Member")],
            "org_user.json",
            id="create_org_user",
        ),
        pytest.param(
            "update_org_user",
            (ORG, ORG_USER),
            {"name": "New", "contact_email": "new@example.com", "is_staff": True, "is_active": False, "quota_total_mb": 1024},
            "PUT",
            f"/api/v2.1/org/{ORG}/admin/users/{ORG_USER}/",
            [("name", "New"), ("contact_email", "new@example.com"), ("is_staff", "true"), ("is_active", "false"), ("quota_total", "1024")],
            "org_user.json",
            id="update_org_user",
        ),
        pytest.param(
            "update_org_user",
            (ORG, ORG_USER),
            {"is_staff": False, "is_active": True},
            "PUT",
            f"/api/v2.1/org/{ORG}/admin/users/{ORG_USER}/",
            [("is_staff", "false"), ("is_active", "true")],
            "org_user.json",
            id="update_org_user_flags",
        ),
        pytest.param(
            "update_org_user",
            (ORG, ORG_USER),
            {"name": "New"},
            "PUT",
            f"/api/v2.1/org/{ORG}/admin/users/{ORG_USER}/",
            [("name", "New")],
            "org_user.json",
            id="update_org_user_name",
        ),
        pytest.param(
            "delete_org_user",
            (ORG, ORG_USER),
            {},
            "DELETE",
            f"/api/v2.1/org/{ORG}/admin/users/{ORG_USER}/",
            [],
            None,
            id="delete_org_user",
        ),
        pytest.param("delete_org_group", (ORG, 4), {}, "DELETE", f"/api/v2.1/org/{ORG}/admin/groups/4/", [], None, id="delete_org_group"),
        pytest.param(
            "delete_org_library",
            (ORG, LIBRARY),
            {},
            "DELETE",
            f"/api/v2.1/org/{ORG}/admin/repos/{LIBRARY}/",
            [],
            None,
            id="delete_org_library",
        ),
    ],
)
async def test_writes(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    snapshot: SnapshotAssertion,
    method: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    http_method: str,
    path: str,
    form: list[tuple[str, str]],
    fixture: str | None,
) -> None:
    """Test write endpoints send the right form body and parse the response."""
    aresponses.add(HOST, path, http_method, _handler({}, form, _fixture(fixture)))
    assert await getattr(seafile_client, method)(*args, **kwargs) == snapshot


@pytest.mark.parametrize(
    ("admins_only", "expected"),
    [
        pytest.param(False, ["Groups Two", "Groups User", "admin"], id="all"),
        pytest.param(True, ["Groups User", "admin"], id="admins_only"),
    ],
)
async def test_get_group_members(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    admins_only: bool,
    expected: list[str],
) -> None:
    """Test group members are fetched page by page until a short page."""
    members = json.loads(_fixture("group_members.json"))
    aresponses.add(HOST, f"/api/v2.1/groups/{GROUP}/members/", "GET", _handler({"page": "1", "per_page": "2"}, [], json.dumps(members[:2])))
    aresponses.add(HOST, f"/api/v2.1/groups/{GROUP}/members/", "GET", _handler({"page": "2", "per_page": "2"}, [], json.dumps(members[2:])))
    result = await seafile_client.get_group_members(GROUP, admins_only=admins_only, per_page=2)
    assert [member.name for member in result] == expected


async def test_get_group_libraries(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test group libraries are fetched until a short page."""
    libraries = _fixture("group_libraries.json")
    aresponses.add(HOST, f"/api/v2.1/groups/{GROUP}/libraries/", "GET", _handler({"page": "1", "per_page": "1"}, [], libraries))
    aresponses.add(HOST, f"/api/v2.1/groups/{GROUP}/libraries/", "GET", _handler({"page": "2", "per_page": "1"}, [], "[]"))
    assert await seafile_client.get_group_libraries(GROUP, per_page=1) == snapshot


async def test_get_org_users(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test organization users are fetched until `page_next` is false."""
    path = f"/api/v2.1/org/{ORG}/admin/users/"
    aresponses.add(HOST, path, "GET", _handler({"page": "1", "per_page": "1"}, [], _fixture("org_users_page1.json")))
    aresponses.add(HOST, path, "GET", _handler({"page": "2", "per_page": "1"}, [], _fixture("org_users_page2.json")))
    assert await seafile_client.get_org_users(ORG, per_page=1) == snapshot


@pytest.mark.parametrize(
    ("parent_group_id", "expected"),
    [
        pytest.param(0, False, id="group"),
        pytest.param(-1, True, id="top_department"),
        pytest.param(7, True, id="sub_department"),
    ],
)
def test_group_is_department(parent_group_id: int, expected: bool) -> None:
    """Test departments are told apart from regular groups."""
    group = json.loads(_fixture("group.json")) | {"parent_group_id": parent_group_id}
    assert Group.from_dict(group).is_department is expected
