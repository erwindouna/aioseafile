"""Models for share link, upload link and share endpoints."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from mashumaro import field_options
from mashumaro.mixins.orjson import DataClassORJSONMixin

from aioseafile.models.common import from_timestamp, optional_datetime


def _tokens(items: list[dict[str, Any]]) -> list[str]:
    return [item["token"] for item in items]


def _emails(items: list[dict[str, Any]]) -> list[str]:
    return [item["email"] for item in items]


OPTIONAL_DATETIME = field_options(deserialize=optional_datetime)


class ShareType(StrEnum):
    """Target of a library or folder share."""

    USER = "user"
    GROUP = "group"


class ShareLinkScope(StrEnum):
    """Who may open a share link."""

    ALL_USERS = "all_users"
    SPECIFIC_USERS = "specific_users"
    SPECIFIC_EMAILS = "specific_emails"


@dataclass
class ShareFailure(DataClassORJSONMixin):
    """A target that could not be processed in a batch request; only the fields that apply are set."""

    error_msg: str
    email: str | None = None
    name: str | None = None
    token: str | None = None
    repo_id: str | None = None
    user_email: str | None = None
    group_id: int | str | None = None
    group_name: str | None = None


@dataclass
class ShareLinkPermissions(DataClassORJSONMixin):
    """What visitors of a share link may do."""

    can_edit: bool
    can_download: bool
    can_upload: bool = False
    can_copy_content: bool | None = None


@dataclass
class ShareLink(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A share (download) link, from `api/v2.1/share-links/`."""

    username: str
    repo_id: str
    repo_name: str
    path: str
    obj_name: str
    is_dir: bool
    token: str
    link: str
    permissions: ShareLinkPermissions
    ctime: datetime | None = field(default=None, metadata=OPTIONAL_DATETIME)
    expire_date: datetime | None = field(default=None, metadata=OPTIONAL_DATETIME)
    is_expired: bool = False
    password: str | None = None
    obj_id: str | None = None
    download_link: str | None = None
    show_download_link: bool = False
    view_cnt: int = 0
    user_scope: ShareLinkScope | None = None
    description: str | None = None
    can_edit: bool = False
    repo_folder_permission: str | None = None


@dataclass
class ShareLinkDirent(DataClassORJSONMixin):
    """An entry in a folder share link, from `api/v2.1/share-links/<token>/dirents/`."""

    is_dir: bool
    size: int
    last_modified: datetime
    folder_path: str | None = None
    folder_name: str | None = None
    file_path: str | None = None
    file_name: str | None = None

    @property
    def path(self) -> str:
        """Return the path of the entry relative to the share link."""
        return self.folder_path or self.file_path or ""

    @property
    def name(self) -> str:
        """Return the name of the entry."""
        return self.folder_name or self.file_name or ""


@dataclass
class ShareLinkUser(DataClassORJSONMixin):
    """A user allowed to open a share link scoped to specific users."""

    username: str
    name: str
    link_token: str
    contact_email: str | None = None
    avatar_url: str | None = None


@dataclass
class ShareLinkUsersResult(DataClassORJSONMixin):
    """Result of adding users to a share link."""

    success: list[ShareLinkUser]
    failed: list[ShareFailure]


@dataclass
class ShareLinkEmailsResult(DataClassORJSONMixin):
    """Result of adding email addresses to a share link; `success` holds the addresses."""

    success: list[str] = field(metadata=field_options(deserialize=_emails))
    failed: list[ShareFailure] = field(default_factory=list)


@dataclass
class LinkDeleteResult(DataClassORJSONMixin):
    """Result of deleting several share or upload links; `success` holds the tokens."""

    success: list[str] = field(metadata=field_options(deserialize=_tokens))
    failed: list[ShareFailure] = field(default_factory=list)


@dataclass
class SendLinkResult(DataClassORJSONMixin):
    """Result of emailing a share or upload link; `success` holds the addresses."""

    success: list[str]
    failed: list[ShareFailure]


