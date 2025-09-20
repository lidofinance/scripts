from archive.scripts.vote_dg_easy_track_tw_holesky import start_vote
from brownie import interface, chain, web3  # type: ignore
from utils.dual_governance import wait_for_noon_utc_to_satisfy_time_constrains
from utils.config import (
    DUAL_GOVERNANCE,
    TIMELOCK,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    contracts,
)

# Implementation address from vote script
TRIGGERABLE_WITHDRAWALS_GATEWAY = "0x4FD4113f2B92856B59BC3be77f2943B7F4eaa9a5"

EASYTRACK_EVMSCRIPT_EXECUTOR = "0x2819B65021E13CEEB9AC33E77DB32c7e64e7520D"

EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x4aB23f409F8F6EdeF321C735e941E4670804a1B4"
EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x7A1c5af4625dc1160a7c67d00335B6Ad492bE53f"


def test_vote(helpers, accounts, vote_ids_from_env, stranger):
    triggerable_withdrawals_gateway = interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)

    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    submit_exit_hashes_role = web3.keccak(text="SUBMIT_REPORT_HASH_ROLE")
    initial_factories = contracts.easy_track.getEVMScriptFactories()
    DG_OLD_WITHDRAWAL_BLOCKERS = (
        contracts.withdrawal_queue.address,
        contracts.validators_exit_bus_oracle.address,
    )

    DG_NEW_WITHDRAWAL_BLOCKERS = (
        contracts.withdrawal_queue.address,
        contracts.validators_exit_bus_oracle.address,
        triggerable_withdrawals_gateway.address,
    )

    tiebreaker_details = contracts.dual_governance.getTiebreakerDetails()
    assert tiebreaker_details[3] == DG_OLD_WITHDRAWAL_BLOCKERS, "Old withdrawal blockers should be set in Dual Governance before vote"


    assert not contracts.validators_exit_bus_oracle.hasRole(submit_exit_hashes_role, EASYTRACK_EVMSCRIPT_EXECUTOR)
    # SDVT EVM script factory is not in Easy Track
    assert EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY not in initial_factories, "EasyTrack should not have SDVT Submit Validator Exit Request Hashes factory before vote"
    # Curated EVM script factory is not in Easy Track
    assert EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY not in initial_factories, "EasyTrack should not have Curated Submit Validator Exit Request Hashes factory before vote"
    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}")

    proposal_id = vote_tx.events["ProposalSubmitted"][1]["proposalId"]
    print(f"proposalId = {proposal_id}")

    chain.sleep(timelock.getAfterSubmitDelay() + 1)
    dual_governance.scheduleProposal(proposal_id, {"from": stranger})

    chain.sleep(timelock.getAfterScheduleDelay() + 1)
    wait_for_noon_utc_to_satisfy_time_constrains()

    dg_tx = timelock.execute(proposal_id, {"from": stranger})
        # Check DG WITHDRAWAL_BLOCKERS
    tiebreaker_details = contracts.dual_governance.getTiebreakerDetails()
    print(f"tiebreaker_details = {tiebreaker_details[3]}")
    assert tiebreaker_details[3] == DG_NEW_WITHDRAWAL_BLOCKERS, "New withdrawal blockers should be set in Dual Governance after vote"

    assert contracts.validators_exit_bus_oracle.hasRole(submit_exit_hashes_role, EASYTRACK_EVMSCRIPT_EXECUTOR)
    new_factories = contracts.easy_track.getEVMScriptFactories()
    # SDVT EVM script factory is added to Easy Track
    assert EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY in new_factories, "EasyTrack should have SDVT Submit Validator Exit Request Hashes factory after vote"
    # Curated EVM script factory is added to Easy Track
    assert EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY in new_factories, "EasyTrack should have Curated Submit Validator Exit Request Hashes factory after vote"
