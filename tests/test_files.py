"""Tests for the directory and file endpoints."""

# pylint: disable=protected-access,too-many-arguments,too-many-positional-arguments

from typing import TYPE_CHECKING, Any

import pytest
from aiohttp import ClientError
from aiohttp.web import Request, Response
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion
from yarl import URL

from aioseafile import Seafile, SeafileConnectionError, SeafileNotFoundError, SeafileTimeoutError
from aioseafile.endpoints.files import _rechunk
from aioseafile.models.files import DirentType, ZipProgress
from tests import load_fixtures

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

HOST = "localhost:8000"
LIB = "7bdfdaf6-a4ea-4784-9146-87ce91700202"
UPLOAD_PATH = "/seafhttp/upload-api/abc"
UPLOAD_LINK = '"http://127.0.0.1/seafhttp/upload-api/abc"'


def _json(text: str, status: int = 200) -> Response:
    return Response(status=status, headers={"Content-Type": "application/json"}, text=text)


def _fixture(name: str) -> Response:
    return _json(load_fixtures(f"files/{name}.json"))


def _expect(
    response: Response,
    *,
    query: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
    body: Any = None,
) -> Callable[[Request], Awaitable[Response]]:
    """Return a handler that checks the request before answering."""

    async def handler(request: Request) -> Response:
        assert request.headers["Authorization"] == "Token test_token"
        if query is not None:
            assert dict(request.query) == query
        if form is not None:
            assert dict(await request.post()) == form
        if body is not None:
            assert await request.json() == body
        return response

    return handler


async def _collect(stream: AsyncIterator[bytes]) -> bytes:
    return b"".join([chunk async for chunk in stream])


async def _stream(data: bytes, step: int) -> AsyncIterator[bytes]:
    for start in range(0, len(data), step):
        yield data[start : start + step]


@pytest.mark.parametrize(
    ("call", "path", "query", "fixture"),
    [
        pytest.param(
            lambda c: c.get_directory(LIB, "/backups/ha"),
            f"/api/v2.1/repos/{LIB}/dir/",
            {"p": "/backups/ha"},
            "directory",
            id="get_directory",
        ),
        pytest.param(
            lambda c: c.get_directory(LIB, "/a", recursive=True, entry_type=DirentType.DIR),
            f"/api/v2.1/repos/{LIB}/dir/",
            {"p": "/a", "recursive": "1", "t": "d"},
            "directory_recursive",
            id="get_directory_recursive",
        ),
        pytest.param(
            lambda c: c.get_directory(LIB, entry_type=DirentType.FILE),
            f"/api/v2.1/repos/{LIB}/dir/",
            {"p": "/", "t": "f"},
            "directory",
            id="get_directory_files",
        ),
        pytest.param(
            lambda c: c.get_directory_detail(LIB, "/backups"),
            f"/api/v2.1/repos/{LIB}/dir/detail/",
            {"path": "/backups"},
            "directory_detail",
            id="get_directory_detail",
        ),
        pytest.param(
            lambda c: c.get_file_detail(LIB, "/backups/ha/single.tar"),
            f"/api2/repos/{LIB}/file/detail/",
            {"p": "/backups/ha/single.tar"},
            "file_detail",
            id="get_file_detail",
        ),
        pytest.param(
            lambda c: c.get_file_info(LIB, "/backups/ha/single.tar"),
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/backups/ha/single.tar"},
            "file_info",
            id="get_file_info",
        ),
        pytest.param(
            lambda c: c.get_file_history(LIB, "/f.tar"),
            f"/api/v2.1/repos/{LIB}/file/history/",
            {"path": "/f.tar", "limit": "50"},
            "file_history",
            id="get_file_history",
        ),
        pytest.param(
            lambda c: c.get_file_history(LIB, "/f.tar", start_commit="abc", limit=2),
            f"/api/v2.1/repos/{LIB}/file/history/",
            {"path": "/f.tar", "limit": "2", "commit_id": "abc"},
            "file_history",
            id="get_file_history_next_page",
        ),
        pytest.param(lambda c: c.get_starred_items(), "/api/v2.1/starred-items/", {}, "starred_items", id="get_starred_items"),
        pytest.param(
            lambda c: c.get_smart_link(LIB, "/backups", is_dir=True),
            "/api/v2.1/smart-link/",
            {"repo_id": LIB, "path": "/backups", "is_dir": "true"},
            "smart_link",
            id="get_smart_link",
        ),
        pytest.param(
            lambda c: c.get_zip_progress("tok"),
            "/api/v2.1/query-zip-progress/",
            {"token": "tok"},
            "zip_progress",
            id="get_zip_progress",
        ),
        pytest.param(
            lambda c: c.get_copy_move_progress("task"),
            "/api/v2.1/query-copy-move-progress/",
            {"task_id": "task"},
            "copy_move_progress",
            id="get_copy_move_progress",
        ),
    ],
)
async def test_get_endpoints(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    snapshot: SnapshotAssertion,
    call: Callable[[Seafile], Awaitable[Any]],
    path: str,
    query: dict[str, str],
    fixture: str,
) -> None:
    """Test read endpoints send the right query and parse the response."""
    aresponses.add(HOST, path, "GET", _expect(_fixture(fixture), query=query))
    assert await call(seafile_client) == snapshot


