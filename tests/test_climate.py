from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.common import load_fixture
from custom_components.wundasmart.const import DOMAIN
from unittest.mock import patch
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACAction

import json


async def test_climate(hass: HomeAssistant, config):
    entry = MockConfigEntry(domain=DOMAIN, data=config)
    entry.add_to_hass(hass)

    # Test setup of climate entity fetches initial state
    data = json.loads(load_fixture("test_get_devices1.json"))
    with patch("custom_components.wundasmart.get_devices", return_value=data):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("climate.test_room")

        assert state
        assert state.attributes["current_temperature"] == 17.8
        assert state.attributes["temperature"] == 0
        assert state.state == "auto"
        assert state.attributes["hvac_action"] == HVACAction.OFF

    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator

    # Test refreshing coordinator updates entity state
    data = json.loads(load_fixture("test_get_devices2.json"))
    with patch("custom_components.wundasmart.get_devices", return_value=data):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state = hass.states.get("climate.test_room")

        assert state
        assert state.attributes["current_temperature"] == 16.0
        assert state.attributes["temperature"] == 0
        assert state.state == "auto"
        assert state.attributes["hvac_action"] == HVACAction.PREHEATING

    # Test setting temperature works
    data = json.loads(load_fixture("test_get_devices3.json"))
    tdata = json.loads(load_fixture("test_set_temperature.json"))
    with patch("custom_components.wundasmart.get_devices", side_effect=[data, tdata]), \
            patch("custom_components.wundasmart.climate.send_command", return_value=None) as mock:
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Check the state before setting the temperature
        state = hass.states.get("climate.test_room")
        assert state
        assert state.attributes["current_temperature"] == 16.0
        assert state.attributes["temperature"] == 20
        assert state.state == "auto"
        assert state.attributes["hvac_action"] == HVACAction.OFF

        # set the temperature
        await hass.services.async_call("climate", "set_temperature", {
            "entity_id": "climate.test_room",
            "temperature": 20
        })
        await hass.async_block_till_done()

        # Check put_state was called for the right entity
        assert mock.call_count == 1
        assert mock.call_args.kwargs["params"]
        assert mock.call_args.kwargs["params"]["roomid"] == "121"

        # Check the state was updated
        state = hass.states.get("climate.test_room")
        assert state
        assert state.attributes["current_temperature"] == 16.0
        assert state.attributes["temperature"] == 20
        assert state.state == "heat"
        assert state.attributes["hvac_action"] == HVACAction.HEATING
