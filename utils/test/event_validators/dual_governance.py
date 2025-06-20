from brownie.network.event import EventDict
from brownie import convert

from .common import validate_events_chain


def validate_dual_governance_submit_event(
    event: EventDict, proposal_id: int, proposer: str, executor: str, metadata: str, proposal_calls: any, emitted_by: list[str] = None
) -> None:
    _events_chain = ["LogScriptCall", "ProposalSubmitted", "ProposalSubmitted"]

    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("LogScriptCall") == 1
    assert event.count("ProposalSubmitted") == 2

    assert event["ProposalSubmitted"][0]["id"] == proposal_id, "Wrong proposalId"
    assert event["ProposalSubmitted"][0]["executor"] == executor, "Wrong executor"

    assert len(event["ProposalSubmitted"][0]["calls"]) == len(proposal_calls), "Wrong callsCount"

    for i in range(0, len(proposal_calls)):
        assert event["ProposalSubmitted"][0]["calls"][i][0] == proposal_calls[i]["target"], "Wrong target"
        assert event["ProposalSubmitted"][0]["calls"][i][1] == proposal_calls[i]["value"], "Wrong value"
        assert event["ProposalSubmitted"][0]["calls"][i][2] == proposal_calls[i]["data"], "Wrong data"

    assert event["ProposalSubmitted"][1]["proposalId"] == proposal_id, "Wrong proposalId"
    assert event["ProposalSubmitted"][1]["proposerAccount"] == proposer, "Wrong proposer"
    assert event["ProposalSubmitted"][1]["metadata"] == metadata, "Wrong metadata"

    assert len(event["ProposalSubmitted"]) == len(emitted_by), "Wrong emitted_by count"

    for i in range(0, len(emitted_by)):
        assert convert.to_address(event["ProposalSubmitted"][i]["_emitted_by"]) == convert.to_address(
            emitted_by[i]
        ), "Wrong event emitter"
       
