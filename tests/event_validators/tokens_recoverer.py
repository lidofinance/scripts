from typing import NamedTuple

from brownie.network.event import EventDict
from .common import validate_events_chain

class Recover(NamedTuple):
    sender_addr: str
    manager_addr: str
    token_addr: str
    amount: int
    recovered_amount: int

def validate_recover_event(event: EventDict, r: Recover, dao_agent: str):
    _events_chain = ['LogScriptCall', 'Transfer', 'ERC20TokenRecovered', 'OwnershipTransferred', 'Recover']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('Recover') == 1
    assert event.count('ERC20TokenRecovered') == 1
    assert event.count('OwnershipTransferred') == 1
    assert event.count('Transfer') == 1

    assert event['Transfer']['from'] == r.manager_addr
    assert event['Transfer']['to'] == dao_agent
    assert event['Transfer']['value'] == r.recovered_amount

    assert event['ERC20TokenRecovered']['token'] == r.token_addr
    assert event['ERC20TokenRecovered']['amount'] == r.recovered_amount
    assert event['ERC20TokenRecovered']['recipient'] == dao_agent

    assert event['OwnershipTransferred']['newOwner'] == dao_agent

    assert event['Recover']['sender'] == r.sender_addr
    assert event['Recover']['manager'] == r.manager_addr
    assert event['Recover']['token'] == r.token_addr
    assert event['Recover']['amount'] == r.amount
    assert event['Recover']['recovered_amount'] == r.recovered_amount
