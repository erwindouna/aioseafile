"""Directory and file endpoints."""

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from aiohttp import ClientTimeout, FormData
from aiohttp.hdrs import METH_DELETE, METH_POST, METH_PUT
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential
from yarl import URL

from aioseafile.client import SeafileClient, _is_retryable
from aioseafile.models.files import (
    CopyMoveProgress,
    DirectoryDetail,
    DirectoryListing,
    DirentInfo,
    DirentType,
    FileDetail,
    FileHistory,
    SmartLink,
    StarredItem,
    UploadedFile,
    ZipProgress,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator

DEFAULT_DOWNLOAD_CHUNK_SIZE = 64 * 1024


async def _rechunk(data: bytes | AsyncIterable[bytes], chunk_size: int) -> AsyncIterator[bytes]:
    """Yield `data` in pieces of exactly `chunk_size` bytes, except the last one."""
    if isinstance(data, bytes):
        for start in range(0, len(data), chunk_size):
            yield data[start : start + chunk_size]
        return
    buffer = bytearray()
    async for part in data:
        buffer += part
        while len(buffer) >= chunk_size:
            yield bytes(buffer[:chunk_size])
            del buffer[:chunk_size]
    if buffer:
        yield bytes(buffer)


def _upload_form(form: dict[str, str], content: bytes | AsyncIterable[bytes], filename: str) -> FormData:
    data = FormData()
    data.add_field("file", content, filename=filename, content_type="application/octet-stream")
    for key, value in form.items():
        data.add_field(key, value)
    return data


class FilesMixin(SeafileClient):
    """Directory and file endpoints."""

    def _transfer_client_timeout(self) -> ClientTimeout:
        return ClientTimeout(total=None, connect=self._request_timeout, sock_read=self._transfer_timeout)

    async def get_directory(
        self,
        library_id: str,
        path: str = "/",
        *,
        recursive: bool = False,
        entry_type: DirentType | None = None,
    ) -> DirectoryListing:
        """Return the entries of a directory.

        Args:
        ----
            library_id: ID of the library.
            path: Path of the directory.
            recursive: Include the entries of all subdirectories.
            entry_type: Only return files or only directories.

        """
        params: dict[str, str] = {"p": path}
        if recursive:
            params["recursive"] = "1"
        if entry_type is not None:
            params["t"] = "f" if entry_type is DirentType.FILE else "d"
        return DirectoryListing.from_dict(await self._request(f"api/v2.1/repos/{library_id}/dir/", params=params))

    async def get_directory_detail(self, library_id: str, path: str) -> DirectoryDetail:
        """Return the details of a directory."""
        return DirectoryDetail.from_dict(await self._request(f"api/v2.1/repos/{library_id}/dir/detail/", params={"path": path}))

    async def create_directory(self, library_id: str, path: str, *, create_parents: bool = True) -> None:
        """Create a directory.

        With `create_parents` (the default), missing parents are created and an
        existing directory is left as is. Without it, Seafile creates a renamed
        copy, for example "backups (1)", when the directory already exists.
        """
        data = {"operation": "mkdir"}
        if create_parents:
            data["create_parents"] = "true"
        await self._request(f"api2/repos/{library_id}/dir/", method=METH_POST, params={"p": path}, data=data)

    async def rename_directory(self, library_id: str, path: str, new_name: str) -> DirentInfo:
        """Rename a directory; Seafile appends a suffix when the new name is taken."""
        return DirentInfo.from_dict(
            await self._request(
                f"api/v2.1/repos/{library_id}/dir/",
                method=METH_POST,
                params={"p": path},
                data={"operation": "rename", "newname": new_name},
            )
        )

    async def revert_directory(self, library_id: str, path: str, commit_id: str) -> None:
        """Restore a directory to its state in an earlier commit."""
        await self._request(
            f"api/v2.1/repos/{library_id}/dir/",
            method=METH_POST,
            params={"p": path},
            data={"operation": "revert", "commit_id": commit_id},
        )

    async def delete_directory(self, library_id: str, path: str) -> None:
        """Delete a directory and its contents."""
        await self._request(f"api/v2.1/repos/{library_id}/dir/", method=METH_DELETE, params={"p": path})

    async def get_file_detail(self, library_id: str, path: str) -> FileDetail:
        """Return the details of a file."""
        return FileDetail.from_dict(await self._request(f"api2/repos/{library_id}/file/detail/", params={"p": path}))

    async def get_file_info(self, library_id: str, path: str) -> DirentInfo:
        """Return a file's lock state and edit/preview capabilities."""
        return DirentInfo.from_dict(await self._request(f"api/v2.1/repos/{library_id}/file/", params={"p": path}))

    async def _file_operation(self, library_id: str, path: str, data: dict[str, str], method: str = METH_POST) -> Any:
        return await self._request(f"api/v2.1/repos/{library_id}/file/", method=method, params={"p": path}, data=data)

    async def create_file(self, library_id: str, path: str) -> DirentInfo:
        """Create an empty file; Seafile appends a suffix when the name is taken."""
        return DirentInfo.from_dict(await self._file_operation(library_id, path, {"operation": "create"}))

    async def rename_file(self, library_id: str, path: str, new_name: str) -> DirentInfo:
        """Rename a file; Seafile appends a suffix when the new name is taken."""
        return DirentInfo.from_dict(await self._file_operation(library_id, path, {"operation": "rename", "newname": new_name}))

    async def move_file(self, library_id: str, path: str, dst_library_id: str, dst_dir: str) -> DirentInfo:
        """Move a file to another directory, possibly in another library."""
        data = {"operation": "move", "dst_repo": dst_library_id, "dst_dir": dst_dir}
        return DirentInfo.from_dict(await self._file_operation(library_id, path, data))

    async def copy_file(self, library_id: str, path: str, dst_library_id: str, dst_dir: str) -> DirentInfo:
        """Copy a file to another directory, possibly in another library."""
        data = {"operation": "copy", "dst_repo": dst_library_id, "dst_dir": dst_dir}
        return DirentInfo.from_dict(await self._file_operation(library_id, path, data))

    async def revert_file(self, library_id: str, path: str, commit_id: str) -> None:
        """Restore a file to its content in an earlier commit."""
        await self._file_operation(library_id, path, {"operation": "revert", "commit_id": commit_id})

    async def delete_file(self, library_id: str, path: str) -> None:
        """Delete a file; deleting a missing file succeeds."""
        await self._request(f"api/v2.1/repos/{library_id}/file/", method=METH_DELETE, params={"p": path})

    async def lock_file(self, library_id: str, path: str, *, expire: int = 0) -> DirentInfo:
        """Lock a file (Pro edition).

        Args:
        ----
            library_id: ID of the library.
            path: Path of the file.
            expire: Lock duration in seconds; 0 locks until unlocked.

        """
        data = {"operation": "lock", "expire": str(expire)}
        return DirentInfo.from_dict(await self._file_operation(library_id, path, data, METH_PUT))

    async def unlock_file(self, library_id: str, path: str) -> DirentInfo:
        """Unlock a file (Pro edition)."""
        return DirentInfo.from_dict(await self._file_operation(library_id, path, {"operation": "unlock"}, METH_PUT))

    async def refresh_file_lock(self, library_id: str, path: str, *, expire: int = 0) -> DirentInfo:
        """Extend the lock on a file (Pro edition)."""
        data = {"operation": "refresh-lock", "expire": str(expire)}
        return DirentInfo.from_dict(await self._file_operation(library_id, path, data, METH_PUT))

    async def get_file_history(self, library_id: str, path: str, *, start_commit: str | None = None, limit: int = 50) -> FileHistory:
        """Return one page of a file's revisions, newest first.

        Args:
        ----
            library_id: ID of the library.
            path: Path of the file.
            start_commit: `next_start_commit` of the previous page.
            limit: Maximum number of revisions to return.

        """
        params = {"path": path, "limit": str(limit)}
        if start_commit is not None:
            params["commit_id"] = start_commit
        return FileHistory.from_dict(await self._request(f"api/v2.1/repos/{library_id}/file/history/", params=params))

    async def get_download_link(self, library_id: str, path: str, *, reuse: bool = False) -> URL:
        """Return a link to download a file.

        Args:
        ----
            library_id: ID of the library.
            path: Path of the file.
            reuse: Allow the link to be used more than once (within one hour).

        """
        params = {"p": path}
        if reuse:
            params["reuse"] = "1"
        link: str = await self._request(f"api2/repos/{library_id}/file/", params=params)
        return self.file_server_link(link)

    async def get_revision_download_link(self, library_id: str, path: str, commit_id: str) -> URL:
        """Return a link to download a file as it was in an earlier commit."""
        link: str = await self._request(f"api2/repos/{library_id}/file/revision/", params={"p": path, "commit_id": commit_id})
        return self.file_server_link(link)

    async def download(self, link: URL, *, chunk_size: int = DEFAULT_DOWNLOAD_CHUNK_SIZE) -> AsyncIterator[bytes]:
        """Stream the content behind a download link."""
        async with self._stream(link) as response:
            async for chunk in response.content.iter_chunked(chunk_size):
                yield chunk

    async def download_file(self, library_id: str, path: str, *, chunk_size: int = DEFAULT_DOWNLOAD_CHUNK_SIZE) -> AsyncIterator[bytes]:
        """Stream the content of a file."""
        link = await self.get_download_link(library_id, path)
        async for chunk in self.download(link, chunk_size=chunk_size):
            yield chunk

    async def get_upload_link(self, library_id: str, parent_dir: str = "/") -> URL:
        """Return a link to upload files into `parent_dir`; the link only accepts that directory."""
        link: str = await self._request(f"api2/repos/{library_id}/upload-link/", params={"p": parent_dir})
        return self.file_server_link(link)

    async def get_update_link(self, library_id: str, parent_dir: str = "/") -> URL:
        """Return a link to replace the content of existing files."""
        link: str = await self._request(f"api2/repos/{library_id}/update-link/", params={"p": parent_dir})
        return self.file_server_link(link)

    async def get_uploaded_bytes(self, library_id: str, parent_dir: str, filename: str) -> int:
        """Return how many bytes of an interrupted chunked upload the server already has."""
        result = await self._request(f"api/v2.1/repos/{library_id}/file-uploaded-bytes/", params={"parent_dir": parent_dir, "file_name": filename})
        return int(result["uploadedBytes"])

    async def _post_upload(  # pylint: disable=too-many-arguments
        self,
        link: URL,
        form: dict[str, str],
        content: bytes,
        filename: str,
        headers: dict[str, str] | None = None,
        *,
        text: bool = False,
    ) -> Any:
        """Post one buffered multipart upload, retrying transient errors with a fresh form."""
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(self._max_retries + 1),
            reraise=True,
        ):
            with attempt:
                return await self._request(
                    link,
                    method=METH_POST,
                    data=_upload_form(form, content, filename),
                    headers=headers,
                    authenticated=False,
                    client_timeout=self._transfer_client_timeout(),
                    retry=False,
                    text=text,
                )
        raise AssertionError  # pragma: no cover

    async def upload_file(  # pylint: disable=too-many-arguments
        self,
        library_id: str,
        parent_dir: str,
        filename: str,
        data: bytes | AsyncIterable[bytes],
        *,
        size: int | None = None,
        replace: bool = False,
        chunk_size: int | None = None,
    ) -> UploadedFile:
        """Upload a file into a directory of a library.

        Args:
        ----
            library_id: ID of the library.
            parent_dir: Existing directory to upload into.
            filename: Name of the file.
            data: File content, as bytes or a stream of bytes.
            size: Total size in bytes; required for chunked uploads of a stream.
            replace: Overwrite an existing file instead of storing a renamed copy.
            chunk_size: Upload in requests of at most this many bytes, using
                Content-Range. Use this for large files, or when a reverse proxy
                limits the request body size. Chunks are buffered in memory and
                each one is retried on transient errors.

        """
        link = await self.get_upload_link(library_id, parent_dir)
        return await self.upload_to_link(link, parent_dir, filename, data, size=size, replace=replace, chunk_size=chunk_size)

    async def upload_to_link(  # pylint: disable=too-many-arguments
        self,
        link: URL,
        parent_dir: str,
        filename: str,
        data: bytes | AsyncIterable[bytes],
        *,
        size: int | None = None,
        replace: bool = False,
        chunk_size: int | None = None,
    ) -> UploadedFile:
        """Upload a file to an upload link, for example one from a library API token.

        See `upload_file` for the arguments.
        """
        link = link.update_query({"ret-json": "1"})
        form = {"parent_dir": parent_dir}
        if replace:
            form["replace"] = "1"
        if isinstance(data, bytes):
            size = len(data)

        if chunk_size is None or size is None or size <= chunk_size:
            if isinstance(data, bytes):
                result = await self._post_upload(link, form, data, filename)
            else:
                result = await self._request(
                    link,
                    method=METH_POST,
                    data=_upload_form(form, data, filename),
                    authenticated=False,
                    client_timeout=self._transfer_client_timeout(),
                    retry=False,
                )
            return UploadedFile.from_dict(result[0])

        start = 0
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
        async for chunk in _rechunk(data, chunk_size):
            end = start + len(chunk) - 1
            result = await self._post_upload(link, form, chunk, filename, headers | {"Content-Range": f"bytes {start}-{end}/{size}"})
            start = end + 1
        return UploadedFile.from_dict(result[0])

    async def update_file(self, library_id: str, path: str, data: bytes) -> str:
        """Replace the content of an existing file and return the new file ID."""
        parent_dir, filename = path.rsplit("/", 1)
        link = await self.get_update_link(library_id, parent_dir or "/")
        result: str = await self._post_upload(link, {"target_file": path}, data, filename, text=True)
        return result.strip()

    async def delete_items(self, library_id: str, parent_dir: str, names: list[str]) -> None:
        """Delete several files and directories in one directory."""
        await self._request(
            "api/v2.1/repos/batch-delete-item/",
            method=METH_DELETE,
            json_body={"repo_id": library_id, "parent_dir": parent_dir, "dirents": names},
        )

    async def _batch_copy_move(self, operation: str, src: tuple[str, str], names: list[str], dst: tuple[str, str]) -> Any:
        return await self._request(
            f"api/v2.1/repos/{operation}-item/",
            method=METH_POST,
            json_body={
                "src_repo_id": src[0],
                "src_parent_dir": src[1],
                "src_dirents": names,
                "dst_repo_id": dst[0],
                "dst_parent_dir": dst[1],
            },
        )

    async def copy_items(self, library_id: str, parent_dir: str, names: list[str], dst_library_id: str, dst_dir: str) -> None:
        """Copy files and directories and wait until done."""
        await self._batch_copy_move("sync-batch-copy", (library_id, parent_dir), names, (dst_library_id, dst_dir))

    async def move_items(self, library_id: str, parent_dir: str, names: list[str], dst_library_id: str, dst_dir: str) -> None:
        """Move files and directories and wait until done."""
        await self._batch_copy_move("sync-batch-move", (library_id, parent_dir), names, (dst_library_id, dst_dir))

    async def copy_items_async(self, library_id: str, parent_dir: str, names: list[str], dst_library_id: str, dst_dir: str) -> str:
        """Start copying files and directories; returns a task ID, empty when the copy already finished."""
        result = await self._batch_copy_move("async-batch-copy", (library_id, parent_dir), names, (dst_library_id, dst_dir))
        return str(result["task_id"])

    async def move_items_async(self, library_id: str, parent_dir: str, names: list[str], dst_library_id: str, dst_dir: str) -> str:
        """Start moving files and directories; returns a task ID, empty when the move already finished."""
        result = await self._batch_copy_move("async-batch-move", (library_id, parent_dir), names, (dst_library_id, dst_dir))
        return str(result["task_id"])

    async def get_copy_move_progress(self, task_id: str) -> CopyMoveProgress:
        """Return the progress of an asynchronous copy or move."""
        return CopyMoveProgress.from_dict(await self._request("api/v2.1/query-copy-move-progress/", params={"task_id": task_id}))

    async def cancel_copy_move(self, task_id: str) -> None:
        """Cancel an asynchronous copy or move."""
        await self._request("api/v2.1/copy-move-task/", method=METH_DELETE, data={"task_id": task_id})

    async def move_directory_merge(self, library_id: str, parent_dir: str, name: str, dst_library_id: str, dst_dir: str) -> None:
        """Move a directory and merge it into an existing directory with the same name."""
        await self._request(
            "api/v2.1/move-folder-merge/",
            method=METH_POST,
            data={
                "src_repo_id": library_id,
                "src_parent_dir": parent_dir,
                "src_dirent_name": name,
                "dst_repo_id": dst_library_id,
                "dst_parent_dir": dst_dir,
            },
        )

    async def create_zip_task(self, library_id: str, parent_dir: str, names: list[str]) -> str:
        """Start zipping files and directories for download; returns the zip token."""
        result = await self._request(f"api/v2.1/repos/{library_id}/zip-task/", params={"parent_dir": parent_dir, "dirents": names})
        return str(result["zip_token"])

    async def get_zip_progress(self, zip_token: str) -> ZipProgress:
        """Return the progress of a zip task.

        Only the C file server prepares archives in advance; the Go file server
        (the default since Seafile 11) streams the archive on download and
        answers this with `SeafileNotFoundError`.
        """
        return ZipProgress.from_dict(await self._request("api/v2.1/query-zip-progress/", params={"token": zip_token}))

    def get_zip_download_link(self, zip_token: str) -> URL:
        """Return the link to download a finished zip task."""
        return self._file_server_url.join(URL(f"zip/{zip_token}"))

    async def get_smart_link(self, library_id: str, path: str, *, is_dir: bool = False) -> SmartLink:
        """Return a permanent link to a file or directory."""
        params = {"repo_id": library_id, "path": path, "is_dir": "true" if is_dir else "false"}
        return SmartLink.from_dict(await self._request("api/v2.1/smart-link/", params=params))

    async def get_starred_items(self) -> list[StarredItem]:
        """Return the starred libraries, directories and files."""
        result = await self._request("api/v2.1/starred-items/")
        return [StarredItem.from_dict(item) for item in result["starred_item_list"]]

    async def star_item(self, library_id: str, path: str = "/") -> StarredItem:
        """Star a library (path '/'), directory or file."""
        return StarredItem.from_dict(await self._request("api/v2.1/starred-items/", method=METH_POST, data={"repo_id": library_id, "path": path}))

    async def unstar_item(self, library_id: str, path: str = "/") -> None:
        """Unstar a library, directory or file."""
        await self._request("api/v2.1/starred-items/", method=METH_DELETE, params={"repo_id": library_id, "path": path})
