from .common import validate_events_chain
from brownie.network.event import EventDict


def validate_voting_adapter_upgraded_event(event: EventDict, voting_adapter_address: str):
    _events_chain = ["LogScriptCall", "VotingAdapterUpgraded"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("VotingAdapterUpgraded") == 1

    assert event["VotingAdapterUpgraded"]["voting_adapter"] == voting_adapter_address, "Wrong voting adapter address"
