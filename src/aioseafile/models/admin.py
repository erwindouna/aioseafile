"""Models for admin endpoints."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from mashumaro import field_options
from mashumaro.mixins.orjson import DataClassORJSONMixin

from aioseafile.models.common import empty_to_none, optional_datetime, optional_int


class AdminLibraryStatus(StrEnum):
    """Status of a library."""

    NORMAL = "normal"
    READ_ONLY = "read-only"


class AdminDevicePlatform(StrEnum):
    """Platform filter for the device list."""

    DESKTOP = "desktop"
    MOBILE = "mobile"


class AdminShareType(StrEnum):
    """Target of a share permission change."""

    ALL = "all"
    USER = "user"
    GROUP = "group"
    DEPARTMENT = "department"


@dataclass
class AdminSystemInfo(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """Server-wide statistics, from `api/v2.1/admin/sysinfo/` (admin only)."""

    users_count: int
    active_users_count: int
    repos_count: int
    total_files_count: int
    total_storage: int
    groups_count: int = 0
    org_count: int = 0
    total_devices_count: int = 0
    current_connected_devices_count: int = 0
    multi_tenancy_enabled: bool = False
    is_pro: bool = False
    with_license: bool = False
    license_expiration: str | None = None
    license_mode: str | None = None
    license_maxusers: int = 0
    license_to: str | None = None


@dataclass
class AdminTotalStorage(DataClassORJSONMixin):
    """Total storage on one day, in bytes."""

    timestamp: datetime = field(metadata=field_options(alias="datetime"))
    total_storage: int


@dataclass
class AdminActiveUsers(DataClassORJSONMixin):
    """Number of active users on one day."""

    timestamp: datetime = field(metadata=field_options(alias="datetime"))
    count: int


@dataclass
class AdminFileOperations(DataClassORJSONMixin):
    """Number of file operations on one day."""

    timestamp: datetime = field(metadata=field_options(alias="datetime"))
    added: int
    visited: int
    deleted: int
    modified: int


@dataclass
class AdminSystemTraffic(DataClassORJSONMixin):
    """Server traffic on one day, in bytes."""

    timestamp: datetime = field(metadata=field_options(alias="datetime"))
    web_file_upload: int = field(metadata=field_options(alias="web-file-upload"))
    web_file_download: int = field(metadata=field_options(alias="web-file-download"))
    sync_file_upload: int = field(metadata=field_options(alias="sync-file-upload"))
    sync_file_download: int = field(metadata=field_options(alias="sync-file-download"))
    link_file_upload: int = field(metadata=field_options(alias="link-file-upload"))
    link_file_download: int = field(metadata=field_options(alias="link-file-download"))


@dataclass
class AdminUserTraffic(DataClassORJSONMixin):
    """Traffic of one user in one month, in bytes."""

    email: str
    name: str
    web_file_upload: int
    web_file_download: int
    sync_file_upload: int
    sync_file_download: int
    link_file_upload: int
    link_file_download: int


@dataclass
class AdminMetricDataPoint(DataClassORJSONMixin):
    """One sample of a server metric; labels hold component, node and collected_at."""

    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class AdminMetric(DataClassORJSONMixin):
    """A Prometheus metric collected by seafevents."""

    name: str
    description: str = field(metadata=field_options(alias="help"))
    metric_type: str = field(metadata=field_options(alias="type"))
    data_points: list[AdminMetricDataPoint] = field(default_factory=list)


@dataclass
class AdminSocialAuth(DataClassORJSONMixin):
    """A linked external login of a user."""

    provider: str
    uid: str


@dataclass
class AdminUser(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A user as seen by an admin; `quota_total` is -2 for unlimited."""

    email: str
    name: str
    contact_email: str
    is_staff: bool
    is_active: bool
    quota_usage: int
    quota_total: int
    create_time: datetime
    role: str | None = None
    login_id: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))
    avatar_url: str | None = None
    source: str | None = None
    last_login: datetime | None = field(default=None, metadata=field_options(deserialize=optional_datetime))
    last_access_time: datetime | None = field(default=None, metadata=field_options(deserialize=optional_datetime))
    has_default_device: bool | None = None
    is_force_2fa: bool | None = None
    org_id: int | None = None
    org_name: str | None = None
    institution: str | None = None
    upload_rate_limit: int | None = None
    download_rate_limit: int | None = None
    social_auth: list[AdminSocialAuth] = field(default_factory=list)


@dataclass
class AdminLibrary(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A library as seen by an admin, from `api/v2.1/admin/libraries/`."""

    id: str
    name: str
    owner: str
    size: int
    encrypted: bool
    file_count: int
    status: str
    last_modified: datetime
    owner_name: str | None = None
    owner_email: str | None = None
    owner_contact_email: str | None = None
    group_name: str | None = None


@dataclass
class AdminLibraryCommit(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A commit in the history of a library."""

    commit_id: str
    time: datetime
    description: str
    email: str
    name: str
    contact_email: str | None = None
    client_version: str | None = None
    device_name: str | None = None
    second_parent_id: str | None = None


@dataclass
class AdminLibraryHistory(DataClassORJSONMixin):
    """One page of library history."""

    commits: list[AdminLibraryCommit] = field(metadata=field_options(alias="data"))
    more: bool


@dataclass
class AdminTrashLibrary(DataClassORJSONMixin):
    """A deleted library in the trash."""

    id: str
    name: str
    owner: str
    delete_time: datetime
    owner_name: str | None = None
    group_name: str | None = None


@dataclass
class AdminDevice(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A linked client device."""

    user: str
    platform: str
    device_id: str
    device_name: str
    last_accessed: datetime
    is_desktop_client: bool
    user_name: str | None = None
    client_version: str | None = None
    last_login_ip: str | None = None


@dataclass
class AdminDeviceError(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A sync error reported by a client (Pro)."""

    email: str
    library_id: str = field(metadata=field_options(alias="repo_id"))
    library_name: str = field(metadata=field_options(alias="repo_name"))
    error_msg: str
    name: str | None = None
    device_ip: str | None = None
    device_name: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))
    client_version: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))
    error_time: datetime | None = field(default=None, metadata=field_options(deserialize=optional_datetime))


