"""Admin endpoints; these require an admin account."""

from typing import TYPE_CHECKING, Any

from aiohttp.hdrs import METH_DELETE, METH_POST, METH_PUT

from aioseafile.client import SeafileClient
from aioseafile.models.admin import (
    AdminActiveUsers,
    AdminDevice,
    AdminDeviceError,
    AdminDevicePlatform,
    AdminFileAccessLog,
    AdminFileOperations,
    AdminFileUpdateLog,
    AdminGroup,
    AdminLibrary,
    AdminLibraryHistory,
    AdminLibraryStatus,
    AdminLoginLog,
    AdminMetric,
    AdminNotification,
    AdminPermissionAuditLog,
    AdminShareLink,
    AdminSharePermissionLog,
    AdminSystemInfo,
    AdminSystemNotification,
    AdminSystemTraffic,
    AdminTotalStorage,
    AdminTrashLibrary,
    AdminUploadLink,
    AdminUser,
    AdminUserNotification,
    AdminUserTraffic,
)

if TYPE_CHECKING:
    from datetime import date, datetime

STATISTICS_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _statistics_range(start: datetime, end: datetime) -> dict[str, str]:
    """Format a statistics range; Seafile reads it in the server's time zone."""
    return {"start": start.strftime(STATISTICS_TIME_FORMAT), "end": end.strftime(STATISTICS_TIME_FORMAT)}


def _bool(value: bool) -> str:  # noqa: FBT001
    return "true" if value else "false"


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


