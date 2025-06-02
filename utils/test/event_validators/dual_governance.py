from typing import NamedTuple, List
from web3 import Web3

from brownie.network.event import EventDict

from .common import validate_events_chain
from brownie.network.transaction import TransactionReceipt
from utils.test.tx_tracing_helpers import tx_events_from_trace


def validate_dual_governance_submit_event(
    event: EventDict, proposal_id: int, proposer: str, executor: str, metadata: str, proposal_calls: any
) -> None:
    _events_chain = ["LogScriptCall", "ProposalSubmitted", "ProposalSubmitted"]

    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("LogScriptCall") == 1
    assert event.count("ProposalSubmitted") == 2

    assert event["ProposalSubmitted"][0]["id"] == proposal_id, "Wrong proposalId"
    assert event["ProposalSubmitted"][0]["executor"] == executor, "Wrong executor"

    # assert event["ProposalSubmitted"][0]["callsCount"] == len(proposal_calls), "Wrong callsCount"

    for i in range(1, len(proposal_calls)):
        assert event["ProposalSubmitted"][0]["calls"][i][0] == proposal_calls[i]["target"], "Wrong target"
        assert event["ProposalSubmitted"][0]["calls"][i][1] == proposal_calls[i]["value"], "Wrong value"
        assert event["ProposalSubmitted"][0]["calls"][i][2] == proposal_calls[i]["data"], "Wrong data"

    assert event["ProposalSubmitted"][1]["proposalId"] == proposal_id, "Wrong proposalId"
    assert event["ProposalSubmitted"][1]["proposerAccount"] == proposer, "Wrong proposer"
    assert event["ProposalSubmitted"][1]["metadata"] == metadata, "Wrong metadata"
