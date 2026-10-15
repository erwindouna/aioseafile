"""Server and account endpoints."""

from typing import Any

from aiohttp import FormData
from aiohttp.hdrs import METH_DELETE, METH_POST, METH_PUT

from aioseafile.client import SeafileClient
from aioseafile.models.account import (
    AccountInfo,
    Activity,
    AllNotifications,
    Device,
    Invitation,
    InvitationBatchResult,
    InvitationType,
    Notifications,
    SearchedUser,
    ServerInfo,
    SystemNotification,
    UserAvatar,
    UserProfile,
)


def _form(**fields: Any) -> dict[str, str]:
    """Build form data from the given fields, leaving out unset ones."""
    return {key: str(value).lower() if isinstance(value, bool) else str(value) for key, value in fields.items() if value is not None}


class AccountMixin(SeafileClient):  # pylint: disable=too-many-public-methods
    """Server and account endpoints."""

    async def ping(self) -> bool:
        """Return whether the server is reachable, without authentication."""
        result: str = await self._request("api2/ping/", authenticated=False)
        return result == "pong"

    async def auth_ping(self) -> bool:
        """Return whether the token is valid."""
        result: str = await self._request("api2/auth/ping/")
        return result == "pong"

    async def get_server_info(self) -> ServerInfo:
        """Return the server version and features, without authentication."""
        return ServerInfo.from_dict(await self._request("api2/server-info/", authenticated=False))

    async def get_account_info(self) -> AccountInfo:
        """Return the account details and quota."""
        return AccountInfo.from_dict(await self._request("api2/account/info/"))

    async def update_account_info(
        self,
        *,
        name: str | None = None,
        file_updates_email_interval: int | None = None,
        collaborate_email_interval: int | None = None,
    ) -> AccountInfo:
        """Update the account name and email notification intervals, and return the account details.

        Args:
        ----
            name: New display name (at most 64 characters, no '/').
            file_updates_email_interval: Seconds between file update emails; 0 disables them.
            collaborate_email_interval: Seconds between collaboration emails; 0 disables them.

        """
        form = _form(name=name, file_updates_email_interval=file_updates_email_interval, collaborate_email_interval=collaborate_email_interval)
        return AccountInfo.from_dict(await self._request("api2/account/info/", method=METH_PUT, data=form))

    async def get_user_profile(self) -> UserProfile:
        """Return the profile of the account."""
        return UserProfile.from_dict(await self._request("api/v2.1/user/"))

    async def update_user_profile(
        self,
        *,
        name: str | None = None,
        contact_email: str | None = None,
        telephone: str | None = None,
        list_in_address_book: bool | None = None,
    ) -> UserProfile:
        """Update the profile of the account and return it.

        Each field needs the matching server setting (for example ENABLE_USER_SET_CONTACT_EMAIL);
        a disabled one raises SeafilePermissionError. Empty values are ignored by the server.
        """
        form = _form(name=name, contact_email=contact_email, telephone=telephone, list_in_address_book=list_in_address_book)
        return UserProfile.from_dict(await self._request("api/v2.1/user/", method=METH_PUT, data=form))

    async def change_password(self, old_password: str, new_password: str) -> None:
        """Change the password of the account.

        Args:
        ----
            old_password: Current password.
            new_password: New password; it must be strong or very strong.

        """
        await self._request(
            "api/v2.1/user/reset-password/",
            method=METH_POST,
            data={"old_password": old_password, "new_password": new_password},
            retry=False,
        )

    async def get_client_login_token(self) -> str | None:
        """Return a one-time token to log in to the web interface, valid for 30 seconds.

        Returns None when the account uses two-factor authentication.
        """
        result: dict[str, str] = await self._request("api2/client-login/", method=METH_POST, retry=False)
        return result.get("token")

    async def logout_device(self) -> None:
        """Revoke the token this client uses; the client can't make authenticated requests afterwards."""
        await self._request("api2/logout-device/", method=METH_POST, retry=False)
        self._token = None

    async def search_users(self, query: str, *, include_self: bool = True) -> list[SearchedUser]:
        """Search users by email, name, contact email or login ID (at most 10 results).

        Args:
        ----
            query: Text to search for.
            include_self: Whether the account itself may appear in the results.

        """
        result = await self._request("api2/search-user/", params={"q": query, "include_self": int(include_self)})
        return [SearchedUser.from_dict(item) for item in result["users"]]

    async def get_user_avatar(self, email: str, size: int = 80) -> UserAvatar:
        """Return the avatar of a user.

        Args:
        ----
            email: Seafile user ID of the user (the `email` field, not the contact email).
            size: Size of the resized avatar in pixels.

        """
        return UserAvatar.from_dict(await self._request(f"api2/avatars/user/{email}/resized/{size}/"))

    async def upload_avatar(self, content: bytes, filename: str, *, content_type: str = "image/png") -> str:
        """Upload a new avatar for the account and return its URL.

        Args:
        ----
            content: Image data.
            filename: File name; the extension must be one the server allows (png, jpg, jpeg, gif by default).
            content_type: MIME type of the image.

        """
        form = FormData()
        form.add_field("avatar", content, filename=filename, content_type=content_type)
        result = await self._request("api/v2.1/user-avatar/", method=METH_POST, data=form, retry=False)
        avatar_url: str = result["avatar_url"]
        return avatar_url

    async def get_devices(self) -> list[Device]:
        """Return the desktop and mobile clients linked to the account."""
        return [Device.from_dict(item) for item in await self._request("api2/devices/")]

    async def unlink_device(self, platform: str, device_id: str, *, wipe: bool = False) -> None:
        """Unlink a device from the account.

        Args:
        ----
            platform: Platform of the device, for example 'linux' or 'android'.
            device_id: ID of the device.
            wipe: Also remove the synced data from the device the next time it connects.

        """
        form = {"platform": platform, "device_id": device_id, "wipe_device": str(wipe).lower()}
        await self._request("api2/devices/", method=METH_DELETE, data=form)

    async def get_activities(self, *, page: int = 1, per_page: int = 25, op_user: str | None = None) -> list[Activity]:
        """Return one page of file activities in the libraries the account can access, newest first.

        Needs the events service; servers without it raise SeafileNotFoundError.

        Args:
        ----
            page: Page number, starting at 1.
            per_page: Number of activities per page.
            op_user: Only return activities by this user.

        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if op_user is not None:
            params["op_user"] = op_user
        result = await self._request("api/v2.1/activities/", params=params)
        return [Activity.from_dict(item) for item in result["events"]]

    async def get_notifications(self, *, page: int = 1, per_page: int = 25) -> Notifications:
        """Return one page of general notifications, newest first."""
        return Notifications.from_dict(await self._request("api/v2.1/notifications/", params={"page": page, "per_page": per_page}))

    async def mark_notifications_seen(self) -> None:
        """Mark all general notifications as seen."""
        await self._request("api/v2.1/notifications/", method=METH_PUT)

    async def mark_notification_seen(self, notification_id: int) -> None:
        """Mark a general notification as seen."""
        await self._request("api/v2.1/notification/", method=METH_PUT, data={"notice_id": str(notification_id)})

    async def delete_notifications(self) -> None:
        """Delete all general notifications."""
        await self._request("api/v2.1/notifications/", method=METH_DELETE)

    async def get_sdoc_notifications(self, *, page: int = 1, per_page: int = 25) -> Notifications:
        """Return one page of SeaDoc (discussion) notifications, newest first."""
        return Notifications.from_dict(await self._request("api/v2.1/sdoc-notifications/", params={"page": page, "per_page": per_page}))

    async def mark_sdoc_notifications_seen(self) -> None:
        """Mark all SeaDoc notifications as seen."""
        await self._request("api/v2.1/sdoc-notifications/", method=METH_PUT)

    async def mark_sdoc_notification_seen(self, notification_id: int) -> None:
        """Mark a SeaDoc notification as seen."""
        await self._request("api/v2.1/sdoc-notification/", method=METH_PUT, data={"notice_id": str(notification_id)})

    async def delete_sdoc_notifications(self) -> None:
        """Delete all SeaDoc notifications."""
        await self._request("api/v2.1/sdoc-notifications/", method=METH_DELETE)

    async def get_all_notifications(self, *, page: int = 1, per_page: int = 25) -> AllNotifications:
        """Return one page of both general and SeaDoc notifications, with the unseen counts."""
        return AllNotifications.from_dict(await self._request("api/v2.1/all-notifications/", params={"page": page, "per_page": per_page}))

    async def mark_all_notifications_seen(self) -> None:
        """Mark all general and SeaDoc notifications as seen."""
        await self._request("api/v2.1/all-notifications/", method=METH_PUT)

    async def get_unseen_system_notifications(self) -> list[SystemNotification]:
        """Return the messages from admins that the account hasn't seen yet."""
        result = await self._request("api/v2.1/sys-user-notifications/unseen/")
        return [SystemNotification.from_dict(item) for item in result["notifications"]]

    async def mark_system_notification_seen(self, notification_id: int) -> SystemNotification:
        """Mark a message from an admin as seen and return it."""
        result = await self._request(f"api/v2.1/sys-user-notifications/{notification_id}/seen/", method=METH_PUT)
        return SystemNotification.from_dict(result["notification"])

    async def get_invitations(self) -> list[Invitation]:
        """Return the guest invitations the account sent; needs ENABLE_GUEST_INVITATION on the server."""
        return [Invitation.from_dict(item) for item in await self._request("api/v2.1/invitations/")]

    async def get_invitation(self, token: str) -> Invitation:
        """Return a guest invitation the account sent."""
        return Invitation.from_dict(await self._request(f"api/v2.1/invitations/{token}/"))

    async def create_invitation(self, email: str) -> Invitation:
        """Invite a guest by email."""
        result = await self._request(
            "api/v2.1/invitations/",
            method=METH_POST,
            data={"type": InvitationType.GUEST.value, "accepter": email},
            retry=False,
        )
        return Invitation.from_dict(result)

    async def create_invitations(self, emails: list[str]) -> InvitationBatchResult:
        """Invite several guests by email; failures are reported per address instead of raised."""
        form = [("type", InvitationType.GUEST.value), *(("accepter", email) for email in emails)]
        return InvitationBatchResult.from_dict(await self._request("api/v2.1/invitations/batch/", method=METH_POST, data=form, retry=False))

    async def delete_invitation(self, token: str) -> None:
        """Delete a guest invitation that hasn't been accepted yet."""
        await self._request(f"api/v2.1/invitations/{token}/", method=METH_DELETE)

    async def revoke_invitation(self, token: str) -> None:
        """Revoke an accepted guest invitation; this deactivates the guest account."""
        await self._request(f"api/v2.1/invitations/{token}/revoke/", method=METH_POST)
