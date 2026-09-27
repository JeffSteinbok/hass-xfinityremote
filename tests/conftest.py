"""Shared fixtures."""

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.xfinity_remote.api import PairingSession

DEVICE_ID = "xbo-device-123"


def make_token(device_id: str = DEVICE_ID, refresh_ms: int = 2998000, nonce: int = 0) -> str:
    """Build an unsigned JWT shaped like a real arToken."""
    def b64(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    claims = {
        "idToken": "id",
        "partner": "comcast",
        "clientDeviceId": "client-1",
        "xboAccountId": "acct-1",
        "xboDeviceId": device_id,
        "refreshIntervalMs": refresh_ms,
        "iat": 1790536227 + nonce,
        "exp": 1806088227 + nonce,
        "iss": "test",
    }
    return f"{b64({'alg': 'HS256'})}.{b64(claims)}.sig"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    yield


@pytest.fixture(autouse=True)
def fast_pairing():
    """Don't actually wait between pairing polls."""
    with patch("custom_components.xfinity_remote.config_flow.PAIRING_POLL_SECONDS", 0):
        yield


@pytest.fixture
def mock_client():
    """Patch every XfinityRemoteClient API method."""
    base = "custom_components.xfinity_remote.api.XfinityRemoteClient"
    refreshed = make_token(nonce=1)

    async def _refresh(self):
        self.token = refreshed
        return refreshed

    with (
        patch(f"{base}.start_pairing", AsyncMock(return_value=PairingSession("1234567", "pair-tok", "client-1"))) as start,
        patch(f"{base}.confirm_pairing", AsyncMock(return_value=make_token())) as confirm,
        patch(f"{base}.refresh_token", autospec=True, side_effect=_refresh) as refresh,
        patch(f"{base}.get_devices", AsyncMock(return_value=[{"id": DEVICE_ID, "name": "Family Room"}])) as devices,
        patch(f"{base}.send_key", AsyncMock()) as send_key,
        patch(f"{base}.send_cec_key", AsyncMock()) as send_cec_key,
        patch(f"{base}.send_text", AsyncMock()) as send_text,
    ):
        yield type("Mocks", (), {
            "start_pairing": start, "confirm_pairing": confirm, "refresh_token": refresh,
            "get_devices": devices, "send_key": send_key, "send_cec_key": send_cec_key,
            "send_text": send_text, "refreshed": refreshed,
        })
