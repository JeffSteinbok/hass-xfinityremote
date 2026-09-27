"""Async client for the Xfinity Web Remote API (remote.xfinity.com).

This module has no Home Assistant dependencies so it can be tested on its own.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://remote.xfinity.com"
DEFAULT_PARTNER = "comcast"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)

# Status strings the server returns in error bodies when a token is no longer usable.
EXPIRED_TOKEN_STATUSES = {"EXPIRED-XAPI-TOKEN", "EXPIRED-EASYPAIR-TOKEN"}

# Button id on the web remote -> vcode sent to /api/v1/processKey.
KEYS: dict[str, str] = {
    "up": "UP",
    "down": "DOWN",
    "left": "LEFT",
    "right": "RIGHT",
    "ok": "ENTER",
    "exit": "EXIT",
    "last": "PREV",
    "menu": "MENU",
    "guide": "GUIDE",
    "info": "INFO",
    "page_up": "PAGE_UP",
    "page_down": "PAGE_DOWN",
    "channel_up": "CHANNEL_UP",
    "channel_down": "CHANNEL_DOWN",
    "play_pause": "PLAY",
    "rewind": "REWIND",
    "fast_forward": "FAST_FORWARD",
    "replay": "REPLAY",
    "record": "RECORD",
    "voice": "VOICE",
    "key_a": "COLOR_KEY_0",
    "key_b": "COLOR_KEY_1",
    "key_c": "COLOR_KEY_2",
    "key_d": "COLOR_KEY_3",
    **{f"number_{n}": f"NUMBER_{n}" for n in range(10)},
}

# TV keys are sent over HDMI-CEC via /api/v1/processCecKey as (key, value).
CEC_KEYS: dict[str, tuple[str, str]] = {
    "tv_power_off": ("POWER", "OFF"),
    "tv_mute": ("MUTE", "ON"),
    "tv_input": ("INPUT", "STB_INPUT"),
    "volume_up": ("VOLUME", "UP"),
    "volume_down": ("VOLUME", "DOWN"),
}

VCODES = frozenset(KEYS.values())


class XfinityRemoteError(Exception):
    """Generic API failure."""


class XfinityRemoteAuthError(XfinityRemoteError):
    """The token was rejected; the user has to pair again."""


@dataclass
class PairingSession:
    """An in-progress EasyPair pairing."""

    code: str
    token: str
    client_device_id: str
    expires: Any = None


@dataclass
class TokenInfo:
    """Fields decoded from an arToken (a JWT) without verifying it."""

    xbo_device_id: str | None
    xbo_account_id: str | None
    client_device_id: str | None
    partner: str | None
    refresh_interval_ms: int | None
    expires_at: int | None


def decode_token(token: str) -> TokenInfo:
    """Read the claims of an arToken. The signature is not (and cannot be) checked."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError) as err:
        raise XfinityRemoteAuthError("Token is not a valid JWT") from err

    return TokenInfo(
        xbo_device_id=claims.get("xboDeviceId"),
        xbo_account_id=claims.get("xboAccountId"),
        client_device_id=claims.get("clientDeviceId"),
        partner=claims.get("partner"),
        refresh_interval_ms=claims.get("refreshIntervalMs"),
        expires_at=claims.get("exp"),
    )


class XfinityRemoteClient:
    """Thin wrapper around the remote.xfinity.com JSON API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str | None = None,
        *,
        partner: str = DEFAULT_PARTNER,
        base_url: str = BASE_URL,
    ) -> None:
        self._session = session
        self.token = token
        self.partner = partner
        self._base_url = base_url

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        token: str | None = None,
        timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    ) -> tuple[int, Any]:
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                data=json.dumps(body) if body is not None else None,
                timeout=timeout,
            ) as resp:
                text = await resp.text()
                data: Any = None
                if text:
                    try:
                        data = json.loads(text)
                    except ValueError:
                        data = text
                status = resp.status
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise XfinityRemoteError(f"{method} {path} failed: {err}") from err

        if status == 401 or (isinstance(data, dict) and data.get("status") in EXPIRED_TOKEN_STATUSES):
            raise XfinityRemoteAuthError(f"{method} {path} rejected the token ({status})")
        if status >= 400:
            raise XfinityRemoteError(f"{method} {path} returned {status}: {data}")

        return status, data

    def _require_token(self) -> str:
        if not self.token:
            raise XfinityRemoteAuthError("No token; pair first")
        return self.token

    # --- Pairing ---------------------------------------------------------

    async def start_pairing(self, client_device_id: str) -> PairingSession:
        """Ask the server for a 7-digit EasyPair code to enter on the TV."""
        _, data = await self._request(
            "POST",
            "/api/v1/pairing/start",
            body={"partner": self.partner, "clientDeviceId": client_device_id},
        )
        if not isinstance(data, dict) or not data.get("token") or not data.get("pairingCode"):
            raise XfinityRemoteError(f"Unexpected pairing response: {data}")
        return PairingSession(
            code=str(data["pairingCode"]),
            token=data["token"],
            client_device_id=client_device_id,
            expires=data.get("exp"),
        )

    async def confirm_pairing(self, pairing: PairingSession) -> str | None:
        """Poll once. Returns the arToken when the TV confirmed, otherwise None."""
        status, data = await self._request(
            "POST",
            "/api/v1/pairing/confirm",
            body={"partner": self.partner, "clientDeviceId": pairing.client_device_id},
            token=pairing.token,
        )
        if status == 200 and isinstance(data, dict) and data.get("status") == "CONFIRMED":
            self.token = data["arToken"]
            return self.token
        return None

    # --- Token lifecycle -------------------------------------------------

    async def refresh_token(self) -> str:
        """Trade the current token for a fresh one. Updates self.token."""
        _, data = await self._request(
            "POST", "/api/v1/auth/token/refresh", token=self._require_token()
        )
        if not isinstance(data, dict) or not data.get("arToken"):
            raise XfinityRemoteAuthError(f"Unexpected refresh response: {data}")
        self.token = data["arToken"]
        return self.token

    async def get_devices(self) -> list[dict[str, Any]]:
        """List the set-top boxes on the account ([{id, name}, ...])."""
        _, data = await self._request("POST", "/api/v1/devices", token=self._require_token())
        return (data or {}).get("devices", []) if isinstance(data, dict) else []

    async def get_version(self) -> str | None:
        """Server version; a cheap authenticated call used to validate a token."""
        _, data = await self._request("GET", "/api/v1/version", token=self._require_token())
        return data.get("version") if isinstance(data, dict) else None

    # --- Commands --------------------------------------------------------

    async def send_key(self, vcode: str) -> None:
        """Press a set-top box button, e.g. "GUIDE" or "NUMBER_7"."""
        await self._request(
            "POST",
            "/api/v1/processKey",
            body={"vcode": vcode},
            token=self._require_token(),
            timeout=aiohttp.ClientTimeout(total=5),
        )

    async def send_cec_key(self, key: str, value: str) -> None:
        """Send an HDMI-CEC command to the TV, e.g. ("VOLUME", "UP")."""
        await self._request(
            "POST",
            "/api/v1/processCecKey",
            body={"key": key, "value": value},
            token=self._require_token(),
            timeout=aiohttp.ClientTimeout(total=5),
        )

    async def send_text(self, command: str) -> None:
        """Send a typed voice-style command, e.g. "watch ESPN"."""
        # This endpoint takes the token in the body rather than the Authorization header.
        await self._request(
            "POST",
            "/api/v1/text",
            body={"cmd": command, "arToken": self._require_token()},
        )
