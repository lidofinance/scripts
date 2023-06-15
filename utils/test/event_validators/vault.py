from typing import NamedTuple
from brownie import ZERO_ADDRESS

from brownie.network.event import EventDict
from .common import validate_events_chain

class transferERC20(NamedTuple):
    token_addr: str
    from_addr: str
    to_addr: str
    amount: int

def validate_transferERC20_event(event: EventDict, t: transferERC20, is_steth: bool = False):
    _token_events_chain = ["LogScriptCall", "LogScriptCall", "Transfer"]
    if is_steth:
        _token_events_chain += ["TransferShares"]

    _token_events_chain += ["ERC20Transferred", "ScriptResult"]

    validate_events_chain([e.name for e in event], _token_events_chain)

    assert event.count("LogScriptCall") == 2
    assert event.count("Transfer") == 1
    assert event.count("ERC20Transferred") == 1

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

    assert _from == t.from_addr, "Wrong payout source ('from')"
    assert _to == t.to_addr, "Wrong payout destination ('to')"
    assert _value == t.amount, "Wrong payout amount"

    assert event["ERC20Transferred"]["_token"] == t.token_addr
    assert event["ERC20Transferred"]["_recipient"] == t.to_addr
    assert event["ERC20Transferred"]["_amount"] == t.amount