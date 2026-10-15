"""Diagnostics for Xfinity Remote. The token and account/device identifiers are redacted."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import XfinityRemoteConfigEntry
from .api import XfinityRemoteAuthError, decode_token
from .const import CONF_TOKEN

TO_REDACT = {CONF_TOKEN, "device_id", "xbo_device_id", "xbo_account_id", "client_device_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: XfinityRemoteConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = entry.runtime_data
    token: dict[str, Any] | str
    try:
        token = asdict(decode_token(runtime.client.token or ""))
    except XfinityRemoteAuthError:
        token = "unreadable"
    else:
        if token["expires_at"]:
            token["expires_at"] = datetime.fromtimestamp(token["expires_at"], timezone.utc).isoformat()

    return async_redact_data(
        {
            "entry": {"title": entry.title, "data": dict(entry.data)},
            "device_id": runtime.device_id,
            "device_name": runtime.device_name,
            "token_claims": token,
        },
        TO_REDACT,
    )
