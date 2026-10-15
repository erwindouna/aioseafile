"""Models for server and account endpoints."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from mashumaro import field_options
from mashumaro.mixins.orjson import DataClassORJSONMixin

from aioseafile.models.common import from_timestamp, optional_datetime


def _optional_timestamp(value: int | None) -> datetime | None:
    """Parse a Unix timestamp that Seafile sends as 0 when unset."""
    return from_timestamp(value) if value else None


@dataclass
class ServerInfo(DataClassORJSONMixin):
    """Server version and enabled features, from `api2/server-info/`."""

    version: str
    encrypted_library_version: int | None = None
    features: list[str] = field(default_factory=list)

    @property
    def is_pro(self) -> bool:
        """Return whether the server runs the Professional edition."""
        return "seafile-pro" in self.features


@dataclass
class AccountInfo(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """Account details and quota, from `api2/account/info/`."""

    email: str
    name: str
    usage: int
    total: int
    contact_email: str | None = None
    login_id: str | None = None
    institution: str | None = None
    is_staff: bool = False
    avatar_url: str | None = None
    department: str | None = None
    space_usage: str | None = None
    enable_subscription: bool | None = None
    file_updates_email_interval: int | None = None
    collaborate_email_interval: int | None = None
    is_org_staff: bool | None = None
    is_inst_admin: bool | None = None

    @property
    def quota_unlimited(self) -> bool:
        """Return whether the account has no quota.

        Seafile reports a negative total (-2) for an unlimited quota.
        """
        return self.total < 0

    @property
    def quota_total(self) -> int | None:
        """Return the quota in bytes, or None when unlimited."""
        return None if self.quota_unlimited else self.total


@dataclass
class UserProfile(DataClassORJSONMixin):
    """Profile of the account, from `api/v2.1/user/`."""

    email: str
    name: str
    contact_email: str | None = None
    telephone: str | None = None
    login_id: str | None = None
    list_in_address_book: bool = False


@dataclass
class SearchedUser(DataClassORJSONMixin):
    """A user found by `api2/search-user/`."""

    email: str
    name: str
    contact_email: str | None = None
    avatar_url: str | None = None
    login_id: str | None = None


@dataclass
class UserAvatar(DataClassORJSONMixin):
    """Avatar of a user, from `api2/avatars/user/<email>/resized/<size>/`."""

    url: str
    is_default: bool
    uploaded: datetime | None = field(default=None, metadata=field_options(alias="mtime", deserialize=_optional_timestamp))


@dataclass
class Device(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A device (desktop or mobile client) linked to the account, from `api2/devices/`.

    The response also holds the device's API token; it is deliberately not kept.
    """

    platform: str
    device_id: str
    device_name: str
    last_accessed: datetime
    user: str | None = None
    client_version: str | None = None
    platform_version: str | None = None
    last_login_ip: str | None = None
    wiped_at: datetime | None = None
    is_desktop_client: bool = False


@dataclass
class ActivityDetail(DataClassORJSONMixin):
    """A single item of an activity; batch operations list several."""

    path: str
    repo_name: str | None = None
    obj_id: str | None = None
    size: int | None = None
    old_path: str | None = None


@dataclass
class Activity(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A file activity event, from `api/v2.1/activities/`."""

    op_type: str
    obj_type: str
    repo_id: str
    repo_name: str
    path: str
    name: str
    time: datetime
    commit_id: str | None = None
    author_email: str | None = None
    author_name: str | None = None
    author_contact_email: str | None = None
    login_id: str | None = None
    avatar_url: str | None = None
    count: int = 0
    details: list[ActivityDetail] = field(default_factory=list)
    days: int | None = None
    old_repo_name: str | None = None
    old_path: str | None = None
    old_name: str | None = None


@dataclass
class Notification(DataClassORJSONMixin):
    """A user notification; `detail` depends on the notification `type`."""

    id: int
    type: str
    time: datetime
    seen: bool
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Notifications(DataClassORJSONMixin):
    """One page of notifications, from `api/v2.1/notifications/` or `api/v2.1/sdoc-notifications/`."""

    unseen_count: int
    count: int
    notifications: list[Notification] = field(default_factory=list, metadata=field_options(alias="notification_list"))


@dataclass
class AllNotifications(DataClassORJSONMixin):
    """General and discussion (SeaDoc) notifications, from `api/v2.1/all-notifications/`."""

    general: Notifications
    discussion: Notifications
    total_unseen_count: int


@dataclass
class SystemNotification(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A message an admin sent to the user, from `api/v2.1/sys-user-notifications/`."""

    id: int
    msg: str
    username: str
    seen: bool
    created_at: datetime
    name: str | None = None
    contact_email: str | None = None
    org_name: str | None = None
    msg_format: str | None = None


class InvitationType(StrEnum):
    """Type of an invitation."""

    GUEST = "guest"


@dataclass
class Invitation(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A guest invitation, from `api/v2.1/invitations/`."""

    id: int
    token: str
    inviter: str
    accepter: str
    type: InvitationType
    invite_time: datetime
    expire_time: datetime
    accept_time: datetime | None = field(default=None, metadata=field_options(deserialize=optional_datetime))


@dataclass
class InvitationFailure(DataClassORJSONMixin):
    """An address a batch invitation could not be sent to."""

    email: str
    error_msg: str


@dataclass
class InvitationBatchResult(DataClassORJSONMixin):
    """Result of `api/v2.1/invitations/batch/`."""

    success: list[Invitation] = field(default_factory=list)
    failed: list[InvitationFailure] = field(default_factory=list)
