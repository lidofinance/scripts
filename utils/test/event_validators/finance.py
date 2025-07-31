from brownie.network.event import EventDict
from brownie import web3
from .common import validate_events_chain


def validate_new_immediate_payment_event(
    event: EventDict, token: str, from_addr: str, to_addr: str, amount: int, finance: str
):
    _events_chain = ["LogScriptCall", "NewPeriod", "NewTransaction", "Transfer", "VaultTransfer"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("Transfer") == 1
    assert event.count("NewTransaction") == 1

    assert event["NewTransaction"]["entity"] == to_addr
    assert event["NewTransaction"]["amount"] == amount
    assert event["NewTransaction"]["incoming"] == False

    assert web3.to_checksum_address(event["NewTransaction"]["_emitted_by"]) == web3.to_checksum_address(
        finance
    ), "Wrong event emitter"


    assert event["Transfer"]["_from"] == from_addr
    assert event["Transfer"]["_to"] == to_addr
    assert event["Transfer"]["_amount"] == amount

    assert web3.to_checksum_address(event["Transfer"]["_emitted_by"]) == web3.to_checksum_address(
        token
    ), "Wrong event emitter"