@dataclass
class AdminShareLink(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A share link; the list omits the library, path and link fields."""

    token: str
    creator_email: str
    created: datetime = field(metadata=field_options(alias="ctime"))
    view_count: int = field(metadata=field_options(alias="view_cnt"))
    creator_name: str | None = None
    creator_contact_email: str | None = None
    obj_name: str | None = None
    library_id: str | None = field(default=None, metadata=field_options(alias="repo_id"))
    library_name: str | None = field(default=None, metadata=field_options(alias="repo_name"))
    path: str | None = None
    is_dir: bool | None = None
    link: str | None = None
    size: int | None = None
    expire_date: datetime | None = field(default=None, metadata=field_options(deserialize=optional_datetime))
    is_expired: bool | None = None
    permissions: dict[str, bool] | None = None


@dataclass
class AdminUploadLink(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """An upload link; the list omits the library and link fields."""

    token: str
    creator_email: str
    path: str
    created: datetime = field(metadata=field_options(alias="ctime"))
    view_count: int = field(metadata=field_options(alias="view_cnt"))
    creator_name: str | None = None
    creator_contact_email: str | None = None
    obj_name: str | None = None
    library_id: str | None = field(default=None, metadata=field_options(alias="repo_id"))
    library_name: str | None = field(default=None, metadata=field_options(alias="repo_name"))
    link: str | None = None
    expire_date: datetime | None = field(default=None, metadata=field_options(deserialize=optional_datetime))
    is_expired: bool | None = None


@dataclass
class AdminGroup(DataClassORJSONMixin):
    """A group as seen by an admin; `quota` is only set on Pro."""

    id: int
    name: str
    owner: str
    created_at: datetime
    owner_name: str | None = None
    quota: int = 0
    parent_group_id: int = 0


@dataclass
class AdminLoginLog(DataClassORJSONMixin):
    """A login attempt (Pro)."""

    email: str
    login_time: datetime
    login_ip: str
    login_success: bool = field(metadata=field_options(alias="log_success"))
    name: str | None = None
    contact_email: str | None = None


@dataclass
class AdminFileAccessLog(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A file or folder access (Pro)."""

    email: str
    time: datetime
    event_type: str
    library_id: str = field(metadata=field_options(alias="repo_id"))
    library_name: str = field(metadata=field_options(alias="repo_name"))
    file_or_dir_name: str
    ip: str | None = None
    device: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))
    name: str | None = None
    contact_email: str | None = None


@dataclass
class AdminFileUpdateLog(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A file change (Pro)."""

    email: str
    time: datetime
    library_id: str = field(metadata=field_options(alias="repo_id"))
    library_name: str = field(metadata=field_options(alias="repo_name"))
    file_operation: str
    commit_id: str
    library_encrypted: bool | None = field(default=None, metadata=field_options(alias="repo_encrypted"))
    name: str | None = None
    contact_email: str | None = None


@dataclass
class AdminSharePermissionLog(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A change to a share permission (Pro)."""

    from_user_email: str
    etype: str
    permission: str
    library_id: str = field(metadata=field_options(alias="repo_id"))
    library_name: str = field(metadata=field_options(alias="repo_name"))
    folder: str
    date: datetime
    share_type: AdminShareType
    from_user_name: str | None = None
    from_user_contact_email: str | None = None
    to_user_email: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))
    to_user_name: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))
    to_user_contact_email: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))
    to_group_id: int | None = field(default=None, metadata=field_options(deserialize=optional_int))
    to_group_name: str | None = field(default=None, metadata=field_options(deserialize=empty_to_none))


@dataclass
class AdminPermissionAuditLog(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A permission change from the legacy permission audit (Pro)."""

    etype: str
    library_id: str = field(metadata=field_options(alias="repo_id"))
    library_name: str = field(metadata=field_options(alias="repo_name"))
    permission: str
    time: datetime
    file_path: str
    from_email: str
    to: str
    from_name: str | None = None


@dataclass
class AdminNotification(DataClassORJSONMixin):
    """A notification sent to a user; `detail` depends on `type`."""

    id: int
    type: str
    time: datetime
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdminSystemNotification(DataClassORJSONMixin):
    """A system banner; at most one is current (shown to all users)."""

    id: int
    msg: str
    is_current: bool


@dataclass
class AdminUserNotification(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """An announcement sent to one user."""

    id: int
    msg: str
    username: str
    seen: bool
    created_at: datetime
    name: str | None = None
    contact_email: str | None = None
    org_name: str | None = None
    msg_format: str | None = None
