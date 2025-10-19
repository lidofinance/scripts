#!/usr/bin/python3

from typing import NamedTuple

from brownie.network.event import EventDict
from .common import validate_events_chain
from utils.finance import ZERO_ADDRESS
from brownie import convert


class Payout(NamedTuple):
    token_addr: str
    from_addr: str
    to_addr: str
    amount: int


def validate_token_payout_event(event: EventDict, p: Payout, is_steth: bool = False, emitted_by: str = None):
    _token_events_chain = ["LogScriptCall", "NewPeriod", "NewPeriod", "NewTransaction", "Transfer"]
    if is_steth:
        _token_events_chain += ["TransferShares"]

    _token_events_chain += ["VaultTransfer"]

    print (event)

    validate_events_chain([e.name for e in event], _token_events_chain)

    assert event.count("VaultTransfer") == 1
    assert event.count("Transfer") == 1
    assert event.count("NewTransaction") == 1

    assert event["VaultTransfer"]["token"] == p.token_addr, "Wrong payout token"
    assert event["VaultTransfer"]["to"] == p.to_addr, "Wrong payout destination ('to')"
    assert event["VaultTransfer"]["amount"] == p.amount, "Wrong payout amount"

    _to = _from = ZERO_ADDRESS
    _value = 0
    try:
        _to = event["Transfer"]["to"]
        _from = event["Transfer"]["from"]
        _value = event["Transfer"]["value"]
    except:
        _to = event["Transfer"]["_to"]
        _from = event["Transfer"]["_from"]
        _value = event["Transfer"]["_amount"]

    assert _from == p.from_addr, "Wrong payout source ('from')"
    assert _to == p.to_addr, "Wrong payout destination ('to')"
    assert _value == p.amount, "Wrong payout amount"

    assert event["NewTransaction"]["entity"] == p.to_addr
    assert event["NewTransaction"]["amount"] == p.amount

    if emitted_by is not None:
        assert convert.to_address(event["VaultTransfer"]["_emitted_by"]) == convert.to_address(
            emitted_by
        ), "Wrong event emitter"


def validate_ether_payout_event(event: EventDict, p: Payout):
    _ether_events_chain = ["LogScriptCall", "NewPeriod", "NewTransaction", "VaultTransfer"]

    validate_events_chain([e.name for e in event], _ether_events_chain)

    assert event.count("VaultTransfer") == 1
    assert event.count("NewTransaction") == 1

    assert event["VaultTransfer"]["token"] == p.token_addr, "Wrong payout token"
    assert event["VaultTransfer"]["to"] == p.to_addr, "Wrong payout destination ('to')"
    assert event["VaultTransfer"]["amount"] == p.amount, "Wrong payout amount"

    assert event["NewTransaction"]["entity"] == p.to_addr
    assert event["NewTransaction"]["amount"] == p.amount


def validate_agent_execute_ether_wrap_event(event: EventDict, p: Payout):
    _ether_wrap_events_chain = ["LogScriptCall", "Deposit", "Execute"]

    validate_events_chain([e.name for e in event], _ether_wrap_events_chain)

    assert p.token_addr == ZERO_ADDRESS
    assert event["Deposit"]["dst"] == p.from_addr, "Wrong payout sender"
    assert event["Deposit"]["wad"] == p.amount, "Wrong payout amount"

    assert event["Execute"]["target"] == p.to_addr, "Wrong payout receiver"
    assert event["Execute"]["ethValue"] == p.amount, "Wrong payout amount"
    assert event["Execute"]["data"] == "0xd0e30db0", "Wrong Agent execute data"
