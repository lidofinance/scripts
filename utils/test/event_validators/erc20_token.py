from typing import NamedTuple
from brownie import ZERO_ADDRESS

from brownie.network.event import EventDict
from .common import validate_events_chain

from utils.config import contracts


class ERC20Approval(NamedTuple):
    owner: str
    spender: str
    amount: int


class ERC20Transfer(NamedTuple):
    from_addr: str
    to_addr: str
    value: int


def validate_erc20_approval_event(event: EventDict, a: ERC20Approval):
    _events_chain = ["LogScriptCall", "LogScriptCall", "Approval", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 2
    assert event.count("Approval") == 1

    assert event["Approval"]["owner"] == a.owner
    assert event["Approval"]["spender"] == a.spender
    assert event["Approval"]["value"] == a.amount


def validate_erc20_transfer_event(event: EventDict, t: ERC20Transfer, is_steth: bool = False):
    _events_chain = ["LogScriptCall", "LogScriptCall", "Transfer"]
    if is_steth:
        _events_chain += ["TransferShares"]
    _events_chain += ["ERC20Transferred", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 2
    assert event.count("Transfer") == 1

    assert event["Transfer"]["from"] == t.from_addr
    assert event["Transfer"]["to"] == t.to_addr
    assert event["Transfer"]["value"] == t.value

    if is_steth:
        assert event.count("TransferShares") == 1

        assert event["TransferShares"]["from"] == t.from_addr
        assert event["TransferShares"]["to"] == t.to_addr
        assert event["TransferShares"]["sharesValue"] == contracts.lido.getSharesByPooledEth(t.value)
