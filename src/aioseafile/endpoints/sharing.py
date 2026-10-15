"""Share link, upload link and share endpoints."""

from typing import TYPE_CHECKING, Any

from aiohttp.hdrs import METH_DELETE, METH_POST, METH_PUT

from aioseafile.client import SeafileClient
from aioseafile.models.sharing import (
    AdminShare,
    AdminShareLinkDirent,
    AdminShareResult,
    BatchShareResult,
    FolderPermission,
    FolderPermissionResult,
    LibraryLink,
    LinkDeleteResult,
    ReceivedShare,
    SendLinkResult,
    SharedFolder,
    SharedItem,
    SharedLibrary,
    ShareLink,
    ShareLinkDirent,
    ShareLinkEmailsResult,
    ShareLinkScope,
    ShareLinkUser,
    ShareLinkUsersResult,
    ShareResult,
    ShareType,
    UploadLink,
)

if TYPE_CHECKING:
    from datetime import datetime

    from yarl import URL


def _expiry(expire_days: int | None, expiration_time: datetime | None) -> dict[str, Any]:
    """Build the expiry fields shared by the link endpoints; Seafile rejects both at once."""
    body: dict[str, Any] = {}
    if expire_days is not None:
        body["expire_days"] = expire_days
    if expiration_time is not None:
        body["expiration_time"] = expiration_time.isoformat()
    return body


def _drop_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


