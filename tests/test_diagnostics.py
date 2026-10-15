"""Diagnostics tests."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xfinity_remote.const import CONF_DEVICE_NAME, CONF_TOKEN, DOMAIN
from custom_components.xfinity_remote.diagnostics import async_get_config_entry_diagnostics

from .conftest import DEVICE_ID, make_token


async def test_diagnostics_redacts_identifiers(hass: HomeAssistant, mock_client) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=DEVICE_ID, data={CONF_TOKEN: make_token(), CONF_DEVICE_NAME: "Family Room"}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["entry"]["data"] == {CONF_TOKEN: "**REDACTED**", CONF_DEVICE_NAME: "Family Room"}
    assert diag["device_id"] == "**REDACTED**"
    assert diag["token_claims"]["xbo_account_id"] == "**REDACTED**"
    assert diag["token_claims"]["partner"] == "comcast"
    assert diag["token_claims"]["refresh_interval_ms"] == 2998000
    assert diag["token_claims"]["expires_at"].startswith("2027-")
    # Nothing that looks like a JWT anywhere in the output.
    assert "eyJ" not in str(diag)
