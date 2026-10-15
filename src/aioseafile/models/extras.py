"""Models for tags, metadata, wiki, comments, search and other Seafile 13+/Pro endpoints."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from mashumaro import field_options
from mashumaro.mixins.orjson import DataClassORJSONMixin

from aioseafile.models.common import from_timestamp, optional_datetime


@dataclass
class SearchResultItem(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A file or folder found by the full text search."""

    repo_id: str
    name: str
    fullpath: str
    is_dir: bool = False
    size: int | None = None
    modified: datetime | None = field(default=None, metadata=field_options(alias="last_modified", deserialize=from_timestamp))
    repo_name: str | None = None
    repo_encrypted: bool | None = None
    repo_owner_email: str | None = None
    repo_owner_name: str | None = None
    repo_owner_contact_email: str | None = None
    repo_type: str | None = None
    content_highlight: str | None = None
    permission: str | None = None
    thumbnail_url: str | None = None


@dataclass
class SearchResult(DataClassORJSONMixin):
    """One page of full text search results."""

    total: int
    has_more: bool
    results: list[SearchResultItem] = field(default_factory=list)


class LibrarySearchItemType(StrEnum):
    """Type of an entry found by the library file name search."""

    FILE = "file"
    FOLDER = "folder"


@dataclass
class LibrarySearchItem(DataClassORJSONMixin):
    """A file or folder found by name in one library."""

    path: str
    type: LibrarySearchItemType
    size: int = 0
    modified: datetime | None = field(default=None, metadata=field_options(alias="mtime"))


@dataclass
class RepoTag(DataClassORJSONMixin):
    """A library tag (the tag system from before metadata tags)."""

    repo_tag_id: int
    tag_name: str
    tag_color: str
    repo_id: str | None = None
    files_count: int | None = None


@dataclass
class FileTag(DataClassORJSONMixin):
    """A library tag attached to a file."""

    file_tag_id: int
    repo_tag_id: int
    tag_name: str | None = None
    tag_color: str | None = None


