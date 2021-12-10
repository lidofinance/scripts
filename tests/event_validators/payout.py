#!/usr/bin/python3

from typing import NamedTuple

from brownie.network.event import EventDict

class Payout(NamedTuple):
    token_addr: str
    from_addr: str
    to_addr: str
    amount: int

# Check that all tx_events contained in reference_events (with proper ordering and occurrences count).
# Allow some of the reference_events skipped in the tx_events. 
#
# Examples:
#
# tx_events: ['A', 'B', 'C'], reference_events: ['A', 'B', 'C'] => valid
# tx_events: ['A', 'B', 'D'], reference_events: ['A', 'B', 'C', 'D'] => valid
#
# tx_events: ['A', 'B', 'D'], reference_events: ['A', 'B', 'C'] => invalid // extra 'D' event
# tx_events: ['A', 'B', 'A', 'B'], reference_events: ['A', 'B'] => invalid // duplicated 'A', 'B' events chain
# tx_events: ['A', 'C', 'B'], reference_events: ['A', 'B', 'C'] => invalid // wrong order
def validate_events_chain (tx_events: [str], reference_events: [str]):
    for ev in tx_events:
        idx = next((reference_events.index(e) for e in reference_events if e == ev), len(reference_events))
        assert idx != len(reference_events), f"{ev} not found in the remaining {reference_events} events chain"
        reference_events=reference_events[idx+1:]

def validate_payout_event (event: EventDict, p: Payout):
    _ldo_events_chain = ['LogScriptCall', 'NewPeriod', 'NewTransaction', 'Transfer', 'VaultTransfer']

    validate_events_chain ([e.name for e in event], _ldo_events_chain)

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