@dataclass
class UploadLink(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """An upload link, from `api/v2.1/upload-links/`."""

    repo_id: str
    repo_name: str
    path: str
    obj_name: str
    token: str
    link: str
    ctime: datetime | None = field(default=None, metadata=OPTIONAL_DATETIME)
    expire_date: datetime | None = field(default=None, metadata=OPTIONAL_DATETIME)
    is_expired: bool = False
    username: str | None = None
    obj_id: str | None = None
    view_cnt: int = 0
    password: str | None = None
    description: str | None = None


@dataclass
class LibraryLink(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A share or upload link of a library, from `api/v2.1/repos/<id>/share-links/` or `upload-links/`."""

    repo_id: str
    repo_name: str
    path: str
    obj_name: str
    token: str
    link: str
    creator_email: str
    creator_name: str
    ctime: datetime | None = field(default=None, metadata=OPTIONAL_DATETIME)
    expire_date: datetime | None = field(default=None, metadata=OPTIONAL_DATETIME)
    view_cnt: int = 0
    is_dir: bool | None = None
    creator_contact_email: str | None = None
    creator_avatar: str | None = None


@dataclass
class SharedUserInfo(DataClassORJSONMixin):
    """The user a library or folder is shared to."""

    name: str
    nickname: str | None = None
    contact_email: str | None = None
    avatar_url: str | None = None


@dataclass
class SharedGroupInfo(DataClassORJSONMixin):
    """The group a library or folder is shared to."""

    id: int
    name: str


@dataclass
class SharedItem(DataClassORJSONMixin):
    """A user or group share of a library or folder, from `api2/repos/<id>/dir/shared_items/`."""

    share_type: ShareType
    permission: str
    is_admin: bool = False
    user_info: SharedUserInfo | None = None
    group_info: SharedGroupInfo | None = None


@dataclass
class ShareResult(DataClassORJSONMixin):
    """Result of sharing a library or folder to users or groups."""

    success: list[SharedItem]
    failed: list[ShareFailure]
    virtual_repo_id: str | None = None


@dataclass
class BatchShareItem(DataClassORJSONMixin):
    """A library shared or unshared by `api/v2.1/repos/batch/`."""

    repo_id: str
    username: str | None = None
    group_id: int | None = None
    group_name: str | None = None
    permission: str | None = None


@dataclass
class BatchShareResult(DataClassORJSONMixin):
    """Result of sharing or unsharing several libraries at once."""

    success: list[BatchShareItem]
    failed: list[ShareFailure]


@dataclass
class SharedLibrary(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A library shared out by the account, from `api/v2.1/shared-repos/`.

    `share_type` is 'personal', 'group' or 'public'.
    """

    repo_id: str
    repo_name: str
    share_type: str
    share_permission: str
    encrypted: bool = False
    share_permission_name: str | None = None
    modifier_email: str | None = None
    modifier_name: str | None = None
    modifier_contact_email: str | None = None
    user_email: str | None = None
    user_name: str | None = None
    contact_email: str | None = None
    group_id: int | None = None
    group_name: str | None = None
    is_admin: bool | None = None
    share_from: str | None = None
    share_from_user_name: str | None = None


@dataclass
class SharedFolder(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A folder shared out by the account, from `api/v2.1/shared-folders/`."""

    repo_id: str
    repo_name: str
    path: str
    folder_name: str
    share_type: str
    share_permission: str
    share_permission_name: str | None = None
    user_email: str | None = None
    user_name: str | None = None
    contact_email: str | None = None
    group_id: int | None = None
    group_name: str | None = None
    share_from: str | None = None
    share_from_user_name: str | None = None


@dataclass
class ReceivedShare(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A library or folder shared to the account, from `api2/beshared-repos/`.

    `user` is the account that shared it. A shared folder has `is_virtual` set
    and `origin_*` pointing to its library.
    """

    repo_id: str
    repo_name: str
    share_type: str
    permission: str
    user: str
    encrypted: bool = False
    size: int = 0
    last_modified: datetime | None = field(default=None, metadata=field_options(deserialize=from_timestamp))
    last_modifier: str | None = None
    is_virtual: bool = False
    origin_repo_id: str | None = None
    origin_repo_name: str | None = None
    origin_path: str | None = None
    group_id: int | None = None
    group_name: str | None = None


@dataclass
class FolderPermission(DataClassORJSONMixin):
    """A sub-folder permission for a user or group (Pro)."""

    repo_id: str
    folder_path: str
    folder_name: str
    permission: str
    user_email: str | None = None
    user_name: str | None = None
    group_id: int | None = None
    group_name: str | None = None


@dataclass
class FolderPermissionResult(DataClassORJSONMixin):
    """Result of adding sub-folder permissions."""

    success: list[FolderPermission]
    failed: list[ShareFailure]


@dataclass
class AdminShareLinkDirent(DataClassORJSONMixin):
    """An entry in a folder share link, as seen by an admin."""

    obj_name: str
    path: str
    size: int
    is_dir: bool
    last_modified: datetime


@dataclass
class AdminShare(DataClassORJSONMixin):
    """A user or group share of a library or folder, from `api/v2.1/admin/shares/`."""

    repo_id: str
    path: str
    share_type: ShareType
    permission: str
    is_admin: bool = False
    user_email: str | None = None
    user_name: str | None = None
    group_id: int | None = None
    group_name: str | None = None


@dataclass
class AdminShareResult(DataClassORJSONMixin):
    """Result of sharing a library or folder as an admin."""

    success: list[AdminShare]
    failed: list[ShareFailure]
