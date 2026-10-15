"""Group, department and organization endpoints."""

from typing import Any

from aiohttp.hdrs import METH_DELETE, METH_POST, METH_PUT

from aioseafile.client import SeafileClient
from aioseafile.models.groups import (
    Department,
    DepartmentLibrary,
    DepartmentLibraryGroupShare,
    DepartmentLibraryGroupShareResult,
    DepartmentLibraryUserShare,
    DepartmentLibraryUserShareResult,
    Group,
    GroupInviteLink,
    GroupLibrary,
    GroupMember,
    GroupMembersResult,
    OrgGroup,
    OrgInfo,
    OrgLibrary,
    OrgUser,
)


class GroupsMixin(SeafileClient):  # pylint: disable=too-many-public-methods
    """Group, department and organization endpoints."""

    async def _get_all_pages(self, uri: str, per_page: int, params: dict[str, Any] | None = None) -> list[Any]:
        """Fetch a list endpoint that pages by slicing, until a short page is returned."""
        items: list[Any] = []
        page = 1
        while True:
            result = await self._request(uri, params={**(params or {}), "page": page, "per_page": per_page})
            items.extend(result)
            if len(result) < per_page:
                return items
            page += 1

    async def _get_org_pages(self, uri: str, key: str, per_page: int) -> list[Any]:
        """Fetch an org admin list endpoint that pages with `page_next`."""
        items: list[Any] = []
        page = 1
        while True:
            result = await self._request(uri, params={"page": page, "per_page": per_page})
            items.extend(result[key])
            if not result["page_next"]:
                return items
            page += 1

    async def get_groups(self, *, with_libraries: bool = False) -> list[Group]:
        """Return the groups the account is a member of.

        Args:
        ----
            with_libraries: Also return the libraries shared with each group in `Group.libraries`.

        """
        params = {"with_repos": 1} if with_libraries else None
        return [Group.from_dict(item) for item in await self._request("api/v2.1/groups/", params=params)]

    async def get_all_groups(self) -> list[Group]:
        """Return every group on the server."""
        return [Group.from_dict(item) for item in await self._request("api/v2.1/all-groups/")]

    async def get_shareable_groups(self) -> list[Group]:
        """Return the groups the account can share a library with."""
        return [Group.from_dict(item) for item in await self._request("api/v2.1/shareable-groups/")]

    async def search_groups(self, query: str) -> list[Group]:
        """Return the groups whose name contains `query` (case-insensitive)."""
        return [Group.from_dict(item) for item in await self._request("api/v2.1/search-group/", params={"q": query})]

    async def get_group(self, group_id: int) -> Group:
        """Return a group the account is a member of."""
        return Group.from_dict(await self._request(f"api/v2.1/groups/{group_id}/"))

    async def create_group(self, name: str) -> Group:
        """Create a group owned by the account."""
        return Group.from_dict(await self._request("api/v2.1/groups/", method=METH_POST, data={"name": name}))

    async def rename_group(self, group_id: int, name: str) -> Group:
        """Rename a group (group owner or admin)."""
        return Group.from_dict(await self._request(f"api/v2.1/groups/{group_id}/", method=METH_PUT, data={"name": name}))

    async def transfer_group(self, group_id: int, owner: str) -> Group:
        """Transfer a group to a new owner (group owner); the new owner is added as member and admin."""
        return Group.from_dict(await self._request(f"api/v2.1/groups/{group_id}/", method=METH_PUT, data={"owner": owner}))

    async def delete_group(self, group_id: int) -> None:
        """Dismiss a group (group owner)."""
        await self._request(f"api/v2.1/groups/{group_id}/", method=METH_DELETE)

    async def get_group_members(self, group_id: int, *, admins_only: bool = False, per_page: int = 100) -> list[GroupMember]:
        """Return the members of a group.

        Args:
        ----
            group_id: Group to list.
            admins_only: Only return the owner and admins.
            per_page: Number of members to fetch per request.

        """
        result = await self._get_all_pages(f"api/v2.1/groups/{group_id}/members/", per_page)
        members = [GroupMember.from_dict(item) for item in result]
        return [member for member in members if member.is_admin] if admins_only else members

    async def get_group_member(self, group_id: int, email: str) -> GroupMember:
        """Return a member of a group."""
        return GroupMember.from_dict(await self._request(f"api/v2.1/groups/{group_id}/members/{email}/"))

    async def search_group_members(self, group_id: int, query: str) -> list[GroupMember]:
        """Return the members of a group whose email contains `query`."""
        result = await self._request(f"api/v2.1/groups/{group_id}/search-member/", params={"q": query})
        return [GroupMember.from_dict(item) for item in result]

    async def add_group_member(self, group_id: int, email: str) -> GroupMember:
        """Add a user to a group (group owner or admin)."""
        return GroupMember.from_dict(await self._request(f"api/v2.1/groups/{group_id}/members/", method=METH_POST, data={"email": email}))

    async def add_group_members(self, group_id: int, emails: list[str]) -> GroupMembersResult:
        """Add several users to a group (group owner or admin); users that can't be added are listed in `failed`."""
        result = await self._request(f"api/v2.1/groups/{group_id}/members/bulk/", method=METH_POST, data={"emails": ",".join(emails)})
        return GroupMembersResult.from_dict(result)

    async def set_group_member_admin(self, group_id: int, email: str, *, is_admin: bool) -> GroupMember:
        """Make a member a group admin, or revoke it (group owner)."""
        data = {"is_admin": "true" if is_admin else "false"}
        return GroupMember.from_dict(await self._request(f"api/v2.1/groups/{group_id}/members/{email}/", method=METH_PUT, data=data))

    async def remove_group_member(self, group_id: int, email: str) -> None:
        """Remove a member from a group, or leave it when `email` is the account itself.

        Libraries the member shared with the group are unshared.
        """
        await self._request(f"api/v2.1/groups/{group_id}/members/{email}/", method=METH_DELETE)

    async def get_group_invite_links(self, group_id: int) -> list[GroupInviteLink]:
        """Return the invite links of a group (group owner or admin; not for departments or multi-tenancy)."""
        result = await self._request(f"api/v2.1/groups/{group_id}/invite-links/")
        return [GroupInviteLink.from_dict(item) for item in result["group_invite_link_list"]]

    async def create_group_invite_link(self, group_id: int) -> GroupInviteLink:
        """Create a link that lets users join a group."""
        return GroupInviteLink.from_dict(await self._request(f"api/v2.1/groups/{group_id}/invite-links/", method=METH_POST))

    async def delete_group_invite_link(self, group_id: int, token: str) -> None:
        """Delete an invite link of a group."""
        await self._request(f"api/v2.1/groups/{group_id}/invite-links/{token}/", method=METH_DELETE)

    async def get_group_libraries(self, group_id: int, *, per_page: int = 100) -> list[GroupLibrary]:
        """Return the libraries shared with a group, most recently modified first."""
        result = await self._get_all_pages(f"api/v2.1/groups/{group_id}/libraries/", per_page)
        return [GroupLibrary.from_dict(item) for item in result]

    async def create_group_library(self, group_id: int, name: str, *, permission: str = "rw", password: str | None = None) -> GroupLibrary:
        """Create a library owned by the account and share it with a group.

        Args:
        ----
            group_id: Group to share the library with.
            name: Library name.
            permission: Permission of the group members, 'r' or 'rw' (or a custom permission).
            password: Create an encrypted library with this password.

        """
        data = {"repo_name": name, "permission": permission}
        if password is not None:
            data["password"] = password
        return GroupLibrary.from_dict(await self._request(f"api/v2.1/groups/{group_id}/libraries/", method=METH_POST, data=data))

    async def unshare_group_library(self, group_id: int, library_id: str) -> None:
        """Stop sharing a library with a group (library owner or admin, or group admin); the library itself is kept."""
        await self._request(f"api/v2.1/groups/{group_id}/libraries/{library_id}/", method=METH_DELETE)

    async def get_departments(self, *, can_admin: bool = False) -> list[Department]:
        """Return the departments the account is a member of (Pro).

        Args:
        ----
            can_admin: Only return the departments the account is an admin of.

        """
        result = await self._request("api/v2.1/departments/", params={"can_admin": "true" if can_admin else "false"})
        return [Department.from_dict(item) for item in result]

    async def get_address_book_departments(self) -> list[Department]:
        """Return all departments in the address book, including sub-departments."""
        result = await self._request("api/v2.1/address-book/departments/")
        return [Department.from_dict(item) for item in result["departments"]]

    async def get_department_members(self, department_id: int) -> list[GroupMember]:
        """Return the members of a department from the address book."""
        result = await self._request(f"api/v2.1/address-book/departments/{department_id}/members/")
        return [GroupMember.from_dict(item) for item in result["members"]]

    async def get_department_sub_departments(self, department_id: int) -> list[Department]:
        """Return all sub-departments of a department (Pro, department admin)."""
        result = await self._request(f"api/v2.1/address-book/groups/{department_id}/sub-groups/")
        return [Department.from_dict(item) for item in result]

    async def create_department_library(
        self, department_id: int, name: str, *, permission: str = "rw", password: str | None = None
    ) -> DepartmentLibrary:
        """Create a library owned by a department (Pro, department admin).

        Args:
        ----
            department_id: Department that will own the library.
            name: Library name.
            permission: Permission of the department members, 'r' or 'rw'.
            password: Create an encrypted library with this password.

        """
        data = {"name": name, "permission": permission}
        if password is not None:
            data["passwd"] = password
        result = await self._request(f"api/v2.1/groups/{department_id}/group-owned-libraries/", method=METH_POST, data=data)
        return DepartmentLibrary.from_dict(result)

    async def rename_department_library(self, department_id: int, library_id: str, name: str) -> DepartmentLibrary:
        """Rename a department library (Pro, department admin)."""
        result = await self._request(f"api/v2.1/groups/{department_id}/group-owned-libraries/{library_id}/", method=METH_PUT, data={"name": name})
        return DepartmentLibrary.from_dict(result)

    async def transfer_department_library(self, department_id: int, library_id: str, owner: str, *, reshare: bool = False) -> None:
        """Transfer a department library to a user or another department (Pro, department admin).

        Args:
        ----
            department_id: Department that owns the library.
            library_id: Library to transfer.
            owner: New owner: a user email, or '<department id>@seafile_group'.
            reshare: Keep the library's existing shares.

        """
        data = {"email": owner}
        if reshare:
            data["reshare"] = "true"
        await self._request(f"api/v2.1/groups/{department_id}/group-owned-libraries/{library_id}/transfer/", method=METH_PUT, data=data)

    async def delete_department_library(self, department_id: int, library_id: str) -> None:
        """Delete a department library (Pro, department admin)."""
        await self._request(f"api/v2.1/groups/{department_id}/group-owned-libraries/{library_id}/", method=METH_DELETE)

    async def get_department_library_user_shares(self, library_id: str, *, path: str = "/") -> list[DepartmentLibraryUserShare]:
        """Return the users a department library (or folder in it) is shared with (Pro, department admin)."""
        result = await self._request(f"api/v2.1/group-owned-libraries/{library_id}/user-share/", params={"path": path})
        return [DepartmentLibraryUserShare.from_dict(item) for item in result]

    async def share_department_library_to_users(
        self, library_id: str, users: list[str], *, permission: str = "r", path: str = "/"
    ) -> DepartmentLibraryUserShareResult:
        """Share a department library (or folder in it) with users (Pro, department admin)."""
        data = [("username", user) for user in users] + [("permission", permission), ("path", path)]
        result = await self._request(f"api/v2.1/group-owned-libraries/{library_id}/user-share/", method=METH_POST, data=data)
        return DepartmentLibraryUserShareResult.from_dict(result)

    async def update_department_library_user_share(self, library_id: str, user: str, permission: str, *, path: str = "/") -> None:
        """Change the permission of a user on a shared department library (Pro, department admin)."""
        data = {"username": user, "permission": permission, "path": path}
        await self._request(f"api/v2.1/group-owned-libraries/{library_id}/user-share/", method=METH_PUT, data=data)

    async def unshare_department_library_from_user(self, library_id: str, user: str, *, path: str = "/") -> None:
        """Stop sharing a department library (or folder in it) with a user (Pro, department admin)."""
        data = {"username": user, "path": path}
        await self._request(f"api/v2.1/group-owned-libraries/{library_id}/user-share/", method=METH_DELETE, data=data)

    async def get_department_library_group_shares(self, library_id: str, *, path: str = "/") -> list[DepartmentLibraryGroupShare]:
        """Return the other groups a department library (or folder in it) is shared with (Pro, department admin)."""
        result = await self._request(f"api/v2.1/group-owned-libraries/{library_id}/group-share/", params={"path": path})
        return [DepartmentLibraryGroupShare.from_dict(item) for item in result]

    async def share_department_library_to_groups(
        self, library_id: str, group_ids: list[int], *, permission: str = "r", path: str = "/"
    ) -> DepartmentLibraryGroupShareResult:
        """Share a department library (or folder in it) with groups (Pro, department admin)."""
        data = [("group_id", str(group_id)) for group_id in group_ids] + [("permission", permission), ("path", path)]
        result = await self._request(f"api/v2.1/group-owned-libraries/{library_id}/group-share/", method=METH_POST, data=data)
        return DepartmentLibraryGroupShareResult.from_dict(result)

    async def update_department_library_group_share(self, library_id: str, group_id: int, permission: str, *, path: str = "/") -> None:
        """Change the permission of a group on a shared department library (Pro, department admin)."""
        data = {"group_id": str(group_id), "permission": permission, "path": path}
        await self._request(f"api/v2.1/group-owned-libraries/{library_id}/group-share/", method=METH_PUT, data=data)

    async def unshare_department_library_from_group(self, library_id: str, group_id: int, *, path: str = "/") -> None:
        """Stop sharing a department library (or folder in it) with a group (Pro, department admin)."""
        data = {"group_id": str(group_id), "path": path}
        await self._request(f"api/v2.1/group-owned-libraries/{library_id}/group-share/", method=METH_DELETE, data=data)

    async def get_org_info(self) -> OrgInfo:
        """Return the organization of the account (Pro multi-tenancy, organization admin)."""
        return OrgInfo.from_dict(await self._request("api/v2.1/org/admin/info/"))

    async def update_org_info(self, *, name: str | None = None, user_default_quota_mb: int | None = None) -> OrgInfo:
        """Update the organization of the account (organization admin).

        Args:
        ----
            name: New organization name; needs ORG_ENABLE_ADMIN_CUSTOM_NAME on the server.
            user_default_quota_mb: Default storage quota for new users, in MB.

        """
        data: dict[str, str] = {}
        if name is not None:
            data["org_name"] = name
        if user_default_quota_mb is not None:
            data["user_default_quota"] = str(user_default_quota_mb)
        return OrgInfo.from_dict(await self._request("api/v2.1/org/admin/info/", method=METH_PUT, data=data))

    async def get_org_users(self, org_id: int, *, per_page: int = 100) -> list[OrgUser]:
        """Return all users of an organization (organization admin)."""
        result = await self._get_org_pages(f"api/v2.1/org/{org_id}/admin/users/", "user_list", per_page)
        return [OrgUser.from_dict(item) for item in result]

    async def get_org_user(self, org_id: int, email: str) -> OrgUser:
        """Return a user of an organization (organization admin)."""
        return OrgUser.from_dict(await self._request(f"api/v2.1/org/{org_id}/admin/users/{email}/"))

    async def create_org_user(self, org_id: int, email: str, password: str, name: str) -> OrgUser:
        """Add a user to an organization (organization admin)."""
        data = {"email": email, "password": password, "name": name}
        return OrgUser.from_dict(await self._request(f"api/v2.1/org/{org_id}/admin/users/", method=METH_POST, data=data))

    async def update_org_user(  # pylint: disable=too-many-arguments
        self,
        org_id: int,
        email: str,
        *,
        name: str | None = None,
        contact_email: str | None = None,
        is_staff: bool | None = None,
        is_active: bool | None = None,
        quota_total_mb: int | None = None,
    ) -> OrgUser:
        """Update a user of an organization (organization admin).

        Args:
        ----
            org_id: Organization of the user.
            email: User to update.
            name: New display name.
            contact_email: New contact email.
            is_staff: Make the user an organization admin, or revoke it.
            is_active: Activate or deactivate the user.
            quota_total_mb: Storage quota in MB.

        """
        data: dict[str, str] = {}
        if name is not None:
            data["name"] = name
        if contact_email is not None:
            data["contact_email"] = contact_email
        if is_staff is not None:
            data["is_staff"] = "true" if is_staff else "false"
        if is_active is not None:
            data["is_active"] = "true" if is_active else "false"
        if quota_total_mb is not None:
            data["quota_total"] = str(quota_total_mb)
        return OrgUser.from_dict(await self._request(f"api/v2.1/org/{org_id}/admin/users/{email}/", method=METH_PUT, data=data))

    async def delete_org_user(self, org_id: int, email: str) -> None:
        """Delete a user of an organization (organization admin)."""
        await self._request(f"api/v2.1/org/{org_id}/admin/users/{email}/", method=METH_DELETE)

    async def get_org_groups(self, org_id: int, *, per_page: int = 100) -> list[OrgGroup]:
        """Return all groups of an organization (organization admin)."""
        result = await self._get_org_pages(f"api/v2.1/org/{org_id}/admin/groups/", "groups", per_page)
        return [OrgGroup.from_dict(item) for item in result]

    async def get_org_group(self, org_id: int, group_id: int) -> OrgGroup:
        """Return a group of an organization (organization admin)."""
        return OrgGroup.from_dict(await self._request(f"api/v2.1/org/{org_id}/admin/groups/{group_id}/"))

    async def delete_org_group(self, org_id: int, group_id: int) -> None:
        """Delete a group of an organization (organization admin)."""
        await self._request(f"api/v2.1/org/{org_id}/admin/groups/{group_id}/", method=METH_DELETE)

    async def get_org_libraries(self, org_id: int, *, per_page: int = 100) -> list[OrgLibrary]:
        """Return all libraries of an organization (organization admin)."""
        result = await self._get_org_pages(f"api/v2.1/org/{org_id}/admin/repos/", "repo_list", per_page)
        return [OrgLibrary.from_dict(item) for item in result]

    async def delete_org_library(self, org_id: int, library_id: str) -> None:
        """Delete a library of an organization (organization admin)."""
        await self._request(f"api/v2.1/org/{org_id}/admin/repos/{library_id}/", method=METH_DELETE)
