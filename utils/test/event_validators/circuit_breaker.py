from brownie import ZERO_ADDRESS
from brownie.network.event import EventDict


def validate_register_pauser_event(
    event: EventDict,
    pausable_address: str,
    expected_pauser: str,
    emitted_by: str,
):
    assert "PauserSet" in event, (
        f"No PauserSet event for {pausable_address}"
    )
    pauser_set = event["PauserSet"]
    assert pauser_set["pausable"].lower() == pausable_address.lower(), (
        f"Wrong pausable in PauserSet event for {pausable_address}"
    )
    assert pauser_set["previousPauser"] == ZERO_ADDRESS, (
        f"PauserSet.previousPauser for {pausable_address} should be zero"
    )
    assert pauser_set["newPauser"].lower() == expected_pauser.lower(), (
        f"PauserSet.newPauser for {pausable_address} should be {expected_pauser}"
    )
    assert pauser_set["_emitted_by"].lower() == emitted_by.lower(), (
        f"PauserSet for {pausable_address} should be emitted by {emitted_by}"
    )

    assert "HeartbeatUpdated" in event, (
        f"No HeartbeatUpdated event for {pausable_address}"
    )
    heartbeat_updated = event["HeartbeatUpdated"]
    assert heartbeat_updated["pauser"].lower() == expected_pauser.lower(), (
        f"HeartbeatUpdated.pauser for {pausable_address} should be {expected_pauser}"
    )
    assert heartbeat_updated["_emitted_by"].lower() == emitted_by.lower(), (
        f"HeartbeatUpdated for {pausable_address} should be emitted by {emitted_by}"
    )
