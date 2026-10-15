"""Asynchronous Python client for Seafile."""

from aioseafile.endpoints.account import AccountMixin
from aioseafile.endpoints.admin import AdminMixin
from aioseafile.endpoints.extras import ExtrasMixin
from aioseafile.endpoints.files import FilesMixin
from aioseafile.endpoints.groups import GroupsMixin
from aioseafile.endpoints.libraries import LibrariesMixin
from aioseafile.endpoints.sharing import SharingMixin


class Seafile(  # pylint: disable=too-many-ancestors
    AccountMixin,
    LibrariesMixin,
    FilesMixin,
    SharingMixin,
    GroupsMixin,
    AdminMixin,
    ExtrasMixin,
):
    """Client for the Seafile Web API."""
