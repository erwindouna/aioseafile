<!-- PROJECT SHIELDS -->

[![GitHub Release][releases-shield]][releases]
[![Python Versions][python-versions-shield]][pypi]
![Project Stage][project-stage-shield]
![Project Maintenance][maintenance-shield]
[![License][license-shield]](LICENSE)

[![GitHub Activity][commits-shield]][commits-url]
[![PyPi Downloads][downloads-shield]][downloads-url]
[![GitHub Last Commit][last-commit-shield]][commits-url]
[![Open in Dev Containers][devcontainer-shield]][devcontainer]

[![Build Status][build-shield]][build-url]
[![Typing Status][typing-shield]][typing-url]
[![Code Coverage][codecov-shield]][codecov-url]

Asynchronous Python client for Python Seafile.

## About

An asynchronous Python client for the [Seafile](https://www.seafile.com/) Web API, built for the Home Assistant Seafile integration. It covers the documented Seafile Web API (checked against Seafile 14), plus the system admin API:

| Area | Examples |
| --- | --- |
| Account | server info, account and quota, profile, avatar, devices, activities, notifications, guest invitations |
| Libraries | create, rename, transfer, delete, encryption passwords, history and snapshots, trash, deleted libraries, library API tokens and all `via-repo-token` endpoints |
| Files | directories, file operations, streaming upload (optionally in chunks) and download, file history, batch copy/move/delete, zip download, smart links, starred items |
| Sharing | share links, upload links, sharing with users and groups, folder permissions |
| Groups | groups, members, group libraries; departments and organizations (Pro / multi-tenancy) |
| Admin | system info, statistics, users, libraries, trash, devices, links, groups, logs, notifications |
| Extras | search, tags, file comments, wikis, metadata (Seafile 13+) |

Endpoints that only exist in the Professional edition, or that need a server setting, raise `SeafilePermissionError` or `SeafileNotFoundError` on servers without them.

## Installation

```bash
pip install aioseafile
```

### Example

```python
import asyncio

from aioseafile import Seafile


async def main() -> None:
    """Run the example."""
    async with Seafile(api_url="https://cloud.example.com") as seafile:
        await seafile.get_auth_token("me@example.com", "password")
        account = await seafile.get_account_info()
        print(f"{account.usage} of {account.quota_total or 'unlimited'} bytes used")
        for library in await seafile.get_libraries():
            print(library.name, library.size)


if __name__ == "__main__":
    asyncio.run(main())
```

Pass `token=` instead of calling `get_auth_token` to reuse a stored token. Admin methods (`get_admin_*`, `create_admin_*`, ...) raise `SeafilePermissionError` for non-admin accounts.

### Uploading and downloading

Uploads and downloads are streamed, so large files never have to fit in memory. Use `chunk_size` to upload in several requests, for example behind a reverse proxy that limits the request size; each chunk is retried on transient errors. Pass `on_progress` to be told how many bytes were uploaded so far.

```python
async def backup(seafile: Seafile, library_id: str, stream: AsyncIterator[bytes], size: int) -> None:
    """Upload a backup and read it back."""
    await seafile.create_directory(library_id, "/backups")
    await seafile.upload_file(library_id, "/backups", "backup.tar", stream, size=size, chunk_size=50 * 1024 * 1024)
    async for chunk in seafile.download_file(library_id, "/backups/backup.tar"):
        ...
```

Seafile builds upload and download links from its `SERVICE_URL` setting, which often differs from the address the client uses. The client rebases these links onto `api_url`, or onto `file_server_url` when the file server runs elsewhere.

## Contributing

This is an active open-source project. We are always open to people who want to
use the code or contribute to it.

We've set up a separate document for our
[contribution guidelines](CONTRIBUTING.md).

Thank you for being involved! :heart_eyes:

## Setting up development environment

The simplest way to begin is by utilizing the [Dev Container][devcontainer]
feature of Visual Studio Code or by opening a CodeSpace directly on GitHub.
By clicking the button below you immediately start a Dev Container in Visual Studio Code.

[![Open in Dev Containers][devcontainer-shield]][devcontainer]

This Python project relies on [UV][poetry] as its dependency manager,
providing comprehensive management and control over project dependencies.

### Installation

Install all packages, including all development requirements:

```bash
uv sync --all-groups && prek install
```

_UV creates by default an virtual environment where it installs all necessary pip packages_.

### Pre-commit

This repository uses the [pre-commit][pre-commit] framework, all changes
are linted and tested with each commit. To setup the pre-commit check, run:

```bash
uv run prek install
```

And to run all checks and tests manually, use the following command:

```bash
uv run prek run --all-files
```

### Testing

It uses [pytest](https://docs.pytest.org/en/stable/) as the test framework. To run the tests:

```bash
uv run pytest
```

To update the [syrupy](https://github.com/tophat/syrupy) snapshot tests:

```bash
uv run pytest --snapshot-update
```

## License

MIT License

Copyright (c) 2026 Erwin Douna

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

<!-- LINKS FROM PLATFORM -->

<!-- MARKDOWN LINKS & IMAGES -->

[build-shield]: https://github.com/erwindouna/aioseafile/actions/workflows/tests.yaml/badge.svg
[build-url]: https://github.com/erwindouna/aioseafile/actions/workflows/tests.yaml
[codecov-shield]: https://codecov.io/gh/erwindouna/aioseafile/branch/main/graph/badge.svg?token=TOKEN
[codecov-url]: https://codecov.io/gh/erwindouna/aioseafile
[commits-shield]: https://img.shields.io/github/commit-activity/y/erwindouna/aioseafile.svg
[commits-url]: https://github.com/erwindouna/aioseafile/commits/main
[devcontainer-shield]: https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode
[devcontainer]: https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/erwindouna/aioseafile
[downloads-shield]: https://img.shields.io/pypi/dm/aioseafile
[downloads-url]: https://pypistats.org/packages/aioseafile
[last-commit-shield]: https://img.shields.io/github/last-commit/erwindouna/aioseafile.svg
[license-shield]: https://img.shields.io/github/license/erwindouna/aioseafile.svg
[project-stage-shield]: https://img.shields.io/badge/project%20stage-experimental-yellow.svg
[maintenance-shield]: https://img.shields.io/maintenance/yes/2026.svg
[pypi]: https://pypi.org/project/aioseafile/
[python-versions-shield]: https://img.shields.io/pypi/pyversions/aioseafile
[releases-shield]: https://img.shields.io/github/release/erwindouna/aioseafile.svg
[releases]: https://github.com/erwindouna/aioseafile/releases
[typing-shield]: https://github.com/erwindouna/aioseafile/actions/workflows/typing.yaml/badge.svg
[typing-url]: https://github.com/erwindouna/aioseafile/actions/workflows/typing.yaml
[uv]: https://docs.astral.sh/uv/
[pre-commit]: https://pre-commit.com