@dataclass
class TaggedFile(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A file carrying a library tag; for deleted files only the name is known."""

    file_tag_id: int
    filename: str
    parent_path: str | None = None
    size: int | None = None
    modified: datetime | None = field(default=None, metadata=field_options(alias="mtime", deserialize=from_timestamp))
    modifier_email: str | None = None
    modifier_name: str | None = None
    modifier_contact_email: str | None = None
    file_deleted: bool = False


@dataclass
class FileCommentReply(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A reply to a file comment."""

    id: int
    reply: str
    # The create response sends the comment ID as a string.
    comment_id: int = field(metadata=field_options(deserialize=int))
    author: str | None = None
    type: str | None = None
    doc_uuid: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    user_name: str | None = None
    user_email: str | None = None
    user_contact_email: str | None = None
    avatar_url: str | None = None


@dataclass
class FileComment(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A comment on a file (a SeaDoc or wiki page)."""

    id: int
    comment: str
    resolved: bool = False
    detail: str | None = None
    repo_id: str | None = None
    parent_path: str | None = None
    item_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    user_name: str | None = None
    user_email: str | None = None
    user_contact_email: str | None = None
    avatar_url: str | None = None
    replies: list[FileCommentReply] = field(default_factory=list)


@dataclass
class Wiki(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A wiki (the wiki2 API, Seafile 12+)."""

    id: str
    name: str
    repo_id: str | None = None
    owner: str | None = None
    owner_nickname: str | None = None
    updated_at: datetime | None = None
    type: str | None = None
    permission: str | None = None
    is_published: bool | None = None
    public_url_suffix: str | None = None
    public_url: str | None = None
    enable_server_render: bool | None = None
    color: str | None = None
    icon: str | None = None
    group_id: int | None = None
    group_name: str | None = None
    group_admins: list[str] | None = None


@dataclass
class GroupWikis(DataClassORJSONMixin):
    """The wikis of one group."""

    group_id: int
    group_name: str
    owner: str | None = None
    group_admins: list[str] = field(default_factory=list)
    wikis: list[Wiki] = field(default_factory=list, metadata=field_options(alias="wiki_info"))


@dataclass
class WikiList(DataClassORJSONMixin):
    """The wikis visible to the user."""

    wikis: list[Wiki] = field(default_factory=list)
    group_wikis: list[GroupWikis] = field(default_factory=list)


@dataclass
class WikiNavigationItem(DataClassORJSONMixin):
    """An entry in the wiki navigation tree."""

    id: str
    type: str
    children: list[WikiNavigationItem] = field(default_factory=list)


@dataclass
class WikiPage(DataClassORJSONMixin):
    """A page in the wiki configuration."""

    id: str
    name: str
    path: str | None = None
    icon: str | None = None
    doc_uuid: str | None = field(default=None, metadata=field_options(alias="docUuid"))
    locked: bool = False
    cover_img_url: str | None = None


@dataclass
class WikiConfig(DataClassORJSONMixin):
    """The page tree of a wiki."""

    version: int | None = None
    navigation: list[WikiNavigationItem] = field(default_factory=list)
    pages: list[WikiPage] = field(default_factory=list)


@dataclass
class WikiDetails(DataClassORJSONMixin):
    """A wiki with its configuration."""

    id: str
    name: str
    repo_id: str | None = None
    owner: str | None = None
    updated_at: datetime | None = None
    wiki_config: WikiConfig = field(default_factory=WikiConfig)


@dataclass
class WikiPageCreated(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A newly created wiki page."""

    page_id: str
    page_name: str
    doc_uuid: str
    repo_id: str
    parent_dir: str
    obj_name: str
    locked: bool = False
    modified: datetime | None = field(default=None, metadata=field_options(alias="mtime", deserialize=optional_datetime))


@dataclass
class WikiPageContent(DataClassORJSONMixin):
    """Access details for the SeaDoc behind a wiki page."""

    seadoc_access_token: str
    assets_url: str
    permission: str | None = None
    latest_contributor: str | None = None
    last_modified: datetime | None = field(default=None, metadata=field_options(deserialize=from_timestamp))


@dataclass
class WikiTrashItem(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A deleted wiki page."""

    id: int
    page_id: str
    name: str
    repo_id: str | None = None
    doc_uuid: str | None = None
    parent_page_id: str | None = None
    subpages: str | None = None
    delete_time: datetime | None = None
    size: int | None = None


@dataclass
class WikiPublishInfo(DataClassORJSONMixin):
    """Publishing state of a wiki; `publish_url` is empty when it is not published."""

    publish_url: str
    enable_server_render: bool = False
    creator: str | None = None
    created_at: datetime | None = field(default=None, metadata=field_options(deserialize=optional_datetime))
    visit_count: int | None = None

    @property
    def is_published(self) -> bool:
        """Return whether the wiki is published."""
        return bool(self.publish_url)


@dataclass
class MetadataStatus(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """Metadata management state of a library."""

    enabled: bool
    tags_enabled: bool = False
    tags_lang: str | None = None
    summary_enabled: bool | None = None
    ocr_enabled: bool | None = None
    face_recognition_enabled: bool | None = None
    details_settings: str | None = None
    global_hidden_columns: list[str] | None = None
    show_view: bool | None = None


@dataclass
class MetadataColumn(DataClassORJSONMixin):
    """A column of a metadata table."""

    key: str
    name: str
    type: str
    data: Any = None


@dataclass
class MetadataQueryResult(DataClassORJSONMixin):
    """Rows of a metadata table; row keys are column keys such as `_name` or `_parent_dir`."""

    metadata: list[MetadataColumn] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MetadataLink(DataClassORJSONMixin):
    """A link from one metadata row to another."""

    row_id: str
    display_value: str | None = None


@dataclass
class MetadataTag(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A metadata tag (Seafile 13+)."""

    id: str = field(metadata=field_options(alias="_id"))
    name: str = field(metadata=field_options(alias="_tag_name"))
    color: str | None = field(default=None, metadata=field_options(alias="_tag_color"))
    creator: str | None = field(default=None, metadata=field_options(alias="_creator"))
    created: datetime | None = field(default=None, metadata=field_options(alias="_ctime"))
    last_modifier: str | None = field(default=None, metadata=field_options(alias="_last_modifier"))
    modified: datetime | None = field(default=None, metadata=field_options(alias="_mtime"))
    file_links: list[MetadataLink] = field(default_factory=list, metadata=field_options(alias="_tag_file_links"))
    parent_links: list[MetadataLink] = field(default_factory=list, metadata=field_options(alias="_tag_parent_links"))
    sub_links: list[MetadataLink] = field(default_factory=list, metadata=field_options(alias="_tag_sub_links"))


@dataclass
class MetadataTaggedFile(DataClassORJSONMixin):
    """A file carrying metadata tags."""

    id: str = field(metadata=field_options(alias="_id"))
    name: str = field(metadata=field_options(alias="_name"))
    parent_dir: str = field(metadata=field_options(alias="_parent_dir"))
    size: int | None = field(default=None, metadata=field_options(alias="_size"))
    modified: datetime | None = field(default=None, metadata=field_options(alias="_file_mtime"))
    tags: list[MetadataLink] = field(default_factory=list, metadata=field_options(alias="_tags"))


class MetadataTagLinkColumn(StrEnum):
    """Link columns of the metadata tags table, for tag hierarchies."""

    PARENT = "_tag_parent_links"
    SUB = "_tag_sub_links"


@dataclass
class MetadataView(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A saved view on the metadata table."""

    id: str = field(metadata=field_options(alias="_id"))
    name: str
    type: str = "table"
    table_id: str | None = None
    filter_conjunction: str | None = None
    filters: list[dict[str, Any]] = field(default_factory=list)
    basic_filters: list[dict[str, Any]] = field(default_factory=list)
    sorts: list[dict[str, Any]] = field(default_factory=list)
    groupbys: list[dict[str, Any]] = field(default_factory=list)
    hidden_columns: list[str] = field(default_factory=list)


@dataclass
class MetadataNavigationItem(DataClassORJSONMixin):
    """An entry in the metadata views navigation; folders have a name and children."""

    id: str = field(metadata=field_options(alias="_id"))
    type: str
    name: str | None = None
    children: list[MetadataNavigationItem] = field(default_factory=list)


@dataclass
class MetadataViews(DataClassORJSONMixin):
    """The metadata views of a library and their navigation tree."""

    views: list[MetadataView] = field(default_factory=list)
    navigation: list[MetadataNavigationItem] = field(default_factory=list)
