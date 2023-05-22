from typing import Tuple, Annotated
from .common import validate_events_chain
from brownie.network.event import EventDict


def validate_app_update_event(event: EventDict, app_id: str, app_address: str):
    _ldo_events_chain = ["LogScriptCall", "SetApp"]

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count("SetApp") == 1

    assert event["SetApp"]["appId"] == app_id, "Wrong app id"
    assert event["SetApp"]["app"] == app_address, "Wrong app address"


def validate_push_to_repo_event(event: EventDict, semantic_version: Annotated[Tuple[int, int, int], 3]):
    _ldo_events_chain = ["LogScriptCall", "NewVersion"]

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count("NewVersion") == 1

    assert event["NewVersion"]["semanticVersion"] == semantic_version, "Wrong version"
