"""Models for library endpoints."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from mashumaro import field_options
from mashumaro.mixins.orjson import DataClassORJSONMixin

from aioseafile.models.common import empty_to_none, from_timestamp, optional_datetime
from aioseafile.models.files import DirentType


class LibraryStatus(StrEnum):
    """Status of a library."""

    NORMAL = "normal"
    READ_ONLY = "read-only"


class LibraryApiTokenPermission(StrEnum):
    """Permission of a library API token."""

    READ = "r"
    READ_WRITE = "rw"


class CommitDiffType(StrEnum):
    """Kind of change in a commit."""

    NEW = "new"
    REMOVED = "removed"
    RENAMED = "renamed"
    MODIFIED = "modified"
    NEW_DIR = "newdir"
    DELETED_DIR = "deldir"
    UNKNOWN = ""


@dataclass
class Library(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A library (repo) the account can access, from `api2/repos/`."""

    id: str
    name: str
    owner: str
    size: int
    encrypted: bool
    permission: str
    modified: datetime = field(metadata=field_options(alias="mtime", deserialize=from_timestamp))
    type: str = "repo"
    owner_name: str | None = None
    modifier_email: str | None = None
    modifier_name: str | None = None
    virtual: bool = False
    head_commit_id: str | None = None


@dataclass
class LibraryDetail(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """Details of a single library, from `api2/repos/<id>/`."""

    id: str
    name: str
    owner: str
    size: int
    encrypted: bool
    permission: str
    file_count: int
    modified: datetime = field(metadata=field_options(alias="mtime", deserialize=from_timestamp))
    modifier_email: str | None = None
    modifier_name: str | None = None
    head_commit_id: str | None = None


@dataclass
class LibraryInfo(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """Details of a single library, from `api/v2.1/repos/<id>/`."""

    id: str = field(metadata=field_options(alias="repo_id"))
    name: str = field(metadata=field_options(alias="repo_name"))
    owner_email: str
    owner_name: str
    owner_contact_email: str
    size: int
    encrypted: bool
    file_count: int
    permission: str
    last_modified: datetime
    status: LibraryStatus
    no_quota: bool = False
    is_admin: bool = False
    is_virtual: bool = False
    has_been_shared_out: bool = False
    lib_need_decrypt: bool = False
    enable_onlyoffice: bool = False
    monitored: bool = False
    repo_type: str | None = None
    owner_avatar: str | None = None


@dataclass
class CreatedLibrary(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A newly created library."""

    id: str = field(metadata=field_options(alias="repo_id"))
    name: str = field(metadata=field_options(alias="repo_name"))
    description: str = field(metadata=field_options(alias="repo_desc"))
    owner: str = field(metadata=field_options(alias="email"))
    size: int = field(metadata=field_options(alias="repo_size"))
    last_modified: datetime
    # Seafile sends "" for a plain library and 1 for an encrypted one.
    encrypted: bool = field(metadata=field_options(deserialize=bool))
    enc_version: int
    permission: str
    head_commit_id: str
    repo_version: int | None = None


@dataclass
class DeletedLibrary(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A deleted library in the account's library trash."""

    id: str = field(metadata=field_options(alias="repo_id"))
    name: str = field(metadata=field_options(alias="repo_name"))
    owner_email: str
    owner_name: str
    owner_contact_email: str
    encrypted: bool
    size: int
    deleted: datetime = field(metadata=field_options(alias="del_time"))
    head_commit_id: str | None = None
    org_id: int | None = None


@dataclass
class LibraryCommit(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A commit (snapshot) in the history of a library."""

    commit_id: str
    time: datetime
    email: str
    name: str
    contact_email: str
    description: str
    client_version: str | None = None
    device_name: str | None = None
    second_parent_id: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class LibraryHistory(DataClassORJSONMixin):
    """One page of the history of a library."""

    commits: list[LibraryCommit] = field(metadata=field_options(alias="data"))
    more: bool


@dataclass
class CommitInfo(DataClassORJSONMixin):
    """Author and description of a commit."""

    creator_email: str
    creator_name: str
    creator_contact_email: str
    time: datetime
    description: str
    device_name: str | None = None


@dataclass
class CommitDiff(DataClassORJSONMixin):
    """A change in a commit."""

    op_type: CommitDiffType
    path: str
    new_path: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))


@dataclass
class LibraryCommitDetail(DataClassORJSONMixin):
    """A commit with the changes it made."""

    info: CommitInfo = field(metadata=field_options(alias="commit_info"))
    diffs: list[CommitDiff] = field(metadata=field_options(alias="commit_diffs"))


@dataclass
class SnapshotDirent(DataClassORJSONMixin):
    """A file or folder in a library snapshot."""

    type: DirentType
    name: str
    parent_dir: str
    obj_id: str
    size: int | None = None


@dataclass
class SnapshotRevision(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """The commit a snapshot label points to."""

    repo_id: str
    commit_id: str
    email: str
    name: str
    contact_email: str
    time: datetime
    description: str
    link: str | None = None


@dataclass
class SnapshotLabel(DataClassORJSONMixin):
    """A label on a library snapshot."""

    tag: str
    tag_creator: str
    revision: SnapshotRevision


@dataclass
class TrashItem(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A deleted file or folder in the trash of a library."""

    name: str = field(metadata=field_options(alias="obj_name"))
    parent_dir: str
    commit_id: str
    is_dir: bool
    deleted: datetime = field(metadata=field_options(alias="deleted_time"))
    size: int | None = field(default=None, metadata=field_options(deserialize=empty_to_none))
    obj_id: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))


@dataclass
class TrashRestored(DataClassORJSONMixin):
    """A file or folder restored from the trash."""

    path: str
    is_dir: bool


@dataclass
class TrashRestoreFailure(DataClassORJSONMixin):
    """A file or folder that could not be restored from the trash."""

    path: str
    error_msg: str
    commit_id: str | None = None


@dataclass
class TrashRestoreResult(DataClassORJSONMixin):
    """Result of restoring items from the trash."""

    success: list[TrashRestored]
    failed: list[TrashRestoreFailure]


@dataclass
class LibraryApiToken(DataClassORJSONMixin):
    """An API token that gives access to a single library."""

    repo_id: str
    app_name: str
    generated_by: str
    permission: LibraryApiTokenPermission
    api_token: str = field(repr=False)


@dataclass
class RepoTokenLibraryInfo(DataClassORJSONMixin):
    """The library a library API token belongs to."""

    id: str = field(metadata=field_options(alias="repo_id"))
    name: str = field(metadata=field_options(alias="repo_name"))
    size: int
    file_count: int
    last_modified: datetime


@dataclass
class RepoTokenDirent(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A file or folder listed with a library API token."""

    type: DirentType
    id: str
    name: str
    parent_dir: str
    mtime: datetime
    size: int | None = None
    permission: str | None = None
    starred: bool | None = None
    modifier_email: str | None = None
    modifier_name: str | None = None
    modifier_contact_email: str | None = None
    is_locked: bool | None = None
    lock_owner: str | None = None


@dataclass
class RepoTokenDir(DataClassORJSONMixin):
    """A folder created or renamed with a library API token."""

    repo_id: str
    name: str = field(metadata=field_options(alias="obj_name"))
    parent_dir: str
    obj_id: str
    mtime: datetime


@dataclass
class RepoTokenFile(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A file accessed with a library API token."""

    repo_id: str
    name: str = field(metadata=field_options(alias="obj_name"))
    parent_dir: str
    obj_id: str | None = field(metadata=field_options(deserialize=empty_to_none))
    size: int | None = field(metadata=field_options(deserialize=empty_to_none))
    mtime: datetime | None = field(metadata=field_options(deserialize=optional_datetime))
    can_preview: bool
    can_edit: bool
    is_locked: bool
    doc_uuid: str | None = None


@dataclass
class RepoTokenSearchResult(DataClassORJSONMixin):
    """A file found with a library API token."""

    path: str
    size: int
    mtime: datetime
    type: DirentType


@dataclass
class RepoTokenDeletedFile(DataClassORJSONMixin):
    """A file deleted from the library of a library API token."""

    name: str = field(metadata=field_options(alias="obj_name"))
    parent_dir: str = field(metadata=field_options(alias="path"))
