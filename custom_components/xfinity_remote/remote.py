"""Remote entity for an Xfinity X1 box."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

import voluptuous as vol

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    RemoteEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import XfinityRemoteConfigEntry
from .api import CEC_KEYS, KEYS, VCODES
from .const import (
    ATTR_CHANNEL,
    ATTR_TEXT,
    DEFAULT_DELAY_SECS,
    SERVICE_SEND_TEXT,
    SERVICE_TUNE,
)
from .entity import XfinityRemoteEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XfinityRemoteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the remote entity."""
    async_add_entities([XfinityRemote(entry)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_TUNE,
        {vol.Required(ATTR_CHANNEL): vol.All(cv.string, vol.Match(r"^\d+$"))},
        "async_tune",
    )
    platform.async_register_entity_service(
        SERVICE_SEND_TEXT,
        {vol.Required(ATTR_TEXT): cv.string},
        "async_send_text",
    )


class XfinityRemote(XfinityRemoteEntity, RemoteEntity):
    """Sends button presses to the box through the Xfinity cloud."""

    _attr_name = None
    _attr_translation_key = "remote"

    def __init__(self, entry: XfinityRemoteConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{self._device_id}_remote"

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send one or more commands.

        Each command can be a raw vcode ("GUIDE"), a friendly key name ("guide",
        "volume_up"), or a string of digits ("702") which is typed digit by digit.
        """
        num_repeats = kwargs.get(ATTR_NUM_REPEATS, 1)
        delay = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)

        presses = [press for cmd in command for press in _resolve(cmd)]
        first = True
        for _ in range(num_repeats):
            for press in presses:
                if not first:
                    await asyncio.sleep(delay)
                first = False
                await self._async_press(press)

    async def async_tune(self, channel: str) -> None:
        """Tune to a channel number by typing its digits."""
        await self.async_send_command([channel])

    async def async_send_text(self, text: str) -> None:
        """Send a voice-style text command such as "watch ESPN"."""
        await self._async_call(lambda: self._client.send_text(text))

    async def _async_press(self, press: str | tuple[str, str]) -> None:
        if isinstance(press, tuple):
            await self._async_call(lambda: self._client.send_cec_key(*press))
        else:
            await self._async_call(lambda: self._client.send_key(press))


def _resolve(command: str) -> list[str | tuple[str, str]]:
    """Map a user-supplied command to vcodes / CEC (key, value) pairs."""
    command = command.strip()
    if command in VCODES:
        return [command]
    name = command.lower()
    if name in KEYS:
        return [KEYS[name]]
    if name in CEC_KEYS:
        return [CEC_KEYS[name]]
    if command.isdigit():
        return [f"NUMBER_{digit}" for digit in command]
    raise ServiceValidationError(
        f"Unknown Xfinity command '{command}'. Use a key name like 'guide', a vcode like "
        f"'GUIDE', or a channel number."
    )
