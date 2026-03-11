from src.aetherlink.input.xinput import XInputPlugin


def test_read_controller_state():
    plugin = XInputPlugin()
    state = plugin.read_controller_state()
    assert isinstance(state, dict)
    assert 'button_a' in state
    assert 'button_b' in state
    assert 'left_trigger' in state
    assert 'right_trigger' in state
    assert 'left_stick' in state
    assert 'right_stick' in state


def test_get_capabilities():
    plugin = XInputPlugin()
    capabilities = plugin.get_capabilities()
    assert isinstance(capabilities, list)
    assert len(capabilities) == 1
    capability = capabilities[0]
    assert isinstance(capability, dict)
    assert 'mode' in capability
    assert 'supported_buttons' in capability
    assert 'supported_triggers' in capability
    assert 'supported_sticks' in capability
