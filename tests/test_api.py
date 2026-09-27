"""API client tests against a mocked HTTP layer."""

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.xfinity_remote.api import (
    BASE_URL,
    PairingSession,
    XfinityRemoteAuthError,
    XfinityRemoteClient,
    XfinityRemoteError,
    decode_token,
)

from .conftest import DEVICE_ID, make_token


def test_decode_token() -> None:
    info = decode_token(make_token())
    assert info.xbo_device_id == DEVICE_ID
    assert info.refresh_interval_ms == 2998000
    with pytest.raises(XfinityRemoteAuthError):
        decode_token("not-a-jwt")


async def test_send_key_request_shape() -> None:
    async with aiohttp.ClientSession() as session:
        client = XfinityRemoteClient(session, "tok")
        with aioresponses() as mock:
            mock.post(f"{BASE_URL}/api/v1/processKey", payload={})
            await client.send_key("GUIDE")
            (req,) = mock.requests.values()
            assert req[0].kwargs["headers"]["Authorization"] == "Bearer tok"
            assert req[0].kwargs["data"] == '{"vcode": "GUIDE"}'


async def test_send_text_puts_token_in_body() -> None:
    async with aiohttp.ClientSession() as session:
        client = XfinityRemoteClient(session, "tok")
        with aioresponses() as mock:
            mock.post(f"{BASE_URL}/api/v1/text", body="")
            await client.send_text("watch ESPN")
            (req,) = mock.requests.values()
            assert "Authorization" not in req[0].kwargs["headers"]
            assert req[0].kwargs["data"] == '{"cmd": "watch ESPN", "arToken": "tok"}'


async def test_pairing_pending_then_confirmed() -> None:
    async with aiohttp.ClientSession() as session:
        client = XfinityRemoteClient(session)
        pairing = PairingSession("1234567", "pair-tok", "client-1")
        with aioresponses() as mock:
            mock.post(f"{BASE_URL}/api/v1/pairing/confirm", status=202, payload={"status": "PENDING"})
            mock.post(f"{BASE_URL}/api/v1/pairing/confirm", payload={"status": "CONFIRMED", "arToken": "ar"})
            assert await client.confirm_pairing(pairing) is None
            assert await client.confirm_pairing(pairing) == "ar"
            assert client.token == "ar"


async def test_refresh_updates_token() -> None:
    async with aiohttp.ClientSession() as session:
        client = XfinityRemoteClient(session, "old")
        with aioresponses() as mock:
            mock.post(f"{BASE_URL}/api/v1/auth/token/refresh", payload={"arToken": "new", "refreshIntervalMs": 1})
            assert await client.refresh_token() == "new"
            assert client.token == "new"


@pytest.mark.parametrize(
    ("status", "payload", "error"),
    [
        (401, {}, XfinityRemoteAuthError),
        (500, {"status": "EXPIRED-XAPI-TOKEN"}, XfinityRemoteAuthError),
        (500, {"msg": "boom"}, XfinityRemoteError),
    ],
)
async def test_error_mapping(status, payload, error) -> None:
    async with aiohttp.ClientSession() as session:
        client = XfinityRemoteClient(session, "tok")
        with aioresponses() as mock:
            mock.post(f"{BASE_URL}/api/v1/processKey", status=status, payload=payload)
            with pytest.raises(error):
                await client.send_key("OK")


async def test_no_token() -> None:
    async with aiohttp.ClientSession() as session:
        with pytest.raises(XfinityRemoteAuthError):
            await XfinityRemoteClient(session).send_key("OK")