@pytest.mark.parametrize(
    ("call", "method", "path", "query", "form", "response"),
    [
        pytest.param(
            lambda c: c.create_directory(LIB, "/backups/ha"),
            "POST",
            f"/api2/repos/{LIB}/dir/",
            {"p": "/backups/ha"},
            {"operation": "mkdir", "create_parents": "true"},
            '"success"',
            id="create_directory",
        ),
        pytest.param(
            lambda c: c.create_directory(LIB, "/backups", create_parents=False),
            "POST",
            f"/api2/repos/{LIB}/dir/",
            {"p": "/backups"},
            {"operation": "mkdir"},
            '"success"',
            id="create_directory_without_parents",
        ),
        pytest.param(
            lambda c: c.rename_directory(LIB, "/y", "y2"),
            "POST",
            f"/api/v2.1/repos/{LIB}/dir/",
            {"p": "/y"},
            {"operation": "rename", "newname": "y2"},
            "dir_info",
            id="rename_directory",
        ),
        pytest.param(
            lambda c: c.revert_directory(LIB, "/y", "c1"),
            "POST",
            f"/api/v2.1/repos/{LIB}/dir/",
            {"p": "/y"},
            {"operation": "revert", "commit_id": "c1"},
            '{"success": true}',
            id="revert_directory",
        ),
        pytest.param(
            lambda c: c.delete_directory(LIB, "/y"),
            "DELETE",
            f"/api/v2.1/repos/{LIB}/dir/",
            {"p": "/y"},
            None,
            '{"success": true}',
            id="delete_directory",
        ),
        pytest.param(
            lambda c: c.create_file(LIB, "/n.txt"),
            "POST",
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/n.txt"},
            {"operation": "create"},
            "file_info",
            id="create_file",
        ),
        pytest.param(
            lambda c: c.rename_file(LIB, "/n.txt", "m.txt"),
            "POST",
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/n.txt"},
            {"operation": "rename", "newname": "m.txt"},
            "file_info",
            id="rename_file",
        ),
        pytest.param(
            lambda c: c.move_file(LIB, "/n.txt", "dst", "/d"),
            "POST",
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/n.txt"},
            {"operation": "move", "dst_repo": "dst", "dst_dir": "/d"},
            "file_info",
            id="move_file",
        ),
        pytest.param(
            lambda c: c.copy_file(LIB, "/n.txt", "dst", "/d"),
            "POST",
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/n.txt"},
            {"operation": "copy", "dst_repo": "dst", "dst_dir": "/d"},
            "file_info",
            id="copy_file",
        ),
        pytest.param(
            lambda c: c.revert_file(LIB, "/n.txt", "c1"),
            "POST",
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/n.txt"},
            {"operation": "revert", "commit_id": "c1"},
            '{"success": true}',
            id="revert_file",
        ),
        pytest.param(
            lambda c: c.delete_file(LIB, "/n.txt"),
            "DELETE",
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/n.txt"},
            None,
            '{"success": true}',
            id="delete_file",
        ),
        pytest.param(
            lambda c: c.lock_file(LIB, "/n.txt", expire=60),
            "PUT",
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/n.txt"},
            {"operation": "lock", "expire": "60"},
            "file_info",
            id="lock_file",
        ),
        pytest.param(
            lambda c: c.unlock_file(LIB, "/n.txt"),
            "PUT",
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/n.txt"},
            {"operation": "unlock"},
            "file_info",
            id="unlock_file",
        ),
        pytest.param(
            lambda c: c.refresh_file_lock(LIB, "/n.txt"),
            "PUT",
            f"/api/v2.1/repos/{LIB}/file/",
            {"p": "/n.txt"},
            {"operation": "refresh-lock", "expire": "0"},
            "file_info",
            id="refresh_file_lock",
        ),
        pytest.param(
            lambda c: c.star_item(LIB, "/backups"),
            "POST",
            "/api/v2.1/starred-items/",
            {},
            {"repo_id": LIB, "path": "/backups"},
            "starred_item",
            id="star_item",
        ),
        pytest.param(
            lambda c: c.unstar_item(LIB, "/backups"),
            "DELETE",
            "/api/v2.1/starred-items/",
            {"repo_id": LIB, "path": "/backups"},
            None,
            '{"success": true}',
            id="unstar_item",
        ),
        pytest.param(
            lambda c: c.cancel_copy_move("task"),
            "DELETE",
            "/api/v2.1/copy-move-task/",
            {},
            {"task_id": "task"},
            '{"success": true}',
            id="cancel_copy_move",
        ),
        pytest.param(
            lambda c: c.move_directory_merge(LIB, "/", "a", "dst", "/d"),
            "POST",
            "/api/v2.1/move-folder-merge/",
            {},
            {"src_repo_id": LIB, "src_parent_dir": "/", "src_dirent_name": "a", "dst_repo_id": "dst", "dst_parent_dir": "/d"},
            '{"success": true}',
            id="move_directory_merge",
        ),
    ],
)
async def test_write_endpoints(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    snapshot: SnapshotAssertion,
    call: Callable[[Seafile], Awaitable[Any]],
    method: str,
    path: str,
    query: dict[str, str],
    form: dict[str, str] | None,
    response: str,
) -> None:
    """Test write endpoints send the right query and form data."""
    reply = _json(response) if response[0] in '{"[' else _fixture(response)
    aresponses.add(HOST, path, method, _expect(reply, query=query, form=form))
    assert await call(seafile_client) == snapshot


