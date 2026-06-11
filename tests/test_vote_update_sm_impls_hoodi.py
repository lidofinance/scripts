"""
Test vote [HOODI] - update CSM and Curated module implementations.
"""

from brownie import chain, interface

from scripts import vote_update_sm_impls_hoodi as voting_script
from scripts.vote_update_sm_impls_hoodi import start_vote
from utils.config import (
    DUAL_GOVERNANCE,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    TIMELOCK,
    contracts,
)
from utils.dual_governance import wait_for_target_time_to_satisfy_time_constrains


def _proxy_impl(proxy_address: str) -> str:
    return interface.OssifiableProxy(proxy_address).proxy__getImplementation()


def _assert_proxy_impl(proxy_address: str, expected_impl: str, label: str) -> None:
    assert _proxy_impl(proxy_address).lower() == expected_impl.lower(), (
        f"{label} implementation mismatch"
    )


def test_vote_update_sm_impls_hoodi(helpers, accounts, vote_ids_from_env, stranger):
    upgrades = voting_script.get_proxy_upgrades()

    for label, proxy_address, new_impl in upgrades:
        assert _proxy_impl(proxy_address).lower() != new_impl.lower(), (
            f"{label} implementation must be different before the vote"
        )

    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        vote_id, _ = start_vote({"from": LDO_HOLDER_ADDRESS_FOR_TESTS}, silent=True)

    helpers._etherscan_is_fetched = True
    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    proposal_id = vote_tx.events["ProposalSubmitted"][1]["proposalId"]

    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    dg = interface.DualGovernance(DUAL_GOVERNANCE)

    chain.sleep(timelock.getAfterSubmitDelay() + 1)
    dg.scheduleProposal(proposal_id, {"from": stranger})

    chain.sleep(timelock.getAfterScheduleDelay() + 1)
    wait_for_target_time_to_satisfy_time_constrains()

    timelock.execute(proposal_id, {"from": stranger})

    for label, proxy_address, new_impl in upgrades:
        _assert_proxy_impl(proxy_address, new_impl, label)
