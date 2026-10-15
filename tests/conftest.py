"""Conftest for the aioseafile tests."""

from typing import TYPE_CHECKING

import pytest
from aiohttp import ClientSession
from syrupy.assertion import SnapshotAssertion

from aioseafile import Seafile

from .syrupy import SeafileSnapshotExtension

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture(name="snapshot")
def snapshot_assertion(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Seafile extension."""
    return snapshot.use_extension(SeafileSnapshotExtension)


@pytest.fixture(name="seafile_client")
async def client() -> AsyncGenerator[Seafile]:
    """Return an aioseafile client."""
    async with (
        ClientSession() as session,
        Seafile(
            api_url="http://localhost:8000",
            token="test_token",
            session=session,
            max_retries=0,
        ) as seafile_client,
    ):
        yield seafile_client