@pytest.mark.parametrize(
    ("call", "method", "path", "body", "response", "expected"),
    [
        pytest.param(
            lambda c: c.delete_items(LIB, "/y", ["a", "b"]),
            "DELETE",
            "/api/v2.1/repos/batch-delete-item/",
            {"repo_id": LIB, "parent_dir": "/y", "dirents": ["a", "b"]},
            '{"success": true, "commit_id": "c"}',
            None,
            id="delete_items",
        ),
        pytest.param(
            lambda c: c.copy_items(LIB, "/a", ["f"], "dst", "/d"),
            "POST",
            "/api/v2.1/repos/sync-batch-copy-item/",
            {"src_repo_id": LIB, "src_parent_dir": "/a", "src_dirents": ["f"], "dst_repo_id": "dst", "dst_parent_dir": "/d"},
            '{"success": true}',
            None,
            id="copy_items",
        ),
        pytest.param(
            lambda c: c.move_items(LIB, "/a", ["f"], "dst", "/d"),
            "POST",
            "/api/v2.1/repos/sync-batch-move-item/",
            {"src_repo_id": LIB, "src_parent_dir": "/a", "src_dirents": ["f"], "dst_repo_id": "dst", "dst_parent_dir": "/d"},
            '{"success": true}',
            None,
            id="move_items",
        ),
        pytest.param(
            lambda c: c.copy_items_async(LIB, "/a", ["f"], "dst", "/d"),
            "POST",
            "/api/v2.1/repos/async-batch-copy-item/",
            {"src_repo_id": LIB, "src_parent_dir": "/a", "src_dirents": ["f"], "dst_repo_id": "dst", "dst_parent_dir": "/d"},
            '{"task_id": "t1"}',
            "t1",
            id="copy_items_async",
        ),
        pytest.param(
            lambda c: c.move_items_async(LIB, "/a", ["f"], "dst", "/d"),
            "POST",
            "/api/v2.1/repos/async-batch-move-item/",
            {"src_repo_id": LIB, "src_parent_dir": "/a", "src_dirents": ["f"], "dst_repo_id": "dst", "dst_parent_dir": "/d"},
            '{"task_id": ""}',
            "",
            id="move_items_async",
        ),
    ],
)
async def test_batch_endpoints(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    call: Callable[[Seafile], Awaitable[Any]],
    method: str,
    path: str,
    body: dict[str, Any],
    response: str,
    expected: str | None,
) -> None:
    """Test batch endpoints send a JSON body."""
    aresponses.add(HOST, path, method, _expect(_json(response), body=body))
    assert await call(seafile_client) == expected


