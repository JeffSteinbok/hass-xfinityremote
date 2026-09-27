"""The Xfinity Remote integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .api import (
    XfinityRemoteAuthError,
    XfinityRemoteClient,
    XfinityRemoteError,
    decode_token,
)
from .const import CONF_DEVICE_NAME, CONF_TOKEN, DEFAULT_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.REMOTE]


@dataclass
class XfinityRemoteData:
    """Runtime state shared by the platforms."""

    client: XfinityRemoteClient
    device_id: str
    device_name: str


type XfinityRemoteConfigEntry = ConfigEntry[XfinityRemoteData]


async def async_setup_entry(hass: HomeAssistant, entry: XfinityRemoteConfigEntry) -> bool:
    """Set up Xfinity Remote from a config entry."""
    client = XfinityRemoteClient(async_get_clientsession(hass), entry.data[CONF_TOKEN])

    # Refreshing on startup both validates the token and resets its clock.
    try:
        await client.refresh_token()
    except XfinityRemoteAuthError as err:
        raise ConfigEntryAuthFailed("Xfinity rejected the saved token; pair again") from err
    except XfinityRemoteError as err:
        raise ConfigEntryNotReady(str(err)) from err

    _async_save_token(hass, entry, client.token)

    info = decode_token(client.token)
    entry.runtime_data = XfinityRemoteData(
        client=client,
        device_id=info.xbo_device_id or entry.unique_id,
        device_name=entry.data.get(CONF_DEVICE_NAME) or "Xfinity",
    )

    interval = (
        timedelta(milliseconds=info.refresh_interval_ms)
        if info.refresh_interval_ms
        else DEFAULT_REFRESH_INTERVAL
    )

    async def _async_refresh(_now: datetime) -> None:
        try:
            await client.refresh_token()
        except XfinityRemoteAuthError:
            _LOGGER.warning("Xfinity token refresh was rejected; re-pairing is required")
            entry.async_start_reauth(hass)
            return
        except XfinityRemoteError as err:
            # Transient; the token is good for months, so just try again next interval.
            _LOGGER.warning("Xfinity token refresh failed: %s", err)
            return
        _async_save_token(hass, entry, client.token)

    entry.async_on_unload(async_track_time_interval(hass, _async_refresh, interval))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: XfinityRemoteConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


@callback
def _async_save_token(hass: HomeAssistant, entry: ConfigEntry, token: str | None) -> None:
    """Persist a refreshed token so it survives restarts."""
    if token and token != entry.data.get(CONF_TOKEN):
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_TOKEN: token})
