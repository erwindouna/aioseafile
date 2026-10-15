"""Library endpoints."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from aiohttp.hdrs import METH_DELETE, METH_POST, METH_PUT

from aioseafile.client import SeafileClient
from aioseafile.models.libraries import (
    CreatedLibrary,
    DeletedLibrary,
    Library,
    LibraryApiToken,
    LibraryApiTokenPermission,
    LibraryCommitDetail,
    LibraryDetail,
    LibraryHistory,
    LibraryInfo,
    RepoTokenDeletedFile,
    RepoTokenDir,
    RepoTokenDirent,
    RepoTokenFile,
    RepoTokenLibraryInfo,
    RepoTokenSearchResult,
    SnapshotDirent,
    SnapshotLabel,
    TrashItem,
    TrashRestoreResult,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from yarl import URL

VIA_REPO = "api/v2.1/via-repo-token/"


class LibrariesMixin(SeafileClient):  # pylint: disable=too-many-public-methods
    """Library endpoints."""

    async def get_libraries(self) -> list[Library]:
        """Return the libraries the account can access."""
        return [Library.from_dict(item) for item in await self._request("api2/repos/")]

    async def get_library(self, library_id: str) -> LibraryDetail:
        """Return the details of one library, including its file count."""
        return LibraryDetail.from_dict(await self._request(f"api2/repos/{library_id}/"))

    async def get_library_info(self, library_id: str) -> LibraryInfo:
        """Return the details of one library, including its status and sharing state."""
        return LibraryInfo.from_dict(await self._request(f"api/v2.1/repos/{library_id}/"))

    async def create_library(self, name: str, *, description: str | None = None, password: str | None = None) -> CreatedLibrary:
        """Create a library.

        Args:
        ----
            name: Name of the library.
            description: Optional description.
            password: Encrypt the library with this password.

        """
        form = {"name": name}
        if description is not None:
            form["desc"] = description
        if password is not None:
            form["passwd"] = password
        # `from=web` stops Seafile from generating a sync token for a desktop client.
        result = await self._request("api2/repos/", method=METH_POST, params={"from": "web"}, data=form)
        return CreatedLibrary.from_dict(result)

    async def rename_library(self, library_id: str, name: str, *, description: str | None = None) -> None:
        """Rename a library; only the owner can do this."""
        form = {"repo_name": name}
        if description is not None:
            form["repo_desc"] = description
        await self._request(f"api2/repos/{library_id}/", method=METH_POST, params={"op": "rename"}, data=form)

    async def delete_library(self, library_id: str) -> None:
        """Delete a library; it moves to the owner's library trash."""
        await self._request(f"api/v2.1/repos/{library_id}/", method=METH_DELETE)

    async def get_default_library(self) -> str | None:
        """Return the ID of the account's default library, or None if it has none."""
        result: dict[str, Any] = await self._request("api2/default-repo/")
        return str(result["repo_id"]) if result["exists"] else None

    async def create_default_library(self) -> str:
        """Create the account's default library if it doesn't exist and return its ID."""
        result: dict[str, str] = await self._request("api2/default-repo/", method=METH_POST)
        return result["repo_id"]

    async def get_library_owner(self, library_id: str) -> str:
        """Return the owner of a library; only the owner can ask."""
        result: dict[str, str] = await self._request(f"api2/repos/{library_id}/owner/")
        return result["owner"]

    async def transfer_library(self, library_id: str, owner: str, *, reshare: bool = False) -> None:
        """Transfer a library to another user or department.

        Args:
        ----
            library_id: The library to transfer.
            owner: The new owner's user ID (the `email` field, which is a virtual
                `...@auth.local` ID on recent servers, not the contact email).
            reshare: Keep the existing shares, with the old owner added as a share.

        """
        form = {"owner": owner}
        if reshare:
            form["reshare"] = "true"
        await self._request(f"api2/repos/{library_id}/owner/", method=METH_PUT, data=form)

    async def set_library_password(self, library_id: str, password: str) -> None:
        """Unlock an encrypted library on the server for this account.

        Raises SeafileConnectionError (400) when the password is wrong.
        """
        await self._request(f"api/v2.1/repos/{library_id}/set-password/", method=METH_POST, data={"password": password})

    async def change_library_password(self, library_id: str, old_password: str, new_password: str) -> None:
        """Change the password of an encrypted library; only the owner can do this."""
        form = {"operation": "change-password", "old_password": old_password, "new_password": new_password}
        await self._request(f"api/v2.1/repos/{library_id}/set-password/", method=METH_PUT, data=form)

    async def can_reset_library_password(self, library_id: str) -> bool:
        """Return whether the server can reset the password of an encrypted library.

        Needs ENABLE_RESET_ENCRYPTED_REPO_PASSWORD on the server.
        """
        result: dict[str, bool] = await self._request(
            f"api/v2.1/repos/{library_id}/set-password/", method=METH_PUT, data={"operation": "can-reset-password"}
        )
        return result["allowed"]

    async def reset_library_password(self, library_id: str, new_password: str) -> None:
        """Reset the password of an encrypted library without the old one.

        Needs ENABLE_RESET_ENCRYPTED_REPO_PASSWORD on the server.
        """
        form = {"operation": "reset-password", "new_password": new_password}
        await self._request(f"api/v2.1/repos/{library_id}/set-password/", method=METH_PUT, data=form)

    async def send_new_library_password(self, library_id: str) -> None:
        """Reset the password of an encrypted library to a random one and email it to the owner.

        Needs ENABLE_RESET_ENCRYPTED_REPO_PASSWORD on the server.
        """
        await self._request(f"api/v2.1/repos/{library_id}/send-new-password/", method=METH_POST)

    async def get_library_history_limit(self, library_id: str) -> int:
        """Return how many days of history a library keeps (-1 is all, 0 is none)."""
        result: dict[str, int] = await self._request(f"api2/repos/{library_id}/history-limit/")
        return result["keep_days"]

    async def set_library_history_limit(self, library_id: str, keep_days: int) -> int:
        """Set how many days of history a library keeps (-1 is all, 0 is none) and return the new value."""
        result: dict[str, int] = await self._request(f"api2/repos/{library_id}/history-limit/", method=METH_PUT, data={"keep_days": keep_days})
        return result["keep_days"]

    async def get_library_auto_delete_days(self, library_id: str) -> int:
        """Return after how many days unchanged files are deleted from a library (0 is never)."""
        result: dict[str, int] = await self._request(f"api/v2.1/repos/{library_id}/auto-delete/")
        return result["auto_delete_days"]

    async def set_library_auto_delete_days(self, library_id: str, days: int) -> int:
        """Set after how many days unchanged files are deleted from a library (0 is never) and return the new value."""
        result: dict[str, int] = await self._request(f"api/v2.1/repos/{library_id}/auto-delete/", method=METH_PUT, data={"auto_delete_days": days})
        return result["auto_delete_days"]

    async def get_library_history(self, library_id: str, *, page: int = 1, per_page: int = 100) -> LibraryHistory:
        """Return one page of the commit history of a library, newest first."""
        result = await self._request(f"api/v2.1/repos/{library_id}/history/", params={"page": page, "per_page": per_page})
        return LibraryHistory.from_dict(result)

    async def get_library_commit(self, library_id: str, commit_id: str) -> LibraryCommitDetail:
        """Return a commit of a library and the changes it made."""
        return LibraryCommitDetail.from_dict(await self._request(f"api/v2.1/repos/{library_id}/commits/{commit_id}/"))

    async def get_library_commit_dir(self, library_id: str, commit_id: str, path: str = "/") -> list[SnapshotDirent]:
        """Return the contents of a folder in a library snapshot."""
        result = await self._request(f"api/v2.1/repos/{library_id}/commits/{commit_id}/dir/", params={"path": path})
        return [SnapshotDirent.from_dict(item) for item in result["dirent_list"]]

    async def revert_library(self, library_id: str, commit_id: str) -> None:
        """Restore a library to the state of a snapshot; only the owner can do this."""
        await self._request(f"api/v2.1/repos/{library_id}/commits/{commit_id}/revert/", method=METH_POST)

    async def get_snapshot_label_names(self) -> list[str]:
        """Return the snapshot labels the account created."""
        labels: list[str] = await self._request("api/v2.1/revision-tags/tag-names/")
        return labels

    async def create_snapshot_labels(self, library_id: str, labels: Sequence[str], *, commit_id: str | None = None) -> list[SnapshotLabel]:
        """Add labels to a library snapshot.

        Args:
        ----
            library_id: The library.
            labels: Labels to add; letters, digits, dots, hyphens and underscores only.
            commit_id: The snapshot to label; defaults to the current state.

        """
        return await self._snapshot_labels(METH_POST, library_id, labels, commit_id)

    async def set_snapshot_labels(self, library_id: str, labels: Sequence[str], *, commit_id: str | None = None) -> list[SnapshotLabel]:
        """Replace the labels of a library snapshot; an empty list removes them all."""
        return await self._snapshot_labels(METH_PUT, library_id, labels, commit_id)

    async def _snapshot_labels(self, method: str, library_id: str, labels: Sequence[str], commit_id: str | None) -> list[SnapshotLabel]:
        form = {"repo_id": library_id, "tag_names": ",".join(labels)}
        if commit_id is not None:
            form["commit_id"] = commit_id
        result = await self._request("api/v2.1/revision-tags/tagged-items/", method=method, data=form)
        return [SnapshotLabel.from_dict(item) for item in result["revisionTags"]]

    async def delete_snapshot_label(self, library_id: str, label: str) -> None:
        """Remove a label from the snapshots of a library."""
        await self._request("api/v2.1/revision-tags/tagged-items/", method=METH_DELETE, params={"repo_id": library_id, "tag_name": label})

    async def get_library_trash(self, library_id: str, *, path: str = "/", show_days: int | None = None) -> list[TrashItem]:
        """Return the deleted files and folders under a folder of a library, by scanning its history.

        Args:
        ----
            library_id: The library.
            path: Only return items deleted from this folder.
            show_days: Only return items deleted in this many days.

        """
        params: dict[str, Any] = {"path": path}
        if show_days is not None:
            params["show_days"] = show_days
        items: list[TrashItem] = []
        while True:
            result = await self._request(f"api/v2.1/repos/{library_id}/trash/", params=params)
            items.extend(TrashItem.from_dict(item) for item in result["data"])
            if not result["more"]:
                return items
            params["scan_stat"] = result["scan_stat"]

    async def get_library_trash_items(self, library_id: str, *, per_page: int = 100) -> list[TrashItem]:
        """Return the deleted files and folders of a library from the trash index (`trash2`).

        Faster than `get_library_trash`; the server limits it to the last 90 days.
        """
        return await self._paged_trash(f"api/v2.1/repos/{library_id}/trash2/", {}, per_page)

    async def search_library_trash(  # pylint: disable=too-many-arguments
        self,
        library_id: str,
        *,
        query: str | None = None,
        users: Sequence[str] | None = None,
        suffixes: Sequence[str] | None = None,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        per_page: int = 100,
    ) -> list[TrashItem]:
        """Search the deleted files and folders of a library.

        Args:
        ----
            library_id: The library.
            query: Text the name must contain.
            users: Only items deleted by these users.
            suffixes: Only files with these extensions, without the dot.
            time_from: Only items deleted after this time; needs `time_to` too.
            time_to: Only items deleted before this time; needs `time_from` too.
            per_page: Page size used while fetching all results.

        """
        params: dict[str, Any] = {}
        if query is not None:
            params["q"] = query
        if users:
            params["op_users"] = ",".join(users)
        if suffixes:
            params["suffixes"] = ",".join(suffixes)
        if time_from is not None:
            params["time_from"] = int(time_from.timestamp())
        if time_to is not None:
            params["time_to"] = int(time_to.timestamp())
        return await self._paged_trash(f"api/v2.1/repos/{library_id}/trash2/search/", params, per_page)

    async def _paged_trash(self, uri: str, params: dict[str, Any], per_page: int) -> list[TrashItem]:
        items: list[TrashItem] = []
        page = 1
        while True:
            result = await self._request(uri, params={**params, "page": page, "per_page": per_page})
            items.extend(TrashItem.from_dict(item) for item in result["items"])
            if not result["items"] or len(items) >= result["total_count"]:
                return items
            page += 1

    async def clean_library_trash(self, library_id: str, *, keep_days: int = 0) -> None:
        """Permanently remove deleted items from the trash of a library.

        Args:
        ----
            library_id: The library.
            keep_days: Keep items deleted in this many days; 0 empties the trash.

        """
        await self._request(f"api/v2.1/repos/{library_id}/trash/", method=METH_DELETE, data={"keep_days": keep_days})

    async def restore_library_trash_items(self, library_id: str, commit_id: str, paths: Sequence[str]) -> TrashRestoreResult:
        """Restore deleted files and folders that share the same trash commit ID."""
        form = {"commit_id": commit_id, "path": list(paths)}
        result = await self._request(f"api/v2.1/repos/{library_id}/trash/revert-dirents/", method=METH_POST, data=form)
        return TrashRestoreResult.from_dict(result)

    async def restore_library_trash(self, library_id: str, items: Mapping[str, Sequence[str]]) -> TrashRestoreResult:
        """Restore deleted files and folders from several trash commits.

        Args:
        ----
            library_id: The library.
            items: Paths to restore, keyed by the trash item's commit ID.

        """
        body = {commit_id: list(paths) for commit_id, paths in items.items()}
        result = await self._request(f"api/v2.1/repos/{library_id}/trash2/revert/", method=METH_POST, json_body=body)
        return TrashRestoreResult.from_dict(result)

    async def get_deleted_libraries(self) -> list[DeletedLibrary]:
        """Return the account's deleted libraries."""
        return [DeletedLibrary.from_dict(item) for item in await self._request("api/v2.1/deleted-repos/")]

    async def restore_deleted_library(self, library_id: str) -> None:
        """Restore a deleted library."""
        await self._request("api/v2.1/deleted-repos/", method=METH_POST, data={"repo_id": library_id})

    async def delete_deleted_library(self, library_id: str) -> None:
        """Permanently delete one deleted library."""
        await self._request(f"api/v2.1/deleted-repos/{library_id}/", method=METH_DELETE)

    async def clean_deleted_libraries(self) -> None:
        """Permanently delete all of the account's deleted libraries."""
        await self._request("api/v2.1/deleted-repos/", method=METH_DELETE)

    async def get_library_api_tokens(self, library_id: str) -> list[LibraryApiToken]:
        """Return the API tokens of a library; only the owner or an admin can ask."""
        result = await self._request(f"api/v2.1/repos/{library_id}/repo-api-tokens/")
        return [LibraryApiToken.from_dict(item) for item in result["repo_api_tokens"]]

    async def create_library_api_token(
        self, library_id: str, app_name: str, *, permission: LibraryApiTokenPermission = LibraryApiTokenPermission.READ_WRITE
    ) -> LibraryApiToken:
        """Create an API token that gives access to one library."""
        form = {"app_name": app_name, "permission": permission.value}
        result = await self._request(f"api/v2.1/repos/{library_id}/repo-api-tokens/", method=METH_POST, data=form, retry=False)
        return LibraryApiToken.from_dict(result)

    async def update_library_api_token(self, library_id: str, app_name: str, permission: LibraryApiTokenPermission) -> LibraryApiToken:
        """Change the permission of a library API token."""
        form = {"permission": permission.value}
        result = await self._request(f"api/v2.1/repos/{library_id}/repo-api-tokens/{app_name}/", method=METH_PUT, data=form)
        return LibraryApiToken.from_dict(result)

    async def delete_library_api_token(self, library_id: str, app_name: str) -> None:
        """Delete a library API token."""
        await self._request(f"api/v2.1/repos/{library_id}/repo-api-tokens/{app_name}/", method=METH_DELETE)

    async def _via_repo_token(self, repo_token: str, uri: str, **kwargs: Any) -> Any:
        """Send a request authenticated with a library API token instead of the account token."""
        return await self._request(VIA_REPO + uri, authenticated=False, headers={"Authorization": f"Token {repo_token}"}, **kwargs)

    async def get_library_info_via_repo_token(self, repo_token: str) -> RepoTokenLibraryInfo:
        """Return the library of a library API token."""
        return RepoTokenLibraryInfo.from_dict(await self._via_repo_token(repo_token, "repo-info/"))

    async def get_dir_via_repo_token(self, repo_token: str, path: str = "/", *, recursive: bool = False) -> list[RepoTokenDirent]:
        """List a folder with a library API token.

        Args:
        ----
            repo_token: The library API token.
            path: The folder to list.
            recursive: Include the contents of all subfolders.

        """
        params = {"path": path, "recursive": "1" if recursive else "0"}
        result = await self._via_repo_token(repo_token, "dir/", params=params)
        return [RepoTokenDirent.from_dict(item) for item in result["dirent_list"]]

    async def create_dir_via_repo_token(self, repo_token: str, path: str) -> RepoTokenDir:
        """Create a folder with a library API token; a taken name gets a numbered suffix."""
        result = await self._via_repo_token(repo_token, "dir/", method=METH_POST, params={"path": path}, data={"operation": "mkdir"})
        return RepoTokenDir.from_dict(result)

    async def rename_dir_via_repo_token(self, repo_token: str, path: str, new_name: str) -> RepoTokenDir:
        """Rename a folder with a library API token; a taken name gets a numbered suffix."""
        form = {"operation": "rename", "newname": new_name}
        return RepoTokenDir.from_dict(await self._via_repo_token(repo_token, "dir/", method=METH_POST, params={"path": path}, data=form))

    async def revert_dir_via_repo_token(self, repo_token: str, path: str, commit_id: str) -> None:
        """Restore a folder to its state in a commit with a library API token."""
        form = {"operation": "revert", "commit_id": commit_id}
        await self._via_repo_token(repo_token, "dir/", method=METH_POST, params={"path": path}, data=form)

    async def delete_dir_via_repo_token(self, repo_token: str, path: str) -> None:
        """Delete a folder with a library API token."""
        await self._via_repo_token(repo_token, "dir/", method=METH_DELETE, params={"path": path})

    async def get_file_via_repo_token(self, repo_token: str, path: str) -> RepoTokenFile:
        """Return the details of a file with a library API token."""
        return RepoTokenFile.from_dict(await self._via_repo_token(repo_token, "file/", params={"path": path}))

    async def create_file_via_repo_token(self, repo_token: str, path: str) -> RepoTokenFile:
        """Create an empty file with a library API token; a taken name gets a numbered suffix."""
        return await self._file_op_via_repo_token(repo_token, path, {"operation": "create"})

    async def rename_file_via_repo_token(self, repo_token: str, path: str, new_name: str) -> RepoTokenFile:
        """Rename a file with a library API token; a taken name gets a numbered suffix."""
        return await self._file_op_via_repo_token(repo_token, path, {"operation": "rename", "newname": new_name})

    async def move_file_via_repo_token(self, repo_token: str, path: str, dst_dir: str) -> RepoTokenFile:
        """Move a file to another folder with a library API token; a taken name gets a numbered suffix."""
        return await self._file_op_via_repo_token(repo_token, path, {"operation": "move", "dst_dir": dst_dir})

    async def copy_file_via_repo_token(self, repo_token: str, path: str, dst_dir: str) -> RepoTokenFile:
        """Copy a file to another folder with a library API token and return the copy."""
        return await self._file_op_via_repo_token(repo_token, path, {"operation": "copy", "dst_dir": dst_dir})

    async def revert_file_via_repo_token(self, repo_token: str, path: str, commit_id: str) -> None:
        """Restore a file to its state in a commit with a library API token."""
        form = {"operation": "revert", "commit_id": commit_id}
        await self._via_repo_token(repo_token, "file/", method=METH_POST, params={"path": path}, data=form)

    async def _file_op_via_repo_token(self, repo_token: str, path: str, form: dict[str, Any]) -> RepoTokenFile:
        return RepoTokenFile.from_dict(await self._via_repo_token(repo_token, "file/", method=METH_POST, params={"path": path}, data=form))

    async def lock_file_via_repo_token(self, repo_token: str, path: str, *, expire: int = 0) -> RepoTokenFile:
        """Lock a file with a library API token (Pro only).

        Args:
        ----
            repo_token: The library API token.
            path: The file to lock.
            expire: Lock duration in seconds; 0 uses the server default.

        """
        form = {"operation": "lock", "expire": expire}
        return RepoTokenFile.from_dict(await self._via_repo_token(repo_token, "file/", method=METH_PUT, params={"path": path}, data=form))

    async def unlock_file_via_repo_token(self, repo_token: str, path: str) -> RepoTokenFile:
        """Unlock a file with a library API token (Pro only)."""
        form = {"operation": "unlock"}
        return RepoTokenFile.from_dict(await self._via_repo_token(repo_token, "file/", method=METH_PUT, params={"path": path}, data=form))

    async def delete_file_via_repo_token(self, repo_token: str, path: str) -> None:
        """Delete a file with a library API token; a missing file is not an error."""
        await self._via_repo_token(repo_token, "file/", method=METH_DELETE, params={"path": path})

    async def delete_items_via_repo_token(self, repo_token: str, parent_dir: str, names: Sequence[str]) -> None:
        """Delete several files and folders in one folder with a library API token."""
        body = {"parent_dir": parent_dir, "dirents": list(names)}
        await self._via_repo_token(repo_token, "batch-delete-item/", method=METH_DELETE, json_body=body)

    async def move_items_via_repo_token(self, repo_token: str, src_parent_dir: str, names: Sequence[str], dst_parent_dir: str) -> None:
        """Move several files and folders to another folder with a library API token."""
        body = {"src_parent_dir": src_parent_dir, "src_dirents": list(names), "dst_parent_dir": dst_parent_dir}
        await self._via_repo_token(repo_token, "sync-batch-move-item/", method=METH_POST, json_body=body)

    async def copy_items_via_repo_token(self, repo_token: str, src_parent_dir: str, names: Sequence[str], dst_parent_dir: str) -> None:
        """Copy several files and folders to another folder with a library API token."""
        body = {"src_parent_dir": src_parent_dir, "src_dirents": list(names), "dst_parent_dir": dst_parent_dir}
        await self._via_repo_token(repo_token, "sync-batch-copy-item/", method=METH_POST, json_body=body)

    async def move_dir_via_repo_token(self, repo_token: str, src_parent_dir: str, name: str, dst_parent_dir: str) -> None:
        """Move a folder with a library API token, merging it into a folder of the same name."""
        form = {"src_parent_dir": src_parent_dir, "src_dirent_name": name, "dst_parent_dir": dst_parent_dir}
        await self._via_repo_token(repo_token, "move-dir/", method=METH_POST, data=form)

    async def get_upload_link_via_repo_token(self, repo_token: str, path: str = "/", *, replace: bool = False) -> URL:
        """Return a link to upload files to a folder with a library API token.

        Args:
        ----
            repo_token: The library API token.
            path: The folder to upload to.
            replace: Overwrite existing files instead of adding a numbered copy.

        """
        params = {"path": path, "replace": "1" if replace else "0"}
        return self.file_server_link(await self._via_repo_token(repo_token, "upload-link/", params=params))

    async def get_download_link_via_repo_token(self, repo_token: str, path: str) -> URL:
        """Return a link to download a file with a library API token."""
        return self.file_server_link(await self._via_repo_token(repo_token, "download-link/", params={"path": path}))

    async def search_files_via_repo_token(self, repo_token: str, query: str) -> list[RepoTokenSearchResult]:
        """Search documents (md, sdoc, docx, pdf, pptx) by name with a library API token."""
        result = await self._via_repo_token(repo_token, "search-files/", params={"q": query})
        return [RepoTokenSearchResult.from_dict(item) for item in result["data"]]

    async def get_recently_deleted_files_via_repo_token(self, repo_token: str, since: datetime, *, limit: int = 1000) -> list[RepoTokenDeletedFile]:
        """Return files deleted after a point in time with a library API token, oldest first.

        Args:
        ----
            repo_token: The library API token.
            since: Only files deleted after this time; a naive datetime is taken as local time.
            limit: Maximum number of files to return.

        """
        # The server requires an ISO timestamp with a "+" offset; only the first page works (it slices [start:limit]).
        params = {"since": since.astimezone(UTC).isoformat(), "per_page": limit}
        result = await self._via_repo_token(repo_token, "recently-deleted-files/", params=params)
        return [RepoTokenDeletedFile.from_dict(item) for item in result["files"]]