@pytest.mark.parametrize(
    ("call", "path", "query", "expected"),
    [
        pytest.param(
            lambda c: c.get_download_link(LIB, "/f.tar"),
            f"/api2/repos/{LIB}/file/",
            {"p": "/f.tar"},
            "http://localhost:8000/seafhttp/files/abc/f.tar",
            id="download_link",
        ),
        pytest.param(
            lambda c: c.get_download_link(LIB, "/f.tar", reuse=True),
            f"/api2/repos/{LIB}/file/",
            {"p": "/f.tar", "reuse": "1"},
            "http://localhost:8000/seafhttp/files/abc/f.tar",
            id="download_link_reuse",
        ),
        pytest.param(
            lambda c: c.get_revision_download_link(LIB, "/f.tar", "c1"),
            f"/api2/repos/{LIB}/file/revision/",
            {"p": "/f.tar", "commit_id": "c1"},
            "http://localhost:8000/seafhttp/files/abc/f.tar",
            id="revision_download_link",
        ),
        pytest.param(
            lambda c: c.get_upload_link(LIB, "/backups"),
            f"/api2/repos/{LIB}/upload-link/",
            {"p": "/backups"},
            "http://localhost:8000/seafhttp/files/abc/f.tar",
            id="upload_link",
        ),
        pytest.param(
            lambda c: c.get_update_link(LIB),
            f"/api2/repos/{LIB}/update-link/",
            {"p": "/"},
            "http://localhost:8000/seafhttp/files/abc/f.tar",
            id="update_link",
        ),
    ],
)
async def test_links(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    call: Callable[[Seafile], Awaitable[URL]],
    path: str,
    query: dict[str, str],
    expected: str,
) -> None:
    """Test file server links are rebased onto the client's URL."""
    aresponses.add(HOST, path, "GET", _expect(_json('"http://127.0.0.1/seafhttp/files/abc/f.tar"'), query=query))
    assert await call(seafile_client) == URL(expected)


@pytest.mark.parametrize(
    ("file_server_url", "link", "expected"),
    [
        pytest.param(None, "http://127.0.0.1/seafhttp/files/a%20b/x?op=1", "https://cloud.example/sub/seafhttp/files/a%20b/x?op=1", id="default"),
        pytest.param("https://files.example:8443/", "http://127.0.0.1/seafhttp/zip/t", "https://files.example:8443/zip/t", id="override"),
        pytest.param(None, "http://127.0.0.1:8082/files/abc/x", "http://127.0.0.1:8082/files/abc/x", id="separate_port"),
    ],
)
async def test_file_server_link(file_server_url: str | None, link: str, expected: str) -> None:
    """Test rebasing links from Seafile's SERVICE_URL."""
    async with Seafile("https://cloud.example/sub", file_server_url=file_server_url) as client:
        assert client.file_server_link(link) == URL(expected)
        assert str(client.get_zip_download_link("t")).endswith("/zip/t")