class SharingMixin(SeafileClient):  # pylint: disable=too-many-public-methods
    """Share link, upload link and share endpoints."""

    async def get_share_links(self, library_id: str | None = None, path: str | None = None, *, per_page: int = 100) -> list[ShareLink]:
        """Return the share links created by the account.

        Args:
        ----
            library_id: Only links in this library.
            path: Only links to this file or folder; requires `library_id`.
            per_page: Links fetched per request.

        """
        links: list[ShareLink] = []
        page = 1
        while True:
            params = _drop_none({"repo_id": library_id, "path": path, "page": page, "per_page": per_page})
            result = await self._request("api/v2.1/share-links/", params=params)
            links.extend(ShareLink.from_dict(item) for item in result)
            if len(result) < per_page:
                return links
            page += 1

    async def get_share_link(self, token: str) -> ShareLink:
        """Return a share link."""
        return ShareLink.from_dict(await self._request(f"api/v2.1/share-links/{token}/"))

    async def create_share_link(  # pylint: disable=too-many-arguments
        self,
        library_id: str,
        path: str,
        *,
        password: str | None = None,
        expire_days: int | None = None,
        expiration_time: datetime | None = None,
        can_edit: bool = False,
        can_download: bool = True,
        can_upload: bool = False,
        user_scope: ShareLinkScope | None = None,
        users: list[str] | None = None,
        description: str | None = None,
        allow_multiple: bool = False,
    ) -> ShareLink:
        """Create a share link to a file or folder.

        Args:
        ----
            library_id: Library of the file or folder.
            path: Path of the file or folder.
            password: Password visitors must enter.
            expire_days: Days until the link expires; exclusive with `expiration_time`.
            expiration_time: Moment the link expires.
            can_edit: Visitors may edit the file online.
            can_download: Visitors may download.
            can_upload: Visitors may upload to the folder.
            user_scope: Restrict who may open the link.
            users: Accounts (SPECIFIC_USERS) or email addresses (SPECIFIC_EMAILS) allowed to open the link.
            description: Description of the link.
            allow_multiple: Create another link even if the item already has one.

        """
        body: dict[str, Any] = {
            "repo_id": library_id,
            "path": path,
            "permissions": {"can_edit": can_edit, "can_download": can_download, "can_upload": can_upload},
            **_expiry(expire_days, expiration_time),
            **_drop_none({"password": password, "description": description, "user_scope": user_scope}),
        }
        if users is not None:
            # Seafile reads a list for specific users but a comma separated string for emails.
            body["emails"] = ",".join(users) if user_scope is ShareLinkScope.SPECIFIC_EMAILS else users
        uri = "api/v2.1/multi-share-links/" if allow_multiple else "api/v2.1/share-links/"
        return ShareLink.from_dict(await self._request(uri, method=METH_POST, json_body=body))

    async def create_share_links(  # pylint: disable=too-many-arguments
        self,
        library_id: str,
        path: str,
        number: int,
        *,
        auto_generate_password: bool = False,
        expire_days: int | None = None,
        expiration_time: datetime | None = None,
        can_edit: bool = False,
        can_download: bool = True,
        can_upload: bool = False,
    ) -> list[ShareLink]:
        """Create several share links to the same file or folder at once.

        Args:
        ----
            library_id: Library of the file or folder.
            path: Path of the file or folder.
            number: Number of links to create.
            auto_generate_password: Give each link its own random password.
            expire_days: Days until the links expire; exclusive with `expiration_time`.
            expiration_time: Moment the links expire.
            can_edit: Visitors may edit the file online.
            can_download: Visitors may download.
            can_upload: Visitors may upload to the folder.

        """
        body: dict[str, Any] = {
            "repo_id": library_id,
            "path": path,
            "number": number,
            "auto_generate_password": "true" if auto_generate_password else "false",
            "permissions": {"can_edit": can_edit, "can_download": can_download, "can_upload": can_upload},
            **_expiry(expire_days, expiration_time),
        }
        result = await self._request("api/v2.1/multi-share-links/batch/", method=METH_POST, json_body=body)
        return [ShareLink.from_dict(item) for item in result]

    async def update_share_link(  # pylint: disable=too-many-arguments
        self,
        token: str,
        *,
        can_edit: bool | None = None,
        can_download: bool | None = None,
        can_upload: bool | None = None,
        expire_days: int | None = None,
        expiration_time: datetime | None = None,
        user_scope: ShareLinkScope | None = None,
        description: str | None = None,
    ) -> ShareLink:
        """Update the permissions, expiry, scope or description of a share link.

        Permissions left out fall back to Seafile's defaults (download only) when any permission is given.
        """
        permissions = _drop_none({"can_edit": can_edit, "can_download": can_download, "can_upload": can_upload})
        body: dict[str, Any] = {
            **_expiry(expire_days, expiration_time),
            **_drop_none({"user_scope": user_scope, "description": description}),
        }
        if permissions:
            body["permissions"] = permissions
        return ShareLink.from_dict(await self._request(f"api/v2.1/share-links/{token}/", method=METH_PUT, json_body=body))

    async def delete_share_link(self, token: str) -> None:
        """Delete a share link."""
        await self._request(f"api/v2.1/share-links/{token}/", method=METH_DELETE)

    async def delete_share_links(self, tokens: list[str]) -> LinkDeleteResult:
        """Delete several share links."""
        return LinkDeleteResult.from_dict(await self._request("api/v2.1/share-links/", method=METH_DELETE, json_body={"tokens": tokens}))

    async def delete_invalid_share_links(self) -> None:
        """Delete the account's expired share links and links to items that no longer exist."""
        await self._request("api/v2.1/share-links/clean-invalid/", method=METH_DELETE)

    async def get_share_link_dirents(self, token: str, path: str = "/") -> list[ShareLinkDirent]:
        """Return the entries of a folder in a folder share link without a password.

        Args:
        ----
            token: Share link token.
            path: Folder relative to the shared folder.

        """
        result = await self._request(f"api/v2.1/share-links/{token}/dirents/", params={"path": path})
        return [ShareLinkDirent.from_dict(item) for item in result["dirent_list"]]

    async def get_share_link_users(self, token: str, path: str) -> list[ShareLinkUser]:
        """Return the users allowed to open a share link scoped to specific users.

        Args:
        ----
            token: Share link token.
            path: Path of the shared item, used for the permission check.

        """
        result = await self._request(f"api/v2.1/share-links/{token}/user-auth/", params={"path": path})
        return [ShareLinkUser.from_dict(item) for item in result["auth_list"]]

    async def add_share_link_users(self, token: str, path: str, users: list[str]) -> ShareLinkUsersResult:
        """Allow users to open a share link scoped to specific users."""
        result = await self._request(f"api/v2.1/share-links/{token}/user-auth/", method=METH_POST, params={"path": path}, json_body={"emails": users})
        return ShareLinkUsersResult.from_dict(result)

    async def delete_share_link_users(self, token: str, path: str, users: list[str]) -> None:
        """Remove users from a share link scoped to specific users."""
        await self._request(f"api/v2.1/share-links/{token}/user-auth/", method=METH_DELETE, params={"path": path}, json_body={"emails": users})

    async def get_share_link_emails(self, token: str, path: str) -> list[str]:
        """Return the email addresses allowed to open a share link scoped to specific emails (needs email configured)."""
        result = await self._request(f"api/v2.1/share-links/{token}/email-auth/", params={"path": path})
        return [str(email) for email in result["auth_list"]]

    async def add_share_link_emails(self, token: str, path: str, emails: list[str]) -> ShareLinkEmailsResult:
        """Allow email addresses to open a share link scoped to specific emails; Seafile mails them the link."""
        result = await self._request(
            f"api/v2.1/share-links/{token}/email-auth/", method=METH_POST, params={"path": path}, json_body={"emails": ",".join(emails)}
        )
        return ShareLinkEmailsResult.from_dict(result)

    async def delete_share_link_emails(self, token: str, path: str, emails: list[str]) -> None:
        """Remove email addresses from a share link scoped to specific emails."""
        await self._request(f"api/v2.1/share-links/{token}/email-auth/", method=METH_DELETE, params={"path": path}, json_body={"emails": emails})

    async def send_share_link(
        self, token: str, emails: list[str], *, message: str | None = None, send_password_separately: bool = False
    ) -> SendLinkResult:
        """Email a share link (needs email configured on the server).

        Args:
        ----
            token: Share link token.
            emails: Recipients.
            message: Extra message in the email.
            send_password_separately: Send the link password in a separate email.

        """
        data = {
            "token": token,
            "email": ",".join(emails),
            "extra_msg": message or "",
            "send_password_separately": str(send_password_separately).lower(),
        }
        return SendLinkResult.from_dict(await self._request("api2/send-share-link/", method=METH_POST, data=data))

    async def get_upload_links(self, library_id: str | None = None, path: str | None = None) -> list[UploadLink]:
        """Return the upload links created by the account.

        Args:
        ----
            library_id: Only links in this library.
            path: Only links to this folder; requires `library_id`.

        """
        result = await self._request("api/v2.1/upload-links/", params=_drop_none({"repo_id": library_id, "path": path}))
        return [UploadLink.from_dict(item) for item in result]

    async def get_upload_link_details(self, token: str) -> UploadLink:
        """Return an upload link."""
        return UploadLink.from_dict(await self._request(f"api/v2.1/upload-links/{token}/"))

    async def create_upload_link(  # pylint: disable=too-many-arguments
        self,
        library_id: str,
        path: str,
        *,
        password: str | None = None,
        expire_days: int | None = None,
        expiration_time: datetime | None = None,
        description: str | None = None,
    ) -> UploadLink:
        """Create an upload link to a folder, or return the existing one.

        Args:
        ----
            library_id: Library of the folder.
            path: Path of the folder.
            password: Password visitors must enter.
            expire_days: Days until the link expires; exclusive with `expiration_time`.
            expiration_time: Moment the link expires.
            description: Description of the link.

        """
        data = {
            "repo_id": library_id,
            "path": path,
            **_expiry(expire_days, expiration_time),
            **_drop_none({"password": password, "description": description}),
        }
        return UploadLink.from_dict(await self._request("api/v2.1/upload-links/", method=METH_POST, data=data))

    async def update_upload_link(self, token: str, *, expire_days: int | None = None, expiration_time: datetime | None = None) -> UploadLink:
        """Update the expiry of an upload link."""
        data = _expiry(expire_days, expiration_time)
        return UploadLink.from_dict(await self._request(f"api/v2.1/upload-links/{token}/", method=METH_PUT, data=data))

    async def delete_upload_link(self, token: str) -> None:
        """Delete an upload link."""
        await self._request(f"api/v2.1/upload-links/{token}/", method=METH_DELETE)

    async def delete_upload_links(self, tokens: list[str]) -> LinkDeleteResult:
        """Delete several upload links."""
        return LinkDeleteResult.from_dict(await self._request("api/v2.1/upload-links/", method=METH_DELETE, json_body={"tokens": tokens}))

    async def delete_invalid_upload_links(self) -> None:
        """Delete the account's expired upload links and links to folders that no longer exist."""
        await self._request("api/v2.1/upload-links/clean-invalid/", method=METH_DELETE)

    async def get_upload_link_upload_url(self, token: str) -> URL:
        """Return a file server URL to upload files through an upload link without a password."""
        result = await self._request(f"api/v2.1/upload-links/{token}/upload/")
        return self.file_server_link(result["upload_link"])

    async def send_upload_link(
        self, token: str, emails: list[str], *, message: str | None = None, send_password_separately: bool = False
    ) -> SendLinkResult:
        """Email an upload link (needs email configured on the server).

        Args:
        ----
            token: Upload link token.
            emails: Recipients.
            message: Extra message in the email.
            send_password_separately: Send the link password in a separate email.

        """
        data = {
            "token": token,
            "email": ",".join(emails),
            "extra_msg": message or "",
            "send_password_separately": str(send_password_separately).lower(),
        }
        return SendLinkResult.from_dict(await self._request("api2/send-upload-link/", method=METH_POST, data=data))

    async def get_library_share_links(self, library_id: str, *, per_page: int = 100) -> list[LibraryLink]:
        """Return the share links of all users in a library (library owner or admin)."""
        links: list[LibraryLink] = []
        page = 1
        while True:
            result = await self._request(f"api/v2.1/repos/{library_id}/share-links/", params={"page": page, "per_page": per_page})
            links.extend(LibraryLink.from_dict(item) for item in result)
            if len(result) < per_page:
                return links
            page += 1

    async def delete_library_share_link(self, library_id: str, token: str) -> None:
        """Delete a share link in a library (library owner or admin)."""
        await self._request(f"api/v2.1/repos/{library_id}/share-links/{token}/", method=METH_DELETE)

    async def get_library_upload_links(self, library_id: str, *, per_page: int = 100) -> list[LibraryLink]:
        """Return the upload links of all users in a library (library owner or admin)."""
        links: list[LibraryLink] = []
        page = 1
        while True:
            result = await self._request(f"api/v2.1/repos/{library_id}/upload-links/", params={"page": page, "per_page": per_page})
            links.extend(LibraryLink.from_dict(item) for item in result)
            if len(result) < per_page:
                return links
            page += 1

    async def delete_library_upload_link(self, library_id: str, token: str) -> None:
        """Delete an upload link in a library (library owner or admin)."""
        await self._request(f"api/v2.1/repos/{library_id}/upload-links/{token}/", method=METH_DELETE)

    async def get_shares(self, library_id: str, path: str = "/", *, share_type: ShareType | None = None) -> list[SharedItem]:
        """Return the users and groups a library or folder is shared to.

        Args:
        ----
            library_id: Library ID.
            path: Folder; '/' for the library itself.
            share_type: Only user or only group shares.

        """
        params = _drop_none({"p": path, "share_type": share_type})
        result = await self._request(f"api2/repos/{library_id}/dir/shared_items/", params=params)
        return [SharedItem.from_dict(item) for item in result]

    async def share_to_users(self, library_id: str, users: list[str], permission: str = "r", *, path: str = "/") -> ShareResult:
        """Share a library or folder to users.

        Args:
        ----
            library_id: Library ID.
            users: Account IDs (the `email` of an account, which may be a virtual ID).
            permission: 'r', 'rw', 'admin', 'cloud-edit', 'preview' or a custom permission.
            path: Folder; '/' for the library itself.

        """
        data = [("share_type", "user"), ("permission", permission), *(("username", user) for user in users)]
        result = await self._request(f"api2/repos/{library_id}/dir/shared_items/", method=METH_PUT, params={"p": path}, data=data)
        return ShareResult.from_dict(result)

    async def share_to_groups(self, library_id: str, group_ids: list[int], permission: str = "r", *, path: str = "/") -> ShareResult:
        """Share a library or folder to groups."""
        data = [("share_type", "group"), ("permission", permission), *(("group_id", str(group_id)) for group_id in group_ids)]
        result = await self._request(f"api2/repos/{library_id}/dir/shared_items/", method=METH_PUT, params={"p": path}, data=data)
        return ShareResult.from_dict(result)

    async def update_user_share(self, library_id: str, user: str, permission: str, *, path: str = "/") -> None:
        """Change the permission of a user share of a library or folder."""
        params = {"p": path, "share_type": "user", "username": user}
        await self._request(f"api2/repos/{library_id}/dir/shared_items/", method=METH_POST, params=params, data={"permission": permission})

    async def update_group_share(self, library_id: str, group_id: int, permission: str, *, path: str = "/") -> None:
        """Change the permission of a group share of a library or folder."""
        params = {"p": path, "share_type": "group", "group_id": group_id}
        await self._request(f"api2/repos/{library_id}/dir/shared_items/", method=METH_POST, params=params, data={"permission": permission})

    async def delete_user_share(self, library_id: str, user: str, *, path: str = "/") -> None:
        """Stop sharing a library or folder to a user."""
        params = {"p": path, "share_type": "user", "username": user}
        await self._request(f"api2/repos/{library_id}/dir/shared_items/", method=METH_DELETE, params=params)

    async def delete_group_share(self, library_id: str, group_id: int, *, path: str = "/") -> None:
        """Stop sharing a library or folder to a group."""
        params = {"p": path, "share_type": "group", "group_id": group_id}
        await self._request(f"api2/repos/{library_id}/dir/shared_items/", method=METH_DELETE, params=params)

    async def _batch_share(self, operation: str, library_ids: list[str], target: dict[str, str]) -> BatchShareResult:
        data = [("operation", operation), *target.items(), *(("repo_id", library_id) for library_id in library_ids)]
        return BatchShareResult.from_dict(await self._request("api/v2.1/repos/batch/", method=METH_POST, data=data))

    async def share_libraries_to_user(self, library_ids: list[str], user: str, permission: str = "rw") -> BatchShareResult:
        """Share several libraries to a user."""
        return await self._batch_share("share", library_ids, {"share_type": "user", "username": user, "permission": permission})

    async def share_libraries_to_group(self, library_ids: list[str], group_id: int, permission: str = "rw") -> BatchShareResult:
        """Share several libraries to a group."""
        return await self._batch_share("share", library_ids, {"share_type": "group", "group_id": str(group_id), "permission": permission})

    async def unshare_libraries_from_user(self, library_ids: list[str], user: str) -> BatchShareResult:
        """Stop sharing several libraries to a user."""
        return await self._batch_share("unshare", library_ids, {"share_type": "user", "username": user})

    async def unshare_libraries_from_group(self, library_ids: list[str], group_id: int) -> BatchShareResult:
        """Stop sharing several libraries to a group."""
        return await self._batch_share("unshare", library_ids, {"share_type": "group", "group_id": str(group_id)})

    async def get_shared_libraries(self) -> list[SharedLibrary]:
        """Return the libraries the account shares to users, groups or everyone."""
        return [SharedLibrary.from_dict(item) for item in await self._request("api/v2.1/shared-repos/")]

    async def get_shared_folders(self) -> list[SharedFolder]:
        """Return the folders the account shares to users or groups."""
        return [SharedFolder.from_dict(item) for item in await self._request("api/v2.1/shared-folders/")]

    async def get_received_shares(self) -> list[ReceivedShare]:
        """Return the libraries and folders shared to the account, including group and public libraries."""
        return [ReceivedShare.from_dict(item) for item in await self._request("api2/beshared-repos/")]

    async def leave_share(self, library_id: str, owner: str, *, group_id: int | None = None) -> None:
        """Leave a library or folder shared to the account.

        Args:
        ----
            library_id: The shared library, or for a folder its `repo_id` from `get_received_shares`.
            owner: Account that shared it (`user` of the received share).
            group_id: Leave a group share instead; needs group admin rights.

        """
        params: dict[str, Any] = {"share_type": "personal", "from": owner}
        if group_id is not None:
            params = {"share_type": "group", "from": owner, "group_id": group_id}
        await self._request(f"api2/beshared-repos/{library_id}/", method=METH_DELETE, params=params)

    async def get_user_folder_permissions(self, library_id: str, path: str | None = None) -> list[FolderPermission]:
        """Return the user sub-folder permissions of a library (Pro).

        Args:
        ----
            library_id: Library ID.
            path: Only permissions of this folder.

        """
        result = await self._request(f"api2/repos/{library_id}/user-folder-perm/", params=_drop_none({"folder_path": path}))
        return [FolderPermission.from_dict(item) for item in result]

    async def create_user_folder_permissions(self, library_id: str, path: str, users: list[str], permission: str) -> FolderPermissionResult:
        """Set a sub-folder permission for users that have none on it yet (Pro)."""
        data = [("folder_path", path), ("permission", permission), *(("user_email", user) for user in users)]
        result = await self._request(f"api2/repos/{library_id}/user-folder-perm/", method=METH_POST, data=data)
        return FolderPermissionResult.from_dict(result)

    async def update_user_folder_permission(self, library_id: str, path: str, user: str, permission: str) -> FolderPermission:
        """Change a user sub-folder permission (Pro)."""
        data = {"folder_path": path, "user_email": user, "permission": permission}
        return FolderPermission.from_dict(await self._request(f"api2/repos/{library_id}/user-folder-perm/", method=METH_PUT, data=data))

    async def delete_user_folder_permission(self, library_id: str, path: str, user: str) -> None:
        """Remove a user sub-folder permission (Pro)."""
        await self._request(f"api2/repos/{library_id}/user-folder-perm/", method=METH_DELETE, data={"folder_path": path, "user_email": user})

    async def get_group_folder_permissions(self, library_id: str, path: str | None = None) -> list[FolderPermission]:
        """Return the group sub-folder permissions of a library (Pro)."""
        result = await self._request(f"api2/repos/{library_id}/group-folder-perm/", params=_drop_none({"folder_path": path}))
        return [FolderPermission.from_dict(item) for item in result]

    async def create_group_folder_permissions(self, library_id: str, path: str, group_ids: list[int], permission: str) -> FolderPermissionResult:
        """Set a sub-folder permission for groups that have none on it yet (Pro)."""
        data = [("folder_path", path), ("permission", permission), *(("group_id", str(group_id)) for group_id in group_ids)]
        result = await self._request(f"api2/repos/{library_id}/group-folder-perm/", method=METH_POST, data=data)
        return FolderPermissionResult.from_dict(result)

    async def update_group_folder_permission(self, library_id: str, path: str, group_id: int, permission: str) -> FolderPermission:
        """Change a group sub-folder permission (Pro)."""
        data = {"folder_path": path, "group_id": str(group_id), "permission": permission}
        return FolderPermission.from_dict(await self._request(f"api2/repos/{library_id}/group-folder-perm/", method=METH_PUT, data=data))

    async def delete_group_folder_permission(self, library_id: str, path: str, group_id: int) -> None:
        """Remove a group sub-folder permission (Pro)."""
        data = {"folder_path": path, "group_id": str(group_id)}
        await self._request(f"api2/repos/{library_id}/group-folder-perm/", method=METH_DELETE, data=data)

    async def get_admin_share_link_dirents(self, token: str, path: str = "/") -> list[AdminShareLinkDirent]:
        """Return the entries of a folder in a folder share link (admin)."""
        result = await self._request(f"api/v2.1/admin/share-links/{token}/dirents/", params={"path": path})
        return [AdminShareLinkDirent.from_dict(item) for item in result]

    async def get_admin_shares(self, library_id: str, share_type: ShareType, *, path: str = "/") -> list[AdminShare]:
        """Return the user or group shares of any library or folder (admin)."""
        params = {"repo_id": library_id, "share_type": share_type, "path": path}
        return [AdminShare.from_dict(item) for item in await self._request("api/v2.1/admin/shares/", params=params)]

    async def create_admin_shares(  # pylint: disable=too-many-arguments
        self, library_id: str, share_type: ShareType, share_to: list[str | int], permission: str, *, path: str = "/"
    ) -> AdminShareResult:
        """Share any library or folder to users or groups (admin).

        Args:
        ----
            library_id: Library ID.
            share_type: Share to users or to groups.
            share_to: Account IDs or group IDs.
            permission: 'r', 'rw', 'admin' or a custom permission.
            path: Folder; '/' for the library itself.

        """
        data = [("repo_id", library_id), ("path", path), ("share_type", str(share_type)), ("permission", permission)]
        data.extend(("share_to", str(target)) for target in share_to)
        return AdminShareResult.from_dict(await self._request("api/v2.1/admin/shares/", method=METH_POST, data=data))

    async def update_admin_share(  # pylint: disable=too-many-arguments
        self, library_id: str, share_type: ShareType, share_to: str | int, permission: str, *, path: str = "/"
    ) -> AdminShare:
        """Change the permission of a user or group share (admin)."""
        data = {"repo_id": library_id, "path": path, "share_type": str(share_type), "share_to": str(share_to), "permission": permission}
        return AdminShare.from_dict(await self._request("api/v2.1/admin/shares/", method=METH_PUT, data=data))

    async def delete_admin_share(self, library_id: str, share_type: ShareType, share_to: str | int, *, path: str = "/") -> None:
        """Remove a user or group share (admin)."""
        data = {"repo_id": library_id, "path": path, "share_type": str(share_type), "share_to": str(share_to)}
        await self._request("api/v2.1/admin/shares/", method=METH_DELETE, data=data)

    async def get_admin_user_shared_libraries(self, user: str) -> list[SharedLibrary]:
        """Return the libraries a user shares out (admin)."""
        return [SharedLibrary.from_dict(item) for item in await self._request(f"api/v2.1/admin/users/{user}/shared-repos/")]

    async def get_admin_user_shared_folders(self, user: str) -> list[SharedFolder]:
        """Return the folders a user shares out (admin)."""
        return [SharedFolder.from_dict(item) for item in await self._request(f"api/v2.1/admin/users/{user}/shared-folders/")]
