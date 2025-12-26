from typing import NamedTuple
from brownie import ZERO_ADDRESS, convert

from brownie.network.event import EventDict
from .common import validate_events_chain

class Burn(NamedTuple):
    holder_addr: str
    amount: int


class Issue(NamedTuple):
    token_manager_addr: str
    amount: int


class Vested(NamedTuple):
    destination_addr: str
    amount: int
    start: int
    cliff: int
    vesting: int
    revokable: bool


def validate_ldo_issue_event(event: EventDict, i: Issue, emitted_by: str):
    _events_chain = ['LogScriptCall', 'Transfer']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('LogScriptCall') == 1
    assert event.count('Transfer') == 1

    assert event['Transfer']['from'] == ZERO_ADDRESS, "Wrong from field"
    assert event['Transfer']['to'] == i.token_manager_addr
    assert event['Transfer']['value'] == i.amount

    assert convert.to_address(event["Transfer"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), "Wrong event emitter"


def validate_ldo_vested_event(event: EventDict, v: Vested, emitted_by: str):
    _events_chain = ['LogScriptCall', 'Transfer', 'NewVesting']

    assert event.count('LogScriptCall') == 1
    assert event.count('Transfer') == 1
    assert event.count('NewVesting') == 1

    validate_events_chain([e.name for e in event], _events_chain)

    assert event['Transfer']['to'] == v.destination_addr
    assert event['Transfer']['value'] == v.amount

    assert event['NewVesting']['receiver'] == v.destination_addr
    assert event['NewVesting']['amount'] == v.amount

    assert convert.to_address(event["NewVesting"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), "Wrong event emitter"


def validate_ldo_burn_event(event: EventDict, b: Burn, emitted_by: str):
    _events_chain = ['LogScriptCall', 'Transfer']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('LogScriptCall') == 1
    assert event.count('Transfer') == 1

    assert event['Transfer']['from'] == b.holder_addr, "Wrong from field"
    assert event['Transfer']['to'] == ZERO_ADDRESS
    assert event['Transfer']['value'] == b.amount

    assert convert.to_address(event["Transfer"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), "Wrong event emitter"