class AdminMixin(SeafileClient):  # pylint: disable=too-many-public-methods
    """Admin endpoints; these require an admin account."""

    async def _get_admin_pages(self, uri: str, key: str, *, per_page: int, params: dict[str, Any] | None = None) -> list[Any]:
        """Return the items of all pages of a list with `page_info.has_next_page`."""
        items: list[Any] = []
        page = 1
        while True:
            result = await self._request(uri, params={**(params or {}), "page": page, "per_page": per_page})
            items.extend(result[key])
            if not result["page_info"]["has_next_page"]:
                return items
            page += 1

    async def _get_admin_counted_pages(self, uri: str, key: str, count_key: str, *, per_page: int, params: dict[str, Any] | None = None) -> list[Any]:
        """Return the items of all pages of a list with a total count."""
        items: list[Any] = []
        page = 1
        while True:
            result = await self._request(uri, params={**(params or {}), "page": page, "per_page": per_page})
            # The user list returns one item more than per_page, which repeats on the next page.
            page_items = result[key][:per_page]
            items.extend(page_items)
            if not page_items or len(items) >= result[count_key]:
                return items
            page += 1

    async def get_admin_system_info(self) -> AdminSystemInfo:
        """Return server-wide statistics."""
        return AdminSystemInfo.from_dict(await self._request("api/v2.1/admin/sysinfo/"))

    async def get_admin_total_storage(self, start: datetime, end: datetime) -> list[AdminTotalStorage]:
        """Return the total storage per day (requires seafevents).

        Args:
        ----
            start: First day, in the server's time zone.
            end: Last day, in the server's time zone.

        """
        result = await self._request("api/v2.1/admin/statistics/total-storage/", params=_statistics_range(start, end))
        return [AdminTotalStorage.from_dict(item) for item in result]

    async def get_admin_active_users(self, start: datetime, end: datetime) -> list[AdminActiveUsers]:
        """Return the number of active users per day (requires seafevents)."""
        result = await self._request("api/v2.1/admin/statistics/active-users/", params=_statistics_range(start, end))
        return [AdminActiveUsers.from_dict(item) for item in result]

    async def get_admin_file_operations(self, start: datetime, end: datetime) -> list[AdminFileOperations]:
        """Return the number of file operations per day (requires seafevents)."""
        result = await self._request("api/v2.1/admin/statistics/file-operations/", params=_statistics_range(start, end))
        return [AdminFileOperations.from_dict(item) for item in result]

    async def get_admin_system_traffic(self, start: datetime, end: datetime) -> list[AdminSystemTraffic]:
        """Return the server traffic per day (requires seafevents)."""
        result = await self._request("api/v2.1/admin/statistics/system-traffic/", params=_statistics_range(start, end))
        return [AdminSystemTraffic.from_dict(item) for item in result]

    async def get_admin_user_traffic(self, month: date, *, order_by: str | None = None, per_page: int = 100) -> list[AdminUserTraffic]:
        """Return the traffic per user in a month (requires seafevents).

        Args:
        ----
            month: Any day in the month.
            order_by: A traffic field such as `sync_file_upload`, optionally with `_desc`;
                defaults to `link_file_download_desc`.
            per_page: Page size used while fetching.

        """
        params = _without_none({"month": month.strftime("%Y%m"), "order_by": order_by, "per_page": per_page})
        traffic: list[AdminUserTraffic] = []
        page = 1
        while True:
            result = await self._request("api/v2.1/admin/statistics/system-user-traffic/", params={**params, "page": page})
            traffic.extend(AdminUserTraffic.from_dict(item) for item in result["user_monthly_traffic_list"])
            if not result["has_next_page"]:
                return traffic
            page += 1

    async def get_admin_system_metrics(self) -> list[AdminMetric]:
        """Return the Prometheus metrics collected by seafevents."""
        result = await self._request("api/v2.1/admin/statistics/system-metrics/")
        return [AdminMetric.from_dict(item) for item in result["metrics"]]

    async def get_admin_users(self, *, is_active: bool | None = None, role: str | None = None, per_page: int = 100) -> list[AdminUser]:
        """Return all users in the database, optionally filtered by active state or role."""
        params = _without_none({"is_active": None if is_active is None else int(is_active), "role": role})
        items = await self._get_admin_counted_pages("api/v2.1/admin/users/", "data", "total_count", per_page=per_page, params=params)
        return [AdminUser.from_dict(item) for item in items]

    async def search_admin_users(self, query: str) -> list[AdminUser]:
        """Return up to 20 users whose email, name, contact email or login ID matches the query."""
        result = await self._request("api/v2.1/admin/search-user/", params={"query": query})
        return [AdminUser.from_dict(item) for item in result["user_list"]]

    async def get_admin_user(self, email: str) -> AdminUser:
        """Return one user by email (the virtual `...@auth.local` id on Seafile 11+)."""
        return AdminUser.from_dict(await self._request(f"api/v2.1/admin/users/{email}/"))

    async def create_admin_user(  # pylint: disable=too-many-arguments
        self,
        email: str,
        password: str,
        *,
        name: str | None = None,
        is_staff: bool = False,
        is_active: bool = True,
        quota_total: int | None = None,
        role: str | None = None,
        login_id: str | None = None,
    ) -> AdminUser:
        """Create a user.

        Args:
        ----
            email: Email address; Seafile 11+ stores it as contact email and returns a virtual id.
            password: Initial password.
            name: Display name.
            is_staff: Whether the user is an admin.
            is_active: Whether the user can log in.
            quota_total: Quota in MB (1 MB = 1000000 bytes).
            role: Role name (Pro).
            login_id: Alternative login name.

        """
        form = _without_none(
            {
                "email": email,
                "password": password,
                "name": name,
                "is_staff": _bool(is_staff),
                "is_active": _bool(is_active),
                "quota_total": quota_total,
                "role": role,
                "login_id": login_id,
            }
        )
        return AdminUser.from_dict(await self._request("api/v2.1/admin/users/", method=METH_POST, data=form))

    async def update_admin_user(  # pylint: disable=too-many-arguments
        self,
        email: str,
        *,
        name: str | None = None,
        password: str | None = None,
        is_staff: bool | None = None,
        is_active: bool | None = None,
        quota_total: int | None = None,
        role: str | None = None,
        contact_email: str | None = None,
        login_id: str | None = None,
    ) -> AdminUser:
        """Update a user; only the given fields change.

        Args:
        ----
            email: The user's email (virtual id).
            name: Display name.
            password: New password.
            is_staff: Grant or revoke admin rights.
            is_active: Activate or deactivate the account.
            quota_total: Quota in MB (1 MB = 1000000 bytes).
            role: Role name.
            contact_email: Contact email address.
            login_id: Alternative login name.

        """
        form = _without_none(
            {
                "name": name,
                "password": password,
                "is_staff": None if is_staff is None else _bool(is_staff),
                "is_active": None if is_active is None else _bool(is_active),
                "quota_total": quota_total,
                "role": role,
                "contact_email": contact_email,
                "login_id": login_id,
            }
        )
        return AdminUser.from_dict(await self._request(f"api/v2.1/admin/users/{email}/", method=METH_PUT, data=form))

    async def delete_admin_user(self, email: str) -> None:
        """Delete a user and their libraries."""
        await self._request(f"api/v2.1/admin/users/{email}/", method=METH_DELETE)

    async def get_admin_libraries(self, *, order_by: str | None = None, per_page: int = 100) -> list[AdminLibrary]:
        """Return all libraries on the server.

        Args:
        ----
            order_by: `size` or `file_count` (descending).
            per_page: Page size used while fetching.

        """
        params = _without_none({"order_by": order_by})
        items = await self._get_admin_pages("api/v2.1/admin/libraries/", "repos", per_page=per_page, params=params)
        return [AdminLibrary.from_dict(item) for item in items]

    async def search_admin_libraries(self, *, name: str | None = None, owner: str | None = None) -> list[AdminLibrary]:
        """Return the libraries whose name contains `name` and/or that `owner` owns."""
        result = await self._request("api/v2.1/admin/libraries/", params=_without_none({"name": name, "owner": owner}))
        return [AdminLibrary.from_dict(item) for item in result["repos"]]

    async def get_admin_library(self, library_id: str) -> AdminLibrary:
        """Return one library."""
        return AdminLibrary.from_dict(await self._request(f"api/v2.1/admin/libraries/{library_id}/"))

    async def create_admin_library(self, name: str, *, owner: str | None = None) -> AdminLibrary:
        """Create a library, owned by `owner` or the admin."""
        form = _without_none({"name": name, "owner": owner})
        return AdminLibrary.from_dict(await self._request("api/v2.1/admin/libraries/", method=METH_POST, data=form))

    async def update_admin_library(
        self,
        library_id: str,
        *,
        name: str | None = None,
        owner: str | None = None,
        status: AdminLibraryStatus | None = None,
    ) -> AdminLibrary:
        """Rename a library, transfer it to another owner or change its status.

        Args:
        ----
            library_id: The library.
            name: New name.
            owner: New owner (user email, or `<group_id>@seafile_group`); transfers the library.
            status: `normal` or `read-only`.

        """
        form = _without_none({"name": name, "owner": owner, "status": status})
        return AdminLibrary.from_dict(await self._request(f"api/v2.1/admin/libraries/{library_id}/", method=METH_PUT, data=form))

    async def delete_admin_library(self, library_id: str) -> None:
        """Delete a library; it moves to the trash."""
        await self._request(f"api/v2.1/admin/libraries/{library_id}/", method=METH_DELETE)

    async def get_admin_library_history(self, library_id: str, *, page: int = 1, per_page: int = 100) -> AdminLibraryHistory:
        """Return one page of a library's commits; needs ENABLE_SYS_ADMIN_VIEW_REPO."""
        result = await self._request(f"api/v2.1/admin/libraries/{library_id}/history/", params={"page": page, "per_page": per_page})
        return AdminLibraryHistory.from_dict(result)

    async def get_admin_library_history_limit(self, library_id: str) -> int:
        """Return how many days of history a library keeps; -1 keeps everything."""
        result = await self._request(f"api/v2.1/admin/libraries/{library_id}/history-limit/")
        return int(result["keep_days"])

    async def set_admin_library_history_limit(self, library_id: str, keep_days: int) -> int:
        """Set how many days of history a library keeps; -1 keeps everything, 0 none."""
        result = await self._request(f"api/v2.1/admin/libraries/{library_id}/history-limit/", method=METH_PUT, data={"keep_days": keep_days})
        return int(result["keep_days"])

    async def get_admin_trash_libraries(self, *, owner: str | None = None, per_page: int = 100) -> list[AdminTrashLibrary]:
        """Return the deleted libraries, optionally only those of one owner."""
        if owner is not None:
            result = await self._request("api/v2.1/admin/trash-libraries/", params={"owner": owner})
            items = result["repos"]
        else:
            items = await self._get_admin_pages("api/v2.1/admin/trash-libraries/", "repos", per_page=per_page)
        return [AdminTrashLibrary.from_dict(item) for item in items]

    async def restore_admin_trash_library(self, library_id: str) -> None:
        """Restore a deleted library."""
        await self._request(f"api/v2.1/admin/trash-libraries/{library_id}/", method=METH_PUT)

    async def delete_admin_trash_library(self, library_id: str) -> None:
        """Permanently delete one library from the trash."""
        await self._request(f"api/v2.1/admin/trash-libraries/{library_id}/", method=METH_DELETE)

    async def clean_admin_trash_libraries(self, *, owner: str | None = None) -> None:
        """Permanently delete all libraries in the trash, or only those of `owner`."""
        await self._request("api/v2.1/admin/trash-libraries/", method=METH_DELETE, data=_without_none({"owner": owner}))

    async def get_admin_devices(self, *, platform: AdminDevicePlatform | None = None, per_page: int = 50) -> list[AdminDevice]:
        """Return all linked client devices, optionally only desktop or mobile ones."""
        params = _without_none({"platform": platform})
        items = await self._get_admin_pages("api/v2.1/admin/devices/", "devices", per_page=per_page, params=params)
        return [AdminDevice.from_dict(item) for item in items]

    async def delete_admin_device(self, user: str, platform: str, device_id: str, *, wipe: bool = False) -> None:
        """Unlink a device, revoking its token.

        Args:
        ----
            user: The device's user.
            platform: The device's platform, as in `AdminDevice.platform`.
            device_id: The device id.
            wipe: Also ask the client to delete its local data.

        """
        form = {"user": user, "platform": platform, "device_id": device_id, "wipe_device": _bool(wipe)}
        await self._request("api/v2.1/admin/devices/", method=METH_DELETE, data=form)

    async def get_admin_device_errors(self, *, per_page: int = 100) -> list[AdminDeviceError]:
        """Return the sync errors reported by clients (Pro)."""
        items = await self._get_admin_pages("api/v2.1/admin/device-errors/", "device_errors", per_page=per_page)
        return [AdminDeviceError.from_dict(item) for item in items]

    async def delete_admin_device_errors(self) -> None:
        """Clear all reported sync errors (Pro)."""
        await self._request("api/v2.1/admin/device-errors/", method=METH_DELETE)

    async def get_admin_share_links(self, *, order_by: str | None = None, direction: str | None = None, per_page: int = 100) -> list[AdminShareLink]:
        """Return all share links.

        Args:
        ----
            order_by: `ctime` (default) or `view_cnt`.
            direction: `desc` (default) or `asc`.
            per_page: Page size used while fetching.

        """
        params = _without_none({"order_by": order_by, "direction": direction})
        items = await self._get_admin_counted_pages("api/v2.1/admin/share-links/", "share_link_list", "count", per_page=per_page, params=params)
        return [AdminShareLink.from_dict(item) for item in items]

    async def get_admin_share_link(self, token: str) -> AdminShareLink:
        """Return one share link with its library, path and permissions."""
        return AdminShareLink.from_dict(await self._request(f"api/v2.1/admin/share-links/{token}/"))

    async def delete_admin_share_link(self, token: str) -> None:
        """Delete a share link."""
        await self._request(f"api/v2.1/admin/share-links/{token}/", method=METH_DELETE)

    async def get_admin_upload_links(
        self, *, order_by: str | None = None, direction: str | None = None, per_page: int = 100
    ) -> list[AdminUploadLink]:
        """Return all upload links; `order_by` is `ctime` or `view_cnt`, `direction` `desc` or `asc`."""
        params = _without_none({"order_by": order_by, "direction": direction})
        items = await self._get_admin_counted_pages("api/v2.1/admin/upload-links/", "upload_link_list", "count", per_page=per_page, params=params)
        return [AdminUploadLink.from_dict(item) for item in items]

    async def get_admin_upload_link(self, token: str) -> AdminUploadLink:
        """Return one upload link with its library."""
        return AdminUploadLink.from_dict(await self._request(f"api/v2.1/admin/upload-links/{token}/"))

    async def delete_admin_upload_link(self, token: str) -> None:
        """Delete an upload link."""
        await self._request(f"api/v2.1/admin/upload-links/{token}/", method=METH_DELETE)

    async def get_admin_groups(self, *, per_page: int = 100) -> list[AdminGroup]:
        """Return all groups (without organization groups)."""
        items = await self._get_admin_pages("api/v2.1/admin/groups/", "groups", per_page=per_page)
        return [AdminGroup.from_dict(item) for item in items]

    async def search_admin_groups(self, name: str) -> list[AdminGroup]:
        """Return the groups whose name contains `name`."""
        result = await self._request("api/v2.1/admin/groups/", params={"name": name})
        return [AdminGroup.from_dict(item) for item in result["groups"]]

    async def create_admin_group(self, name: str, *, owner: str | None = None) -> AdminGroup:
        """Create a group, owned by `owner` or the admin."""
        form = _without_none({"group_name": name, "group_owner": owner})
        return AdminGroup.from_dict(await self._request("api/v2.1/admin/groups/", method=METH_POST, data=form))

    async def update_admin_group(
        self,
        group_id: int,
        *,
        name: str | None = None,
        owner: str | None = None,
        quota: int | None = None,
    ) -> AdminGroup:
        """Rename a group, transfer it to another owner or set its quota.

        Args:
        ----
            group_id: The group.
            name: New name.
            owner: New owner; transfers the group.
            quota: Quota in bytes, or -2 for unlimited (Pro).

        """
        form = _without_none({"name": name, "new_owner": owner, "quota": quota})
        return AdminGroup.from_dict(await self._request(f"api/v2.1/admin/groups/{group_id}/", method=METH_PUT, data=form))

    async def delete_admin_group(self, group_id: int) -> None:
        """Delete a group."""
        await self._request(f"api/v2.1/admin/groups/{group_id}/", method=METH_DELETE)

    async def get_admin_login_logs(self, *, emails: list[str] | None = None, page: int = 1, per_page: int = 100) -> list[AdminLoginLog]:
        """Return one page of login attempts, newest first (Pro)."""
        params = _without_none({"email": emails, "page": page, "per_page": per_page})
        result = await self._request("api/v2.1/admin/logs/login-logs/", params=params)
        return [AdminLoginLog.from_dict(item) for item in result["login_log_list"]]

    async def get_admin_file_access_logs(
        self,
        *,
        emails: list[str] | None = None,
        library_ids: list[str] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[AdminFileAccessLog]:
        """Return one page of file accesses, newest first (Pro)."""
        params = _without_none({"email": emails, "repo": library_ids, "page": page, "per_page": per_page})
        result = await self._request("api/v2.1/admin/logs/file-access-logs/", params=params)
        return [AdminFileAccessLog.from_dict(item) for item in result["file_access_log_list"]]

    async def get_admin_file_update_logs(
        self,
        *,
        emails: list[str] | None = None,
        library_ids: list[str] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[AdminFileUpdateLog]:
        """Return one page of file changes, newest first (Pro)."""
        params = _without_none({"email": emails, "repo": library_ids, "page": page, "per_page": per_page})
        result = await self._request("api/v2.1/admin/logs/file-update-logs/", params=params)
        return [AdminFileUpdateLog.from_dict(item) for item in result["file_update_log_list"]]

    async def get_admin_share_permission_logs(  # pylint: disable=too-many-arguments
        self,
        *,
        from_emails: list[str] | None = None,
        to_emails: list[str] | None = None,
        to_groups: list[str] | None = None,
        library_ids: list[str] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[AdminSharePermissionLog]:
        """Return one page of share permission changes, newest first (Pro)."""
        params = _without_none(
            {
                "from_email": from_emails,
                "to_email": to_emails,
                "to_group": to_groups,
                "repo": library_ids,
                "page": page,
                "per_page": per_page,
            }
        )
        result = await self._request("api/v2.1/admin/logs/share-permission-logs/", params=params)
        return [AdminSharePermissionLog.from_dict(item) for item in result["share_permission_log_list"]]

    async def get_admin_permission_audit(self, start: date, end: date) -> list[AdminPermissionAuditLog]:
        """Return the legacy permission audit log between two days, inclusive (Pro)."""
        params = {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")}
        result = await self._request("api/v2.1/admin/logs/perm-audit/", params=params)
        return [AdminPermissionAuditLog.from_dict(item) for item in result]

    async def get_admin_notifications(self, *, username: str | None = None, page: int = 1, per_page: int = 100) -> list[AdminNotification]:
        """Return one page of the notifications sent to all users, or to `username`."""
        params = _without_none({"username": username, "page": page, "per_page": per_page})
        result = await self._request("api/v2.1/admin/notifications/", params=params)
        return [AdminNotification.from_dict(item) for item in result["notification_list"]]

    async def get_admin_system_notifications(self) -> list[AdminSystemNotification]:
        """Return the system banners."""
        result = await self._request("api/v2.1/admin/sys-notifications/")
        return [AdminSystemNotification.from_dict(item) for item in result["notifications"]]

    async def create_admin_system_notification(self, msg: str) -> AdminSystemNotification:
        """Create a system banner; make it current to show it."""
        result = await self._request("api/v2.1/admin/sys-notifications/", method=METH_POST, data={"msg": msg})
        return AdminSystemNotification.from_dict(result["notification"])

    async def set_admin_current_system_notification(self, notification_id: int) -> AdminSystemNotification:
        """Show a system banner to all users, replacing the current one."""
        result = await self._request(f"api/v2.1/admin/sys-notifications/{notification_id}/", method=METH_PUT)
        return AdminSystemNotification.from_dict(result["notification"])

    async def delete_admin_system_notification(self, notification_id: int) -> None:
        """Delete a system banner."""
        await self._request(f"api/v2.1/admin/sys-notifications/{notification_id}/", method=METH_DELETE)

    async def get_admin_user_notifications(self, *, per_page: int = 100) -> list[AdminUserNotification]:
        """Return all announcements sent to individual users, newest first."""
        items = await self._get_admin_counted_pages("api/v2.1/admin/sys-user-notifications/", "notifications", "total_count", per_page=per_page)
        return [AdminUserNotification.from_dict(item) for item in items]

    async def create_admin_user_notification(self, msg: str, username: str) -> AdminUserNotification:
        """Send an announcement to one user; it shows until they dismiss it."""
        result = await self._request("api/v2.1/admin/sys-user-notifications/", method=METH_POST, data={"msg": msg, "username": username})
        return AdminUserNotification.from_dict(result["notification"])

    async def delete_admin_user_notification(self, notification_id: int) -> None:
        """Delete an announcement."""
        await self._request(f"api/v2.1/admin/sys-user-notifications/{notification_id}/", method=METH_DELETE)
