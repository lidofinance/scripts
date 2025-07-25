from brownie.network.event import EventDict
from brownie import convert, web3
from .common import validate_events_chain


def validate_dual_governance_submit_event(
    event: EventDict,
    proposal_id: int,
    proposer: str,
    executor: str,
    metadata: str,
    proposal_calls: any,
    emitted_by: list[str] = None,
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

    if emitted_by is not None:
        for i in range(0, len(emitted_by)):
            assert convert.to_address(event["ProposalSubmitted"][i]["_emitted_by"]) == convert.to_address(
                emitted_by[i]
            ), "Wrong event emitter"


def validate_dual_governance_tiebreaker_activation_timeout_set_event(
    event: EventDict, timeout: int, emitted_by: str = None
) -> None:
    _events_chain = ["TiebreakerActivationTimeoutSet", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("TiebreakerActivationTimeoutSet") == 1

    assert event["TiebreakerActivationTimeoutSet"]["newTiebreakerActivationTimeout"] == timeout, "Wrong timeout"

    assert web3.to_checksum_address(event["TiebreakerActivationTimeoutSet"]["_emitted_by"]) == web3.to_checksum_address(
        emitted_by
    ), "Wrong event emitter"


def validate_dual_governance_tiebreaker_committee_set_event(event: EventDict, committee: str, emitted_by: str) -> None:
    _events_chain = ["TiebreakerCommitteeSet", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("TiebreakerCommitteeSet") == 1

    assert event["TiebreakerCommitteeSet"]["newTiebreakerCommittee"] == committee, "Wrong committee"

    assert web3.to_checksum_address(event["TiebreakerCommitteeSet"]["_emitted_by"]) == web3.to_checksum_address(
        emitted_by
    ), "Wrong event emitter"


def validate_dual_governance_tiebreaker_sealable_withdrawal_blocker_added_event(
    event: EventDict, blocker: str, emitted_by: str
) -> None:
    _events_chain = ["SealableWithdrawalBlockerAdded", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("SealableWithdrawalBlockerAdded") == 1

    assert event["SealableWithdrawalBlockerAdded"]["sealable"] == blocker, "Wrong blocker"

    assert web3.to_checksum_address(event["SealableWithdrawalBlockerAdded"]["_emitted_by"]) == web3.to_checksum_address(
        emitted_by
    ), "Wrong event emitter"


def validate_dual_governance_proposer_registered_event(
    event: EventDict, proposer: str, executor: str, emitted_by: str
) -> None:
    _events_chain = ["ProposerRegistered", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ProposerRegistered") == 1

    assert event["ProposerRegistered"]["proposerAccount"] == proposer, "Wrong proposer"
    assert event["ProposerRegistered"]["executor"] == executor, "Wrong executor"

    assert web3.to_checksum_address(event["ProposerRegistered"]["_emitted_by"]) == web3.to_checksum_address(
        emitted_by
    ), "Wrong event emitter"


def validate_dual_governance_proposals_canceller_set_event(event: EventDict, canceller: str, emitted_by: str) -> None:
    _events_chain = ["ProposalsCancellerSet", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ProposalsCancellerSet") == 1

    assert event["ProposalsCancellerSet"]["proposalsCanceller"] == canceller, "Wrong canceller"

    assert web3.to_checksum_address(event["ProposalsCancellerSet"]["_emitted_by"]) == web3.to_checksum_address(
        emitted_by
    ), "Wrong event emitter"


def validate_dual_governance_reseal_committee_set_event(event: EventDict, committee: str, emitted_by: str) -> None:
    _events_chain = ["ResealCommitteeSet", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ResealCommitteeSet") == 1

    assert event["ResealCommitteeSet"]["resealCommittee"] == committee, "Wrong committee"

    assert web3.to_checksum_address(event["ResealCommitteeSet"]["_emitted_by"]) == web3.to_checksum_address(
        emitted_by
    ), "Wrong event emitter"


def validate_dual_governance_config_provider_set_event(
    event: EventDict, config_provider: str, min_assets_lock_duration: int, emitted_by: str
) -> None:
    _events_chain = ["ConfigProviderSet", "MinAssetsLockDurationSet", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ConfigProviderSet") == 1

    assert event["ConfigProviderSet"]["newConfigProvider"] == config_provider, "Wrong configProvider"

    assert event.count("MinAssetsLockDurationSet") == 1

    assert (
        event["MinAssetsLockDurationSet"]["newAssetsLockDuration"] == min_assets_lock_duration
    ), "Wrong minAssetsLockDuration"

    assert web3.to_checksum_address(event["ConfigProviderSet"]["_emitted_by"]) == web3.to_checksum_address(
        emitted_by
    ), "Wrong event emitter"


def validate_timelock_governance_set_event(
    event: EventDict, governance: str, proposals_cancelled_till: int, emitted_by: str
) -> None:
    _events_chain = ["GovernanceSet", "ProposalsCancelledTill", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("GovernanceSet") == 1

    assert event["GovernanceSet"]["newGovernance"] == governance, "Wrong governance"

    assert event.count("ProposalsCancelledTill") == 1

    assert event["ProposalsCancelledTill"]["proposalId"] == proposals_cancelled_till, "Wrong proposalsCancelledTill"

    assert web3.to_checksum_address(event["GovernanceSet"]["_emitted_by"]) == web3.to_checksum_address(
        emitted_by
    ), "Wrong event emitter"