async def test_get_uploaded_bytes(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test resuming information for chunked uploads."""
    aresponses.add(
        HOST,
        f"/api/v2.1/repos/{LIB}/file-uploaded-bytes/",
        "GET",
        _expect(_json('{"uploadedBytes": 1000}'), query={"parent_dir": "/b", "file_name": "f.tar"}),
    )
    assert await seafile_client.get_uploaded_bytes(LIB, "/b", "f.tar") == 1000


async def test_create_zip_task(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test starting a zip task with several entries."""

    async def handler(request: Request) -> Response:
        assert request.query.getall("dirents") == ["a", "b"]
        assert request.query["parent_dir"] == "/"
        return _json('{"zip_token": "zt"}')

    aresponses.add(HOST, f"/api/v2.1/repos/{LIB}/zip-task/", "GET", handler)
    assert await seafile_client.create_zip_task(LIB, "/", ["a", "b"]) == "zt"


def test_zip_progress_done() -> None:
    """Test the zip progress matches the web interface's completion check."""
    assert ZipProgress(zipped=0, total=0).done
    assert not ZipProgress(zipped=1, total=2).done


def _upload_handler(
    received: list[dict[str, Any]],
    *,
    final: bool = True,
) -> Callable[[Request], Awaitable[Response]]:
    async def handler(request: Request) -> Response:
        assert "Authorization" not in request.headers
        assert request.query["ret-json"] == "1"
        form = await request.post()
        upload = form["file"]
        received.append(
            {
                "content": upload.file.read(),  # type: ignore[union-attr]
                "filename": upload.filename,  # type: ignore[union-attr]
                "form": {key: value for key, value in form.items() if key != "file"},
                "range": request.headers.get("Content-Range"),
                "disposition": request.headers.get("Content-Disposition"),
            }
        )
        return _fixture("uploaded") if final else _json('{"success": true}')

    return handler


async def test_upload_file_bytes(aresponses: ResponsesMockServer, seafile_client: Seafile, snapshot: SnapshotAssertion) -> None:
    """Test uploading bytes in one request through a fresh upload link."""
    received: list[dict[str, Any]] = []
    aresponses.add(HOST, f"/api2/repos/{LIB}/upload-link/", "GET", _expect(_json(UPLOAD_LINK), query={"p": "/backups"}))
    aresponses.add(HOST, UPLOAD_PATH, "POST", _upload_handler(received))
    assert await seafile_client.upload_file(LIB, "/backups", "backup.tar", b"data", replace=True) == snapshot
    assert received == [
        {"content": b"data", "filename": "backup.tar", "form": {"parent_dir": "/backups", "replace": "1"}, "range": None, "disposition": None}
    ]


async def test_upload_stream_single_request(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test a stream without a chunk size is sent in one request."""
    received: list[dict[str, Any]] = []
    aresponses.add(HOST, UPLOAD_PATH, "POST", _upload_handler(received))
    link = URL(f"http://{HOST}{UPLOAD_PATH}")
    await seafile_client.upload_to_link(link, "/", "b.tar", _stream(b"abcdefgh", 3), size=8)
    assert [item["content"] for item in received] == [b"abcdefgh"]
    assert received[0]["form"] == {"parent_dir": "/"}


@pytest.mark.parametrize(
    ("data", "size"),
    [
        pytest.param(b"abcdefghij", None, id="bytes"),
        pytest.param(_stream(b"abcdefghij", 3), 10, id="stream"),
    ],
)
async def test_upload_chunked(
    aresponses: ResponsesMockServer,
    seafile_client: Seafile,
    data: bytes | AsyncIterator[bytes],
    size: int | None,
) -> None:
    """Test chunked uploads send Content-Range requests of the chunk size."""
    received: list[dict[str, Any]] = []
    aresponses.add(HOST, UPLOAD_PATH, "POST", _upload_handler(received, final=False))
    aresponses.add(HOST, UPLOAD_PATH, "POST", _upload_handler(received, final=False))
    aresponses.add(HOST, UPLOAD_PATH, "POST", _upload_handler(received))
    link = URL(f"http://{HOST}{UPLOAD_PATH}")
    result = await seafile_client.upload_to_link(link, "/b", "bäck up.tar", data, size=size, chunk_size=4)
    assert result.name == "backup.tar"
    assert [(item["content"], item["range"]) for item in received] == [
        (b"abcd", "bytes 0-3/10"),
        (b"efgh", "bytes 4-7/10"),
        (b"ij", "bytes 8-9/10"),
    ]
    assert {item["disposition"] for item in received} == {"attachment; filename*=UTF-8''b%C3%A4ck%20up.tar"}


async def test_upload_chunk_retried(aresponses: ResponsesMockServer) -> None:
    """Test a chunk is resent after a transient server error."""
    received: list[dict[str, Any]] = []
    aresponses.add(HOST, UPLOAD_PATH, "POST", _json("{}", status=502))
    aresponses.add(HOST, UPLOAD_PATH, "POST", _upload_handler(received))
    async with Seafile(f"http://{HOST}", "test_token", max_retries=1) as client:
        await client.upload_to_link(URL(f"http://{HOST}{UPLOAD_PATH}"), "/", "f", b"abc", chunk_size=10)
    assert [item["content"] for item in received] == [b"abc"]


async def test_upload_stream_not_retried(aresponses: ResponsesMockServer) -> None:
    """Test a one-shot stream is not resent after a transient server error."""
    aresponses.add(HOST, UPLOAD_PATH, "POST", _json("{}", status=502))
    async with Seafile(f"http://{HOST}", "test_token", max_retries=3) as client:
        with pytest.raises(SeafileConnectionError):
            await client.upload_to_link(URL(f"http://{HOST}{UPLOAD_PATH}"), "/", "f", _stream(b"abc", 1))


async def test_update_file(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test replacing the content of a file, which answers in plain text."""
    received: list[dict[str, Any]] = []

    async def handler(request: Request) -> Response:
        form = await request.post()
        received.append({"target_file": form["target_file"], "content": form["file"].file.read()})  # type: ignore[union-attr]
        return Response(text="ba7fdc65\n", content_type="text/plain")

    aresponses.add(HOST, f"/api2/repos/{LIB}/update-link/", "GET", _expect(_json(UPLOAD_LINK), query={"p": "/backups"}))
    aresponses.add(HOST, UPLOAD_PATH, "POST", handler)
    assert await seafile_client.update_file(LIB, "/backups/f.tar", b"new") == "ba7fdc65"
    assert received == [{"target_file": "/backups/f.tar", "content": b"new"}]


async def test_download_file(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test streaming a file through its download link."""
    content = bytes(range(256)) * 1000
    aresponses.add(HOST, f"/api2/repos/{LIB}/file/", "GET", _expect(_json('"http://127.0.0.1/seafhttp/files/t/f.tar"'), query={"p": "/f.tar"}))
    aresponses.add(HOST, "/seafhttp/files/t/f.tar", "GET", Response(body=content))
    assert await _collect(seafile_client.download_file(LIB, "/f.tar", chunk_size=1000)) == content


async def test_download_not_found(aresponses: ResponsesMockServer, seafile_client: Seafile) -> None:
    """Test an expired download link."""
    aresponses.add(HOST, "/seafhttp/files/t/f.tar", "GET", Response(status=404, text="Bad access token"))
    with pytest.raises(SeafileNotFoundError):
        await _collect(seafile_client.download(URL(f"http://{HOST}/seafhttp/files/t/f.tar")))


@pytest.mark.parametrize(
    ("error", "exception"),
    [
        pytest.param(TimeoutError(), SeafileTimeoutError, id="timeout"),
        pytest.param(ClientError(), SeafileConnectionError, id="connection"),
    ],
)
async def test_download_errors(seafile_client: Seafile, error: Exception, exception: type[Exception], monkeypatch: pytest.MonkeyPatch) -> None:
    """Test errors while opening a download."""

    async def fail(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(seafile_client._get_session(), "get", fail)
    with pytest.raises(exception):
        await _collect(seafile_client.download(URL(f"http://{HOST}/seafhttp/files/t/f")))


@pytest.mark.parametrize(
    ("data", "chunk_size", "expected"),
    [
        pytest.param(b"abcdefg", 3, [b"abc", b"def", b"g"], id="bytes"),
        pytest.param(b"abcdef", 3, [b"abc", b"def"], id="bytes_exact"),
        pytest.param(_stream(b"abcdefg", 2), 3, [b"abc", b"def", b"g"], id="stream"),
        pytest.param(_stream(b"abcdefg", 5), 2, [b"ab", b"cd", b"ef", b"g"], id="stream_large_parts"),
    ],
)
async def test_rechunk(data: bytes | AsyncIterator[bytes], chunk_size: int, expected: list[bytes]) -> None:
    """Test splitting data into upload chunks."""
    assert [chunk async for chunk in _rechunk(data, chunk_size)] == expected
