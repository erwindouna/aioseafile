"""Models for directory and file endpoints."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from mashumaro import field_options
from mashumaro.mixins.orjson import DataClassORJSONMixin

from aioseafile.models.common import from_timestamp


class DirentType(StrEnum):
    """Type of a directory entry."""

    FILE = "file"
    DIR = "dir"


@dataclass
class DirectoryEntry(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """An entry in a directory listing."""

    type: DirentType
    id: str
    name: str
    modified: datetime = field(metadata=field_options(alias="mtime", deserialize=from_timestamp))
    permission: str | None = None
    parent_dir: str | None = None
    size: int | None = None
    starred: bool = False
    is_locked: bool | None = None
    modifier_email: str | None = None
    modifier_name: str | None = None

    @property
    def path(self) -> str | None:
        """Return the full path of the entry, when the listing includes the parent directory."""
        return None if self.parent_dir is None else f"{self.parent_dir.rstrip('/')}/{self.name}"


@dataclass
class DirectoryListing(DataClassORJSONMixin):
    """A directory listing; recursive listings leave out the directory ID and permission."""

    entries: list[DirectoryEntry] = field(metadata=field_options(alias="dirent_list"))
    dir_id: str | None = None
    user_perm: str | None = None


@dataclass
class DirectoryDetail(DataClassORJSONMixin):
    """Details of a directory."""

    repo_id: str
    path: str
    name: str
    modified: datetime = field(metadata=field_options(alias="mtime"))
    permission: str | None = None


@dataclass
class DirentInfo(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A file or directory returned after creating, renaming, moving or copying it."""

    type: DirentType
    repo_id: str
    parent_dir: str
    name: str = field(metadata=field_options(alias="obj_name"))
    id: str = field(metadata=field_options(alias="obj_id"))
    modified: datetime | None = field(default=None, metadata=field_options(alias="mtime"))
    size: int | None = None
    is_locked: bool | None = None
    can_preview: bool | None = None
    can_edit: bool | None = None


@dataclass
class FileDetail(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """Details of a file."""

    id: str
    name: str
    size: int
    modified: datetime = field(metadata=field_options(alias="mtime", deserialize=from_timestamp))
    type: str = "file"
    permission: str | None = None
    last_modifier_email: str | None = None
    last_modifier_name: str | None = None
    starred: bool = False
    comment_total: int | None = None
    can_edit: bool | None = None


@dataclass
class FileRevision(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A revision of a file."""

    commit_id: str
    rev_file_id: str
    path: str
    size: int
    created: datetime = field(metadata=field_options(alias="ctime"))
    description: str | None = None
    creator_email: str | None = None
    creator_name: str | None = None
    rev_renamed_old_path: str | None = None


@dataclass
class FileHistory(DataClassORJSONMixin):
    """One page of file revisions; pass `next_start_commit` to get the next page."""

    revisions: list[FileRevision] = field(metadata=field_options(alias="data"))
    next_start_commit: str | None = None


@dataclass
class UploadedFile(DataClassORJSONMixin):
    """A file stored by an upload."""

    id: str
    name: str
    size: int


@dataclass
class StarredItem(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A starred library, directory or file."""

    repo_id: str
    repo_name: str
    path: str
    name: str = field(metadata=field_options(alias="obj_name"))
    is_dir: bool = False
    repo_encrypted: bool = False
    deleted: bool = False
    modified: datetime | None = field(default=None, metadata=field_options(alias="mtime"))
    user_email: str | None = None
    user_name: str | None = None


@dataclass
class SmartLink(DataClassORJSONMixin):
    """A permanent link to a file or directory that survives renames and moves."""

    smart_link: str
    smart_link_token: str
    name: str


@dataclass
class ZipProgress(DataClassORJSONMixin):
    """Progress of a server-side zip task."""

    zipped: int
    total: int
    failed: int = 0
    failed_reason: str | None = None
    canceled: int = 0

    @property
    def done(self) -> bool:
        """Return whether the archive is ready for download."""
        return self.zipped >= self.total


@dataclass
class CopyMoveProgress(DataClassORJSONMixin):
    """Progress of an asynchronous copy or move task."""

    done: bool
    successful: bool
    total: int = 0
    canceled: bool = False
    failed: bool = False
