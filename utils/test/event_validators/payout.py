#!/usr/bin/python3

from typing import NamedTuple

from brownie.network.event import EventDict
from .common import validate_events_chain


class Payout(NamedTuple):
    token_addr: str
    from_addr: str
    to_addr: str
    amount: int


def validate_token_payout_event(event: EventDict, p: Payout):
    _ldo_events_chain = ['LogScriptCall', 'NewPeriod', 'NewTransaction', 'Transfer', 'VaultTransfer']

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count('VaultTransfer') == 1
    assert event.count('Transfer') == 1
    assert event.count('NewTransaction') == 1

    assert event['VaultTransfer']['token'] == p.token_addr, "Wrong payout token"
    assert event['VaultTransfer']['to'] == p.to_addr, "Wrong payout destination ('to')"
    assert event['VaultTransfer']['amount'] == p.amount, "Wrong payout amount"

    assert event['Transfer']['to'] == p.to_addr, "Wrong payout destination ('to')"
    assert event['Transfer']['value'] == p.amount, "Wrong payout amount"
    assert event['Transfer']['from'] == p.from_addr, "Wrong payout source ('from')"

    assert event['NewTransaction']['entity'] == p.to_addr
    assert event['NewTransaction']['amount'] == p.amount

def validate_ether_payout_event(event: EventDict, p: Payout):
    _ldo_events_chain = ['LogScriptCall', 'NewPeriod', 'NewTransaction', 'VaultTransfer']

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count('VaultTransfer') == 1
    assert event.count('NewTransaction') == 1

    assert event['VaultTransfer']['token'] == p.token_addr, "Wrong payout token"
    assert event['VaultTransfer']['to'] == p.to_addr, "Wrong payout destination ('to')"
    assert event['VaultTransfer']['amount'] == p.amount, "Wrong payout amount"

    assert event['NewTransaction']['entity'] == p.to_addr
    assert event['NewTransaction']['amount'] == p.amount
