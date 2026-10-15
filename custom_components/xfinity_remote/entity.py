"""Base entity for Xfinity Remote."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from . import XfinityRemoteConfigEntry, async_save_token
from .api import XfinityRemoteAuthError, XfinityRemoteError
from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


class XfinityRemoteEntity(Entity):
    """Common device info and error handling."""

    _attr_has_entity_name = True

    def __init__(self, entry: XfinityRemoteConfigEntry) -> None:
        self._entry = entry
        self._client = entry.runtime_data.client
        device_id = entry.runtime_data.device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=entry.runtime_data.device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
        self._device_id = device_id

    async def _async_call(self, call: Callable[[], Awaitable[None]]) -> None:
        """Run an API call, turning failures into Home Assistant errors.

        Xfinity sometimes rejects a command while the token is still good (e.g. while its
        backend is timing out). So a rejected command only leads to re-pairing if
        refreshing the token is rejected too; otherwise the command is retried once.
        """
        try:
            await call()
            return
        except XfinityRemoteAuthError as err:
            _LOGGER.warning("Xfinity rejected a command; refreshing the token and retrying: %s", err)
        except XfinityRemoteError as err:
            raise HomeAssistantError(f"Xfinity command failed: {err}") from err

        try:
            await self._client.refresh_token()
        except XfinityRemoteAuthError as err:
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError("Xfinity rejected the token; re-pair the remote") from err
        except XfinityRemoteError as err:
            raise HomeAssistantError(f"Xfinity command failed: {err}") from err
        async_save_token(self.hass, self._entry, self._client.token)

        try:
            await call()
        except XfinityRemoteError as err:
            # The token was just accepted, so this is Xfinity's problem, not a reason to re-pair.
            raise HomeAssistantError(f"Xfinity command failed: {err}") from err
