"""Tags, metadata, wiki, comments, search and other Seafile 13+/Pro endpoints."""

import json
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from aiohttp.hdrs import METH_DELETE, METH_POST, METH_PUT

from aioseafile.client import SeafileClient
from aioseafile.models.extras import (
    FileComment,
    FileCommentReply,
    FileTag,
    LibrarySearchItem,
    MetadataColumn,
    MetadataNavigationItem,
    MetadataQueryResult,
    MetadataStatus,
    MetadataTag,
    MetadataTaggedFile,
    MetadataTagLinkColumn,
    MetadataView,
    MetadataViews,
    RepoTag,
    SearchResult,
    TaggedFile,
    Wiki,
    WikiDetails,
    WikiList,
    WikiPageContent,
    WikiPageCreated,
    WikiPublishInfo,
    WikiTrashItem,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime


class SearchScope(StrEnum):
    """Libraries searched by the full text search."""

    ALL = "all"
    MINE = "mine"
    SHARED = "shared"
    GROUP = "group"
    PUBLIC = "public"


class SearchObjectType(StrEnum):
    """Restrict the full text search to files or folders."""

    FILE = "file"
    DIR = "dir"


class WikiPagePosition(StrEnum):
    """Where a new wiki page goes relative to an existing page."""

    ABOVE = "above"
    BELOW = "below"
    INNER = "inner"


class ExtrasMixin(SeafileClient):  # pylint: disable=too-many-public-methods
    """Tags, metadata, wiki, comments, search and other Seafile 13+/Pro endpoints."""

    async def search(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        query: str,
        *,
        library_id: str | None = None,
        path: str | None = None,
        scope: SearchScope = SearchScope.ALL,
        object_type: SearchObjectType | None = None,
        file_types: Sequence[str] | None = None,
        extensions: Sequence[str] | None = None,
        filename_only: bool = False,
        modified_after: datetime | None = None,
        modified_before: datetime | None = None,
        size_min: int | None = None,
        size_max: int | None = None,
        with_permission: bool = False,
        page: int = 1,
        per_page: int = 10,
    ) -> SearchResult:
        """Search file names and contents across libraries; requires Seafile Pro with search enabled.

        Args:
        ----
            query: Search keyword.
            library_id: Only search this library.
            path: Only search this folder; requires `library_id`.
            scope: Which libraries to search when `library_id` is not given.
            object_type: Only return files or only folders.
            file_types: Seafile file type groups, such as 'Image', 'Video' or 'Document'.
            extensions: File extensions, such as 'pdf'.
            filename_only: Match file names only, not contents.
            modified_after: Only return items modified at or after this time.
            modified_before: Only return items modified at or before this time.
            size_min: Minimum size in bytes.
            size_max: Maximum size in bytes.
            with_permission: Include the user's permission on each result.
            page: Page number, starting at 1.
            per_page: Results per page.

        """
        params: dict[str, Any] = {
            "q": query,
            "search_repo": library_id or scope,
            "page": page,
            "per_page": per_page,
        }
        optional: dict[str, Any] = {
            "search_path": path,
            "obj_type": object_type,
            "time_from": int(modified_after.timestamp()) if modified_after else None,
            "time_to": int(modified_before.timestamp()) if modified_before else None,
            "size_from": size_min,
            "size_to": size_max,
        }
        params |= {key: value for key, value in optional.items() if value is not None}
        if file_types or extensions:
            params["search_ftypes"] = "custom"
            if file_types:
                params["ftype"] = list(file_types)
            if extensions:
                params["input_fexts"] = ",".join(extensions)
        if filename_only:
            params["search_filename_only"] = "true"
        if with_permission:
            params["with_permission"] = "true"
        return SearchResult.from_dict(await self._request("api2/search/", params=params))

    async def search_library(self, library_id: str, query: str) -> list[LibrarySearchItem]:
        """Search files and folders by name in one library; works on every edition."""
        result = await self._request("api/v2.1/search-file/", params={"repo_id": library_id, "q": query})
        return [LibrarySearchItem.from_dict(item) for item in result["data"]]

    async def get_repo_tags(self, library_id: str, *, include_file_count: bool = True) -> list[RepoTag]:
        """Return the library tags of a library (the tag system from before metadata tags)."""
        result = await self._request(f"api/v2.1/repos/{library_id}/repo-tags/", params={"include_file_count": str(include_file_count).lower()})
        return [RepoTag.from_dict(item) for item in result["repo_tags"]]

    async def create_repo_tag(self, library_id: str, name: str, color: str) -> RepoTag:
        """Create a library tag.

        Args:
        ----
            library_id: ID of the library.
            name: Tag name; must be unique in the library.
            color: Tag color, for example '#FF0000'.

        """
        result = await self._request(f"api/v2.1/repos/{library_id}/repo-tags/", method=METH_POST, data={"name": name, "color": color})
        return RepoTag.from_dict(result["repo_tag"])

    async def create_repo_tags(self, library_id: str, tags: Mapping[str, str]) -> list[RepoTag]:
        """Create several library tags at once; `tags` maps names to colors. Existing names are not checked."""
        body = {"tags": [{"name": name, "color": color} for name, color in tags.items()]}
        result = await self._request(f"api/v2.1/repos/{library_id}/repo-tags/", method=METH_PUT, json_body=body)
        return [RepoTag.from_dict(item) for item in result["repo_tags"]]

    async def update_repo_tag(self, library_id: str, repo_tag_id: int, name: str, color: str) -> RepoTag:
        """Rename or recolor a library tag; both values are required."""
        result = await self._request(f"api/v2.1/repos/{library_id}/repo-tags/{repo_tag_id}/", method=METH_PUT, data={"name": name, "color": color})
        return RepoTag.from_dict(result["repo_tag"])

    async def delete_repo_tag(self, library_id: str, repo_tag_id: int) -> None:
        """Delete a library tag."""
        await self._request(f"api/v2.1/repos/{library_id}/repo-tags/{repo_tag_id}/", method=METH_DELETE)

    async def get_file_tags(self, library_id: str, path: str) -> list[FileTag]:
        """Return the library tags attached to a file."""
        result = await self._request(f"api/v2.1/repos/{library_id}/file-tags/", params={"file_path": path})
        return [FileTag.from_dict(item) for item in result["file_tags"]]

    async def add_file_tag(self, library_id: str, path: str, repo_tag_id: int) -> FileTag:
        """Attach a library tag to a file."""
        result = await self._request(
            f"api/v2.1/repos/{library_id}/file-tags/", method=METH_POST, data={"file_path": path, "repo_tag_id": str(repo_tag_id)}
        )
        return FileTag.from_dict(result["file_tag"])

    async def delete_file_tag(self, library_id: str, file_tag_id: int) -> None:
        """Remove a library tag from a file, by the ID of the file tag."""
        await self._request(f"api/v2.1/repos/{library_id}/file-tags/{file_tag_id}/", method=METH_DELETE)

    async def get_tagged_files(self, library_id: str, repo_tag_id: int) -> list[TaggedFile]:
        """Return the files carrying a library tag."""
        result = await self._request(f"api/v2.1/repos/{library_id}/tagged-files/{repo_tag_id}/")
        return [TaggedFile.from_dict(item) for item in result["tagged_files"]]

    async def get_file_comments(self, library_id: str, file_uuid: str, *, resolved: bool | None = None, per_page: int = 100) -> list[FileComment]:
        """Return all comments on a SeaDoc file or wiki page.

        Args:
        ----
            library_id: ID of the library (or wiki).
            file_uuid: UUID of the document, for example `WikiPage.doc_uuid`.
            resolved: Only return resolved (True) or open (False) comments.
            per_page: Comments fetched per request.

        """
        params: dict[str, Any] = {"per_page": per_page}
        if resolved is not None:
            params["resolved"] = str(resolved).lower()
        comments: list[FileComment] = []
        page = 1
        while True:
            result = await self._request(f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/", params=params | {"page": page})
            comments.extend(FileComment.from_dict(item) for item in result["comments"])
            # total_count ignores the resolved filter, so stop on a short page.
            if len(result["comments"]) < per_page:
                return comments
            page += 1

    async def get_file_comment(self, library_id: str, file_uuid: str, comment_id: int) -> FileComment:
        """Return one file comment, without its replies."""
        return FileComment.from_dict(await self._request(f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/{comment_id}/"))

    async def create_file_comment(self, library_id: str, file_uuid: str, comment: str, *, detail: str | None = None) -> FileComment:
        """Add a comment to a SeaDoc file or wiki page.

        Args:
        ----
            library_id: ID of the library (or wiki).
            file_uuid: UUID of the document.
            comment: Comment text.
            detail: Free-form detail string; SeaDoc stores the commented element here as JSON.

        """
        data = {"comment": comment}
        if detail is not None:
            data["detail"] = detail
        return FileComment.from_dict(await self._request(f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/", method=METH_POST, data=data))

    async def update_file_comment(  # pylint: disable=too-many-arguments
        self,
        library_id: str,
        file_uuid: str,
        comment_id: int,
        *,
        comment: str | None = None,
        detail: str | None = None,
        resolved: bool | None = None,
    ) -> FileComment:
        """Edit a file comment (author only) or mark it resolved (author or library admin)."""
        data: dict[str, str] = {}
        if comment is not None:
            data["comment"] = comment
        if detail is not None:
            data["detail"] = detail
        if resolved is not None:
            data["resolved"] = str(resolved).lower()
        result = await self._request(f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/{comment_id}/", method=METH_PUT, data=data)
        return FileComment.from_dict(result)

    async def delete_file_comment(self, library_id: str, file_uuid: str, comment_id: int) -> None:
        """Delete a file comment and its replies."""
        await self._request(f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/{comment_id}/", method=METH_DELETE)

    async def get_file_comment_replies(self, library_id: str, file_uuid: str, comment_id: int, *, per_page: int = 100) -> list[FileCommentReply]:
        """Return all replies to a file comment."""
        replies: list[FileCommentReply] = []
        page = 1
        while True:
            result = await self._request(
                f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/{comment_id}/replies/", params={"page": page, "per_page": per_page}
            )
            replies.extend(FileCommentReply.from_dict(item) for item in result["replies"])
            if page * per_page >= result["total_count"]:
                return replies
            page += 1

    async def get_file_comment_reply(self, library_id: str, file_uuid: str, comment_id: int, reply_id: int) -> FileCommentReply:
        """Return one reply to a file comment."""
        result = await self._request(f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/{comment_id}/replies/{reply_id}/")
        return FileCommentReply.from_dict(result)

    async def create_file_comment_reply(
        self, library_id: str, file_uuid: str, comment_id: int, reply: str, *, reply_type: str = "reply"
    ) -> FileCommentReply:
        """Reply to a file comment.

        Args:
        ----
            library_id: ID of the library (or wiki).
            file_uuid: UUID of the document.
            comment_id: ID of the comment.
            reply: Reply text.
            reply_type: Reply type; SeaDoc uses 'reply' and 'comment' (a resolve note).

        """
        result = await self._request(
            f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/{comment_id}/replies/",
            method=METH_POST,
            data={"reply": reply, "type": reply_type},
        )
        return FileCommentReply.from_dict(result)

    async def update_file_comment_reply(self, library_id: str, file_uuid: str, comment_id: int, reply_id: int, reply: str) -> FileCommentReply:
        """Edit a reply to a file comment."""
        result = await self._request(
            f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/{comment_id}/replies/{reply_id}/", method=METH_PUT, data={"reply": reply}
        )
        return FileCommentReply.from_dict(result)

    async def delete_file_comment_reply(self, library_id: str, file_uuid: str, comment_id: int, reply_id: int) -> None:
        """Delete a reply to a file comment."""
        await self._request(f"api/v2.1/repos/{library_id}/file/{file_uuid}/comments/{comment_id}/replies/{reply_id}/", method=METH_DELETE)

    async def get_wikis(self) -> WikiList:
        """Return the user's own, shared and group wikis."""
        return WikiList.from_dict(await self._request("api/v2.1/wikis2/"))

    async def create_wiki(self, name: str, *, group_id: int | None = None, color: str | None = None, icon: str | None = None) -> Wiki:
        """Create a wiki.

        Args:
        ----
            name: Wiki name.
            group_id: Create a group-owned wiki in this group (group admins only).
            color: Wiki color.
            icon: Wiki icon name.

        """
        data = {"name": name, "owner": "me" if group_id is None else str(group_id)}
        if color is not None:
            data["color"] = color
        if icon is not None:
            data["icon"] = icon
        return Wiki.from_dict(await self._request("api/v2.1/wikis2/", method=METH_POST, data=data))

    async def update_wiki(self, wiki_id: str, *, name: str | None = None, color: str | None = None, icon: str | None = None) -> None:
        """Rename a wiki or change its color or icon."""
        data: dict[str, str] = {}
        if name is not None:
            data["wiki_name"] = name
        if color is not None:
            data["color"] = color
        if icon is not None:
            data["icon"] = icon
        await self._request(f"api/v2.1/wiki2/{wiki_id}/", method=METH_PUT, data=data)

    async def delete_wiki(self, wiki_id: str) -> None:
        """Delete a wiki and its library."""
        await self._request(f"api/v2.1/wiki2/{wiki_id}/", method=METH_DELETE)

    async def convert_wiki(self, old_wiki_id: int, name: str, *, group_id: int | None = None) -> str:
        """Convert an old-style wiki into a new wiki; returns the ID of the background task."""
        data = {"old_wiki_id": str(old_wiki_id), "name": name, "owner": "me" if group_id is None else str(group_id)}
        result = await self._request("api/v2.1/convert-wiki/", method=METH_POST, data=data)
        return str(result["task_id"])

    async def get_wiki_config(self, wiki_id: str) -> WikiDetails:
        """Return a wiki with its page tree."""
        result = await self._request(f"api/v2.1/wiki2/{wiki_id}/config/")
        return WikiDetails.from_dict(result["wiki"])

    async def update_wiki_config(self, wiki_id: str, config: Mapping[str, Any]) -> None:
        """Replace the page tree of a wiki (the `navigation` and `pages` of `WikiConfig`, in the raw JSON format)."""
        await self._request(f"api/v2.1/wiki2/{wiki_id}/config/", method=METH_PUT, data={"wiki_config": json.dumps(config)})

    async def create_wiki_page(
        self, wiki_id: str, name: str, *, relative_to: str | None = None, position: WikiPagePosition | None = None
    ) -> WikiPageCreated:
        """Create a wiki page.

        Args:
        ----
            wiki_id: ID of the wiki.
            name: Page name; a suffix is added when a sibling has the same name.
            relative_to: ID of an existing page to place the new page next to or under.
            position: Position relative to `relative_to`; the page is appended at the top level when omitted.

        """
        data = {"page_name": name}
        if relative_to is not None:
            data["current_id"] = relative_to
        if position is not None:
            data["insert_position"] = position
        result = await self._request(f"api/v2.1/wiki2/{wiki_id}/pages/", method=METH_POST, data=data)
        return WikiPageCreated.from_dict(result["file_info"])

    async def get_wiki_page(self, wiki_id: str, page_id: str) -> WikiPageContent:
        """Return the SeaDoc access details of a wiki page."""
        return WikiPageContent.from_dict(await self._request(f"api/v2.1/wiki2/{wiki_id}/page/{page_id}/"))

    async def update_wiki_page(
        self, wiki_id: str, page_id: str, *, name: str | None = None, icon: str | None = None, cover: str | None = None
    ) -> None:
        """Rename a wiki page or change its icon or cover; an empty icon or cover removes it."""
        data: dict[str, str] = {}
        if name is not None:
            data["page_name"] = name
        if icon is not None:
            data["page_icon"] = icon
        if cover is not None:
            data["page_cover"] = cover
        await self._request(f"api/v2.1/wiki2/{wiki_id}/page/{page_id}/config/", method=METH_PUT, data=data)

    async def delete_wiki_page(self, wiki_id: str, page_id: str) -> None:
        """Move a wiki page and its subpages to the wiki trash."""
        await self._request(f"api/v2.1/wiki2/{wiki_id}/page/{page_id}/", method=METH_DELETE)

    async def get_wiki_trash(self, wiki_id: str, *, per_page: int = 100) -> list[WikiTrashItem]:
        """Return the deleted pages of a wiki."""
        items: list[WikiTrashItem] = []
        page = 1
        while True:
            result = await self._request(f"api/v2.1/wiki2/{wiki_id}/trash/", params={"page": page, "per_page": per_page})
            items.extend(WikiTrashItem.from_dict(item) for item in result["items"])
            if page * per_page >= result["total_count"]:
                return items
            page += 1

    async def restore_wiki_page(self, wiki_id: str, page_id: str) -> None:
        """Restore a deleted wiki page from the trash."""
        await self._request(f"api/v2.1/wiki2/{wiki_id}/trash/", method=METH_PUT, data={"page_id": page_id})

    async def clean_wiki_trash(self, wiki_id: str, *, keep_days: int = 0) -> None:
        """Permanently delete wiki pages that were deleted more than `keep_days` days ago."""
        await self._request(f"api/v2.1/wiki2/{wiki_id}/trash/", method=METH_DELETE, data={"keep_days": str(keep_days)})

    async def get_wiki_publish_info(self, wiki_id: str) -> WikiPublishInfo:
        """Return whether and where a wiki is published."""
        return WikiPublishInfo.from_dict(await self._request(f"api/v2.1/wiki2/{wiki_id}/publish/"))

    async def publish_wiki(self, wiki_id: str, publish_url: str, *, enable_server_render: bool = False) -> WikiPublishInfo:
        """Publish a wiki under `<server>/wiki/publish/<publish_url>`.

        Args:
        ----
            wiki_id: ID of the wiki.
            publish_url: 5 to 30 letters, digits or hyphens.
            enable_server_render: Render pages on the server, for search engines.

        """
        result = await self._request(
            f"api/v2.1/wiki2/{wiki_id}/publish/",
            method=METH_POST,
            data={"publish_url": publish_url, "enable_server_render": str(enable_server_render).lower()},
        )
        return WikiPublishInfo.from_dict(result)

    async def unpublish_wiki(self, wiki_id: str) -> None:
        """Stop publishing a wiki."""
        await self._request(f"api/v2.1/wiki2/{wiki_id}/publish/", method=METH_DELETE)

    async def get_published_wiki_config(self, wiki_id: str) -> WikiDetails:
        """Return the page tree of a published wiki; works without authentication."""
        result = await self._request(f"api/v2.1/wiki2/{wiki_id}/publish/config/", authenticated=self._token is not None)
        return WikiDetails.from_dict(result["wiki"])

    async def get_published_wiki_page(self, wiki_id: str, page_id: str) -> WikiPageContent:
        """Return the read-only SeaDoc access details of a published wiki page; works without authentication."""
        result = await self._request(f"api/v2.1/wiki2/{wiki_id}/publish/page/{page_id}/", authenticated=self._token is not None)
        return WikiPageContent.from_dict(result)

    async def get_metadata_status(self, library_id: str) -> MetadataStatus:
        """Return whether metadata management and tags are enabled for a library (Seafile 13+)."""
        return MetadataStatus.from_dict(await self._request(f"api/v2.1/repos/{library_id}/metadata/"))

    async def enable_metadata(self, library_id: str) -> str:
        """Enable metadata management and tags for a library; returns the ID of the indexing task."""
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/", method=METH_PUT)
        return str(result["task_id"])

    async def disable_metadata(self, library_id: str) -> None:
        """Disable metadata management for a library and delete its metadata, tags and views."""
        await self._request(f"api/v2.1/repos/{library_id}/metadata/", method=METH_DELETE)

    async def enable_metadata_tags(self, library_id: str) -> None:
        """Enable metadata tags for a library with metadata management enabled."""
        await self._request(f"api/v2.1/repos/{library_id}/metadata/tags-status/", method=METH_PUT)

    async def disable_metadata_tags(self, library_id: str) -> None:
        """Disable metadata tags for a library and delete all its tags."""
        await self._request(f"api/v2.1/repos/{library_id}/metadata/tags-status/", method=METH_DELETE)

    async def get_metadata_records(self, library_id: str, view_id: str, *, start: int = 0, limit: int = 1000) -> MetadataQueryResult:
        """Return one page of metadata records (files and folders) matching a view."""
        params = {"view_id": view_id, "start": start, "limit": limit}
        return MetadataQueryResult.from_dict(await self._request(f"api/v2.1/repos/{library_id}/metadata/records/", params=params))

    async def get_metadata_record(
        self,
        library_id: str,
        *,
        record_id: str | None = None,
        parent_dir: str | None = None,
        file_name: str | None = None,
    ) -> MetadataQueryResult:
        """Return the metadata record of one file, by record ID or by `parent_dir` and `file_name`."""
        params = {
            key: value for key, value in {"record_id": record_id, "parent_dir": parent_dir, "file_name": file_name}.items() if value is not None
        }
        return MetadataQueryResult.from_dict(await self._request(f"api/v2.1/repos/{library_id}/metadata/record/", params=params))

    async def update_metadata_record(
        self,
        library_id: str,
        data: Mapping[str, Any],
        *,
        record_id: str | None = None,
        parent_dir: str | None = None,
        file_name: str | None = None,
    ) -> None:
        """Update the editable columns of one metadata record, by record ID or by `parent_dir` and `file_name`.

        Args:
        ----
            library_id: ID of the library.
            data: New values, keyed by column name.
            record_id: ID of the record.
            parent_dir: Folder of the file, used when `record_id` is omitted.
            file_name: Name of the file, used when `record_id` is omitted.

        """
        body: dict[str, Any] = {"data": dict(data)}
        body |= {key: value for key, value in {"record_id": record_id, "parent_dir": parent_dir, "file_name": file_name}.items() if value is not None}
        await self._request(f"api/v2.1/repos/{library_id}/metadata/record/", method=METH_PUT, json_body=body)

    async def update_metadata_records(self, library_id: str, records: Mapping[str, Mapping[str, Any]]) -> None:
        """Update several metadata records; `records` maps record IDs to new values keyed by column name."""
        body = {"records_data": [{"record_id": record_id, "record": dict(values)} for record_id, values in records.items()]}
        await self._request(f"api/v2.1/repos/{library_id}/metadata/records/", method=METH_PUT, json_body=body)

    async def create_metadata_column(
        self, library_id: str, name: str, *, column_type: str = "text", key: str | None = None, data: Any = None
    ) -> MetadataColumn:
        """Add a custom column to the metadata table.

        Args:
        ----
            library_id: ID of the library.
            name: Column name.
            column_type: Column type, such as 'text', 'number', 'date', 'single-select' or 'checkbox'.
            key: Column key; generated when omitted.
            data: Type specific column settings, such as select options.

        """
        body: dict[str, Any] = {"column_name": name, "column_type": column_type}
        if key is not None:
            body["column_key"] = key
        if data is not None:
            body["column_data"] = data
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/columns/", method=METH_POST, json_body=body)
        return MetadataColumn.from_dict(result["column"])

    async def update_metadata_column(self, library_id: str, key: str, *, name: str | None = None, data: Any = None) -> MetadataColumn:
        """Rename a custom metadata column or change its settings."""
        body: dict[str, Any] = {"column_key": key}
        if name is not None:
            body["name"] = name
        if data is not None:
            body["data"] = data
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/columns/", method=METH_PUT, json_body=body)
        return MetadataColumn.from_dict(result["column"])

    async def delete_metadata_column(self, library_id: str, key: str) -> None:
        """Delete a custom metadata column."""
        await self._request(f"api/v2.1/repos/{library_id}/metadata/columns/", method=METH_DELETE, json_body={"column_key": key})

    async def get_metadata_views(self, library_id: str) -> MetadataViews:
        """Return the metadata views of a library and their navigation tree."""
        return MetadataViews.from_dict(await self._request(f"api/v2.1/repos/{library_id}/metadata/views/"))

    async def get_metadata_view(self, library_id: str, view_id: str) -> MetadataView:
        """Return one metadata view."""
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/views/{view_id}/")
        return MetadataView.from_dict(result["view"])

    async def create_metadata_view(
        self,
        library_id: str,
        name: str,
        *,
        view_type: str = "table",
        folder_id: str | None = None,
        data: Mapping[str, Any] | None = None,
    ) -> MetadataView:
        """Create a metadata view.

        Args:
        ----
            library_id: ID of the library.
            name: View name; a suffix is added when it already exists.
            view_type: View type, such as 'table', 'gallery', 'kanban', 'map' or 'card'.
            folder_id: Put the view in this navigation folder.
            data: Initial view settings, such as filters and sorts.

        """
        body: dict[str, Any] = {"name": name, "type": view_type}
        if folder_id is not None:
            body["folder_id"] = folder_id
        if data is not None:
            body["data"] = dict(data)
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/views/", method=METH_POST, json_body=body)
        return MetadataView.from_dict(result["view"])

    async def update_metadata_view(self, library_id: str, view_id: str, view_data: Mapping[str, Any]) -> None:
        """Update the settings of a metadata view, such as `name`, `filters` or `sorts`."""
        body = {"view_id": view_id, "view_data": dict(view_data)}
        await self._request(f"api/v2.1/repos/{library_id}/metadata/views/", method=METH_PUT, json_body=body)

    async def delete_metadata_view(self, library_id: str, view_id: str, *, folder_id: str | None = None) -> None:
        """Delete a metadata view; pass `folder_id` when the view is in a navigation folder."""
        body = {"view_id": view_id}
        if folder_id is not None:
            body["folder_id"] = folder_id
        await self._request(f"api/v2.1/repos/{library_id}/metadata/views/", method=METH_DELETE, json_body=body)

    async def duplicate_metadata_view(self, library_id: str, view_id: str, *, folder_id: str | None = None) -> MetadataView:
        """Copy a metadata view."""
        body = {"view_id": view_id}
        if folder_id is not None:
            body["folder_id"] = folder_id
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/duplicate-view/", method=METH_POST, json_body=body)
        return MetadataView.from_dict(result["view"])

    async def move_metadata_view(  # pylint: disable=too-many-arguments
        self,
        library_id: str,
        *,
        source_view_id: str | None = None,
        source_folder_id: str | None = None,
        target_view_id: str | None = None,
        target_folder_id: str | None = None,
        above_folder: bool = False,
    ) -> list[MetadataNavigationItem]:
        """Move a metadata view or navigation folder next to or into another one; returns the new navigation tree.

        Args:
        ----
            library_id: ID of the library.
            source_view_id: View to move.
            source_folder_id: Folder to move, or the folder that contains `source_view_id`.
            target_view_id: View to move to.
            target_folder_id: Folder to move to, or the folder that contains `target_view_id`.
            above_folder: Place the source above `target_folder_id` instead of inside it.

        """
        body: dict[str, Any] = {"is_above_folder": above_folder}
        optional = {
            "source_view_id": source_view_id,
            "source_folder_id": source_folder_id,
            "target_view_id": target_view_id,
            "target_folder_id": target_folder_id,
        }
        body |= {key: value for key, value in optional.items() if value is not None}
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/move-views/", method=METH_POST, json_body=body)
        return [MetadataNavigationItem.from_dict(item) for item in result["navigation"]]

    async def get_metadata_tags(self, library_id: str, *, per_page: int = 1000) -> list[MetadataTag]:
        """Return all metadata tags of a library; empty when tags are disabled."""
        tags: list[MetadataTag] = []
        start = 0
        while True:
            result = await self._request(f"api/v2.1/repos/{library_id}/metadata/tags/", params={"start": start, "limit": per_page})
            tags.extend(MetadataTag.from_dict(item) for item in result["results"])
            if len(result["results"]) < per_page:
                return tags
            start += per_page

    async def create_metadata_tags(self, library_id: str, tags: Mapping[str, str]) -> list[MetadataTag]:
        """Create metadata tags; `tags` maps names to colors. Returns the new and the already existing tags."""
        body = {"tags_data": [{"_tag_name": name, "_tag_color": color} for name, color in tags.items()]}
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/tags/", method=METH_POST, json_body=body)
        return [MetadataTag.from_dict(item) for item in result["tags"]]

    async def update_metadata_tag(self, library_id: str, tag_id: str, *, name: str | None = None, color: str | None = None) -> None:
        """Rename or recolor a metadata tag."""
        tag = {key: value for key, value in {"_tag_name": name, "_tag_color": color}.items() if value is not None}
        body = {"tags_data": [{"tag_id": tag_id, "tag": tag}]}
        await self._request(f"api/v2.1/repos/{library_id}/metadata/tags/", method=METH_PUT, json_body=body)

    async def delete_metadata_tags(self, library_id: str, tag_ids: Sequence[str]) -> None:
        """Delete metadata tags."""
        await self._request(f"api/v2.1/repos/{library_id}/metadata/tags/", method=METH_DELETE, json_body={"tag_ids": list(tag_ids)})

    async def add_metadata_tag_links(self, library_id: str, column: MetadataTagLinkColumn, links: Mapping[str, Sequence[str]]) -> None:
        """Link tags to other tags, for tag hierarchies; `links` maps a tag ID to the tag IDs to link."""
        body = {"link_column_key": column, "row_id_map": {key: list(value) for key, value in links.items()}}
        await self._request(f"api/v2.1/repos/{library_id}/metadata/tags-links/", method=METH_POST, json_body=body)

    async def set_metadata_tag_links(self, library_id: str, column: MetadataTagLinkColumn, links: Mapping[str, Sequence[str]]) -> None:
        """Replace the links of tags to other tags; `links` maps a tag ID to the complete list of linked tag IDs."""
        body = {"link_column_key": column, "row_id_map": {key: list(value) for key, value in links.items()}}
        await self._request(f"api/v2.1/repos/{library_id}/metadata/tags-links/", method=METH_PUT, json_body=body)

    async def delete_metadata_tag_links(self, library_id: str, column: MetadataTagLinkColumn, links: Mapping[str, Sequence[str]]) -> None:
        """Remove links between tags; `links` maps a tag ID to the tag IDs to unlink."""
        body = {"link_column_key": column, "row_id_map": {key: list(value) for key, value in links.items()}}
        await self._request(f"api/v2.1/repos/{library_id}/metadata/tags-links/", method=METH_DELETE, json_body=body)

    async def set_metadata_file_tags(self, library_id: str, file_tags: Mapping[str, Sequence[str]]) -> None:
        """Replace the tags of files; `file_tags` maps metadata record IDs to the complete list of tag IDs."""
        body = {"file_tags_data": [{"record_id": record_id, "tags": list(tag_ids)} for record_id, tag_ids in file_tags.items()]}
        await self._request(f"api/v2.1/repos/{library_id}/metadata/file-tags/", method=METH_PUT, json_body=body)

    async def get_metadata_tag_files(self, library_id: str, tag_id: str) -> list[MetadataTaggedFile]:
        """Return the files carrying a metadata tag."""
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/tag-files/{tag_id}/")
        return [MetadataTaggedFile.from_dict(item) for item in result["results"]]

    async def get_metadata_tags_files(self, library_id: str, tag_ids: Sequence[str]) -> list[MetadataTaggedFile]:
        """Return the files carrying any of the given metadata tags."""
        result = await self._request(f"api/v2.1/repos/{library_id}/metadata/tags-files/", method=METH_POST, json_body={"tags_ids": list(tag_ids)})
        # Seafile returns a bare empty list when nothing matches.
        if not result:
            return []
        return [MetadataTaggedFile.from_dict(item) for item in result["results"]]

    async def merge_metadata_tags(self, library_id: str, target_tag_id: str, merged_tag_ids: Sequence[str]) -> None:
        """Merge tags into `target_tag_id`; the merged tags are deleted and their files get the target tag."""
        body = {"target_tag_id": target_tag_id, "merged_tags_ids": list(merged_tag_ids)}
        await self._request(f"api/v2.1/repos/{library_id}/metadata/merge-tags/", method=METH_POST, json_body=body)
