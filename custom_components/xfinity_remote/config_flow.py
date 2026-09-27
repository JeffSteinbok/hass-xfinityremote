"""Config flow for Xfinity Remote.

Pairing uses Xfinity's "EasyPair": the server hands out a 7-digit code, the user says
"Easy Pair" into their real voice remote and types the code on the TV, and we poll until
the server confirms and returns a long-lived token bound to that box.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    PairingSession,
    XfinityRemoteAuthError,
    XfinityRemoteClient,
    XfinityRemoteError,
    decode_token,
)
from .const import (
    CONF_DEVICE_NAME,
    CONF_TOKEN,
    DOMAIN,
    PAIRING_POLL_SECONDS,
    PAIRING_TIMEOUT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class XfinityRemoteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Xfinity Remote."""

    VERSION = 1

    def __init__(self) -> None:
        self._client: XfinityRemoteClient | None = None
        self._pairing: PairingSession | None = None
        self._pair_task: asyncio.Task[str] | None = None
        self._token: str | None = None
        self._pair_error: str | None = None

    @property
    def client(self) -> XfinityRemoteClient:
        if self._client is None:
            self._client = XfinityRemoteClient(async_get_clientsession(self.hass))
        return self._client

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Let the user pick how to connect."""
        return self.async_show_menu(step_id="user", menu_options=["pair", "token"])

    # --- EasyPair ----------------------------------------------------------

    async def async_step_pair(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the pairing code and wait for it to be entered on the TV."""
        if self._pair_task is None:
            try:
                self._pairing = await self.client.start_pairing(str(uuid.uuid4()))
            except XfinityRemoteError as err:
                _LOGGER.warning("Could not start EasyPair: %s", err)
                return self.async_abort(reason="cannot_connect")
            self._pair_task = self.hass.async_create_task(self._async_wait_for_pairing())

        if not self._pair_task.done():
            return self.async_show_progress(
                step_id="pair",
                progress_action="wait_for_tv",
                description_placeholders={"code": self._pairing.code},
                progress_task=self._pair_task,
            )

        task, self._pair_task = self._pair_task, None
        try:
            self._token = task.result()
        except TimeoutError:
            self._pair_error = "pair_timeout"
        except XfinityRemoteError as err:
            _LOGGER.warning("EasyPair failed: %s", err)
            self._pair_error = "pair_failed"
        return self.async_show_progress_done(
            next_step_id="pair_failed" if self._pair_error else "finish"
        )

    async def _async_wait_for_pairing(self) -> str:
        async with asyncio.timeout(PAIRING_TIMEOUT_SECONDS):
            while True:
                await asyncio.sleep(PAIRING_POLL_SECONDS)
                if token := await self.client.confirm_pairing(self._pairing):
                    return token

    async def async_step_pair_failed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Offer to try pairing again with a fresh code."""
        if user_input is not None:
            self._pair_error = None
            return await self.async_step_pair()
        return self.async_show_form(step_id="pair_failed", errors={"base": self._pair_error})

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pairing succeeded."""
        return await self._async_create_or_update(self._token)

    # --- Manual token --------------------------------------------------------

    async def async_step_token(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Accept an arToken copied from remote.xfinity.com's localStorage."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.client.token = user_input[CONF_TOKEN].strip()
            try:
                decode_token(self.client.token)
                await self.client.refresh_token()
            except XfinityRemoteAuthError:
                errors["base"] = "invalid_auth"
            except XfinityRemoteError:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_create_or_update(self.client.token)

        return self.async_show_form(
            step_id="token",
            data_schema=vol.Schema(
                {vol.Required(CONF_TOKEN): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))}
            ),
            errors=errors,
        )

    # --- Reauth --------------------------------------------------------------

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The saved token stopped working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Explain, then re-run pairing."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    # --- Shared --------------------------------------------------------------

    async def _async_create_or_update(self, token: str) -> ConfigFlowResult:
        info = decode_token(token)
        if not info.xbo_device_id:
            return self.async_abort(reason="invalid_token")

        await self.async_set_unique_id(info.xbo_device_id)

        name = await self._async_device_name(token, info.xbo_device_id)
        data = {CONF_TOKEN: token, CONF_DEVICE_NAME: name}

        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch(reason="wrong_device")
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data_updates=data)

        self._abort_if_unique_id_configured(updates=data)
        return self.async_create_entry(title=name or "Xfinity Remote", data=data)

    async def _async_device_name(self, token: str, device_id: str) -> str | None:
        """Best-effort lookup of the box's friendly name ("Family Room")."""
        self.client.token = token
        try:
            devices = await self.client.get_devices()
        except XfinityRemoteError as err:
            _LOGGER.debug("Could not list devices: %s", err)
            return None
        return next((d.get("name") for d in devices if d.get("id") == device_id), None)
