"""Models for group, department and organization endpoints."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from mashumaro import field_options
from mashumaro.mixins.orjson import DataClassORJSONMixin

from aioseafile.models.common import optional_int
from aioseafile.models.sharing import ShareFailure


class GroupRole(StrEnum):
    """Role of a member in a group."""

    OWNER = "Owner"
    ADMIN = "Admin"
    MEMBER = "Member"


@dataclass
class GroupLibrary(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A library shared with a group, from `api/v2.1/groups/<id>/libraries/`."""

    id: str = field(metadata=field_options(alias="repo_id"))
    name: str = field(metadata=field_options(alias="repo_name"))
    size: int
    encrypted: bool
    permission: str
    last_modified: datetime
    is_admin: bool = False
    owner_email: str | None = None
    owner_name: str | None = None
    owner_contact_email: str | None = None
    modifier_email: str | None = None
    modifier_name: str | None = None
    modifier_contact_email: str | None = None
    starred: bool = False
    monitored: bool = False
    status: str | None = None


@dataclass
class Group(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A group or department.

    `parent_group_id` is 0 for a regular group, -1 for a top level department
    and the parent's id for a sub-department.
    """

    id: int
    name: str
    owner: str
    created_at: datetime
    parent_group_id: int = 0
    admins: list[str] = field(default_factory=list)
    group_quota: int | None = None
    group_quota_usage: int | None = None
    libraries: list[GroupLibrary] | None = field(default=None, metadata=field_options(alias="repos"))

    @property
    def is_department(self) -> bool:
        """Return whether the group is a department."""
        return self.parent_group_id != 0


@dataclass
class GroupMember(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A member of a group."""

    email: str
    name: str
    is_admin: bool
    role: GroupRole
    group_id: int | None = None
    contact_email: str | None = None
    login_id: str | None = None
    avatar_url: str | None = None


@dataclass
class GroupMemberFailure(DataClassORJSONMixin):
    """A user that could not be added to a group."""

    email: str
    error_msg: str
    email_name: str | None = None


@dataclass
class GroupMembersResult(DataClassORJSONMixin):
    """Result of adding several members to a group."""

    success: list[GroupMember]
    failed: list[GroupMemberFailure]


@dataclass
class GroupInviteLink(DataClassORJSONMixin):
    """A link that lets users join a group."""

    id: int
    token: str
    group_id: int
    created_at: datetime
    created_by: str
    link: str


@dataclass
class Department(DataClassORJSONMixin):
    """A department (Pro), from `api/v2.1/departments/` or the address book."""

    id: int
    name: str
    owner: str
    created_at: datetime
    parent_group_id: int
    email: str | None = None
    quota: int | None = None


@dataclass
class DepartmentLibrary(DataClassORJSONMixin):
    """A library owned by a department (Pro)."""

    id: str
    name: str
    size: int
    encrypted: bool
    owner: str
    modified: datetime = field(metadata=field_options(alias="mtime"))
    group_name: str | None = None
    permission: str | None = None


@dataclass
class DepartmentLibraryUserShare(DataClassORJSONMixin):
    """A user a department library is shared with."""

    user_email: str
    permission: str
    user_name: str | None = None
    user_contact_email: str | None = None
    avatar_url: str | None = None


@dataclass
class DepartmentLibraryGroupShare(DataClassORJSONMixin):
    """A group a department library is shared with."""

    group_id: int
    group_name: str
    permission: str


@dataclass
class DepartmentLibraryUserShareResult(DataClassORJSONMixin):
    """Result of sharing a department library with users."""

    success: list[DepartmentLibraryUserShare]
    failed: list[ShareFailure]


@dataclass
class DepartmentLibraryGroupShareResult(DataClassORJSONMixin):
    """Result of sharing a department library with groups."""

    success: list[DepartmentLibraryGroupShare]
    failed: list[ShareFailure]


@dataclass
class OrgInfo(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """An organization as seen by its admin (multi-tenancy), from `api/v2.1/org/admin/info/`."""

    org_id: int
    org_name: str | None
    storage_quota: int
    storage_usage: int
    user_default_quota: int
    member_usage: int
    active_members: int
    member_quota: int | None = None
    file_ext_white_list: str | None = None
    traffic_this_month: int | None = None
    monthly_download_traffic_limit: int | None = None
    disable_org_encrypted_library: bool = False
    disable_org_user_clean_trash: bool = False
    force_adfs_login: bool = False
    ai_credit: float | None = None
    ai_credit_used: float | None = None


@dataclass
class OrgUser(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A user of an organization."""

    email: str
    name: str
    quota_usage: int
    quota_total: int
    contact_email: str | None = None
    is_active: bool | None = None
    is_staff: bool | None = None
    create_time: datetime | None = None
    last_login: datetime | None = None
    avatar_url: str | None = None


@dataclass
class OrgGroup(DataClassORJSONMixin):
    """A group in an organization."""

    id: int
    name: str = field(metadata=field_options(alias="group_name"))
    created_at: datetime = field(metadata=field_options(alias="ctime"))
    creator_email: str
    creator_name: str | None = None
    creator_contact_email: str | None = None


@dataclass
class OrgLibrary(DataClassORJSONMixin):  # pylint: disable=too-many-instance-attributes
    """A library in an organization."""

    id: str = field(metadata=field_options(alias="repo_id"))
    name: str = field(metadata=field_options(alias="repo_name"))
    owner_email: str
    size: int
    encrypted: bool
    owner_name: str | None = None
    file_count: int | None = None
    is_department_repo: bool = False
    group_id: int | None = field(default=None, metadata=field_options(deserialize=optional_int))
