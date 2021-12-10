#!/usr/bin/python3

from typing import NamedTuple

from brownie.network.event import EventDict

class Payout(NamedTuple):
    token_addr: str
    from_addr: str
    to_addr: str
    amount: int

def validate_payout_event (event: EventDict, p: Payout):
    _ldo_events_chain = ['LogScriptCall', 'NewPeriod', 'NewTransaction', 'Transfer', 'VaultTransfer']

    # We check that transaction events contained in _ldo_events_chain (ordering and occurrences count are preserved)
    # e.g. duplicated chain will trigger assert
    events_chain = [e.name for e in event]
    for ev in events_chain:
        idx = next((_ldo_events_chain.index(e) for e in _ldo_events_chain if e == ev), len(_ldo_events_chain))
        assert idx != len(_ldo_events_chain), f"{ev} not found in the remaining {_ldo_events_chain} events chain"
        _ldo_events_chain=_ldo_events_chain[idx:]

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
