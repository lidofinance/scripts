import pytest
import os

from brownie import chain, interface, ZERO_ADDRESS, reverts, web3
from scripts.vote_2025_07_25_hoodi_dg_upgrade import start_vote
from utils.config import contracts
from brownie.network.transaction import TransactionReceipt
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import *

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str

VOTING = "0x49B3512c44891bef83F8967d075121Bd1b07a01B"
DUAL_GOVERNANCE = "0x4D12B9F6ACAB54FF6A3A776BA3B8724D9B77845F"
TIMELOCK = "0x0A5E22782C0BD4ADDF10D771F0BF0406B038282D"
ADMIN_EXECUTOR = "0x0ECC17597D292271836691358B22340B78F3035B"
WITHDRAWAL_QUEUE = "0xFE56573178F1BCDF53F01A6E9977670DCBBD9186"
VALIDATORS_EXIT_BUS_ORACLE = "0x8664D394C2B3278F26A1B44B967AEF99707EEAB2"
TRIGGERABLE_WITHDRAWALS_GATEWAY = "0x6679090D92B08A2A686EF8614FEECD8CDFE209DB"
RESEAL_COMMITTEE = "0x83BCE68B4E8B7071B2A664A26E6D3BC17EEE3102"
TIEBREAKER_ACTIVATION_TIMEOUT = 900
MIN_ASSETS_LOCK_DURATION = 1
ACTIVE_CONFIG_PROVIDER = "0x2b685e6fB288bBb7A82533BAfb679FfDF6E5bb33"

NEW_DUAL_GOVERNANCE = "0x9Ce4bA766C87cC87e507307163eA54C5003A3563"
NEW_TIEBREAKER_COMMITTEE = "0xEd27F0d08630685A0cEFb1040596Cb264cf79f14"
CONFIG_PROVIDER_FOR_DISCONNECTED_DUAL_GOVERNANCE = "0x9CAaCCc62c66d817CC59c44780D1b722359795bF"
DG_UPGRADE_STATE_VERIFIER = "0x816E10812B63A3dAf531cC9A79eAf07a718b4007"

EXPECTED_VOTE_EVENTS_COUNT = 1
EXPECTED_DG_EVENTS_COUNT = 11
IPFS_DESCRIPTION_HASH = "bafkreibaqjqmhreqanbdrdiixodyrxzwcswdnsxonrjn2fnoidni4tupve"


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    steth_token = contracts.lido

    new_dual_governance = interface.DualGovernance(NEW_DUAL_GOVERNANCE)

    # =======================================================================
    # ========================= Before voting tests =========================
    # =======================================================================

    assert timelock.getGovernance() == DUAL_GOVERNANCE
    assert dual_governance.getConfigProvider() == ACTIVE_CONFIG_PROVIDER

    assert new_dual_governance.getConfigProvider() == ACTIVE_CONFIG_PROVIDER
    assert new_dual_governance.getResealCommittee() == ZERO_ADDRESS
    assert new_dual_governance.getProposalsCanceller() == ZERO_ADDRESS
    assert len(new_dual_governance.getProposers()) == 0
    assert new_dual_governance.getTiebreakerDetails() == (False, ZERO_ADDRESS, 0, [])

    # =======================================================================
    # ============================== Voting =================================
    # =======================================================================
    # START VOTE
    vote_id = (
        vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder, "force": True}, silent=True)[0]
    )

    last_dual_governance_proposal_id = timelock.getProposalsCount()
    vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=contracts.voting)

    vote_events = group_voting_events_from_receipt(vote_tx)

    expected_dg_proposal_id = last_dual_governance_proposal_id + 1

    assert expected_dg_proposal_id == timelock.getProposalsCount()

    # =======================================================================
    # ==================== DG Proposal Submit => Execute ====================
    # =======================================================================

    # EXECUTE DUAL GOVERNANCE PROPOSAL
    chain.sleep(timelock.getAfterSubmitDelay() + 1)

    dual_governance.scheduleProposal(expected_dg_proposal_id, {"from": stranger})

    chain.sleep(timelock.getAfterScheduleDelay() + 1)

    dg_tx: TransactionReceipt = timelock.execute(expected_dg_proposal_id, {"from": stranger})

    display_dg_events(dg_tx)
    dg_events = group_dg_events_from_receipt(dg_tx, timelock=TIMELOCK, admin_executor=ADMIN_EXECUTOR)

    # =======================================================================
    # ================= After DG proposal execution tests ===================
    # =======================================================================

    assert timelock.getGovernance() == NEW_DUAL_GOVERNANCE
    assert dual_governance.getConfigProvider() == CONFIG_PROVIDER_FOR_DISCONNECTED_DUAL_GOVERNANCE

    assert new_dual_governance.getConfigProvider() == ACTIVE_CONFIG_PROVIDER
    assert new_dual_governance.getResealCommittee() == RESEAL_COMMITTEE
    assert new_dual_governance.getProposalsCanceller() == VOTING
    proposers = new_dual_governance.getProposers()
    assert len(proposers) == 1
    assert proposers[0][0] == VOTING
    assert proposers[0][1] == ADMIN_EXECUTOR
    assert new_dual_governance.getTiebreakerDetails() == (
        False,
        NEW_TIEBREAKER_COMMITTEE,
        TIEBREAKER_ACTIVATION_TIMEOUT,
        [WITHDRAWAL_QUEUE, VALIDATORS_EXIT_BUS_ORACLE, TRIGGERABLE_WITHDRAWALS_GATEWAY],
    )

    some_proposal_calls = [
        (
            NEW_DUAL_GOVERNANCE,
            0,
            interface.DualGovernance(NEW_DUAL_GOVERNANCE).setTiebreakerActivationTimeout.encode_input(
                TIEBREAKER_ACTIVATION_TIMEOUT - 1
            ),
        )
    ]

    # Test that old DG can't submit proposals
    with reverts(f"CallerIsNotGovernance: {DUAL_GOVERNANCE.lower()}"):
        dual_governance.submitProposal(some_proposal_calls, "This should revert", {"from": VOTING})

    last_proposal_id_before = timelock.getProposalsCount()
    # Test that new DG can submit proposals
    new_dual_governance.submitProposal(some_proposal_calls, "This should not revert", {"from": VOTING})
    assert timelock.getProposalsCount() == last_proposal_id_before + 1

    # Test that old escrow won't get into Rage Quit if lock amount above previous 2nd seal
    old_escrow = interface.DualGovernanceEscrow(contracts.dual_governance.getVetoSignallingEscrow())
    new_escrow = interface.DualGovernanceEscrow(new_dual_governance.getVetoSignallingEscrow())

    old_dual_governance_second_seal = interface.IDualGovernanceConfigProvider(
        dual_governance.getConfigProvider()
    ).SECOND_SEAL_RAGE_QUIT_SUPPORT()
    new_dual_governance_second_seal = interface.IDualGovernanceConfigProvider(
        new_dual_governance.getConfigProvider()
    ).SECOND_SEAL_RAGE_QUIT_SUPPORT()

    steth_total_supply = steth_token.totalSupply()

    # 20% steth of total supply is greater than previous 2nd seal - 10%
    steth_to_lock = steth_total_supply * 0.2

    steth_whale = accounts.at("0xF865A1d43D36c713B4DA085f32b7d1e9739B9275", force=True)
    steth_token.approve(old_escrow.address, steth_to_lock, {"from": steth_whale})

    old_dual_governance_rage_quit_support_before = old_escrow.getRageQuitSupport()
    new_dual_governance_rage_quit_support_before = new_escrow.getRageQuitSupport()

    old_escrow.lockStETH(steth_to_lock, {"from": steth_whale})

    assert old_escrow.getRageQuitSupport() > old_dual_governance_rage_quit_support_before
    assert new_escrow.getRageQuitSupport() == new_dual_governance_rage_quit_support_before

    assert old_escrow.getRageQuitSupport() < old_dual_governance_second_seal
    assert old_escrow.getRageQuitSupport() > new_dual_governance_second_seal

    chain.sleep(old_escrow.MAX_MIN_ASSETS_LOCK_DURATION() + 1)
    old_escrow.unlockStETH({"from": steth_whale})

    assert old_escrow.getRageQuitSupport() == old_dual_governance_rage_quit_support_before

    # =======================================================================
    # ======================== IPFS & events checks =========================
    # =======================================================================
    metadata = find_metadata_by_vote_id(vote_id)
    assert get_lido_vote_cid_from_str(metadata) == IPFS_DESCRIPTION_HASH

    """Validating events"""

    # Validate after voting events count
    assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT

    # Validate after DG proposal execution events count
    assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

    validate_dual_governance_submit_event(
        vote_events[0],
        proposal_id=expected_dg_proposal_id,
        proposer=VOTING,
        executor=ADMIN_EXECUTOR,
        metadata="1.1 - 1.10 Proposal to upgrade Dual Governance contract on Hoodi testnet (Immunefi reported vulnerability fix)",
        proposal_calls=[
            {
                "target": NEW_DUAL_GOVERNANCE,
                "value": 0,
                "data": interface.DualGovernance(NEW_DUAL_GOVERNANCE).setTiebreakerActivationTimeout.encode_input(
                    TIEBREAKER_ACTIVATION_TIMEOUT
                ),
            },
            {
                "target": NEW_DUAL_GOVERNANCE,
                "value": 0,
                "data": interface.DualGovernance(NEW_DUAL_GOVERNANCE).setTiebreakerCommittee.encode_input(
                    NEW_TIEBREAKER_COMMITTEE
                ),
            },
            {
                "target": NEW_DUAL_GOVERNANCE,
                "value": 0,
                "data": interface.DualGovernance(
                    NEW_DUAL_GOVERNANCE
                ).addTiebreakerSealableWithdrawalBlocker.encode_input(WITHDRAWAL_QUEUE),
            },
            {
                "target": NEW_DUAL_GOVERNANCE,
                "value": 0,
                "data": interface.DualGovernance(
                    NEW_DUAL_GOVERNANCE
                ).addTiebreakerSealableWithdrawalBlocker.encode_input(VALIDATORS_EXIT_BUS_ORACLE),
            },
            {
                "target": NEW_DUAL_GOVERNANCE,
                "value": 0,
                "data": interface.DualGovernance(
                    NEW_DUAL_GOVERNANCE
                ).addTiebreakerSealableWithdrawalBlocker.encode_input(TRIGGERABLE_WITHDRAWALS_GATEWAY),
            },
            {
                "target": NEW_DUAL_GOVERNANCE,
                "value": 0,
                "data": interface.DualGovernance(NEW_DUAL_GOVERNANCE).registerProposer.encode_input(
                    VOTING, ADMIN_EXECUTOR
                ),
            },
            {
                "target": NEW_DUAL_GOVERNANCE,
                "value": 0,
                "data": interface.DualGovernance(NEW_DUAL_GOVERNANCE).setProposalsCanceller.encode_input(VOTING),
            },
            {
                "target": NEW_DUAL_GOVERNANCE,
                "value": 0,
                "data": interface.DualGovernance(NEW_DUAL_GOVERNANCE).setResealCommittee.encode_input(RESEAL_COMMITTEE),
            },
            {
                "target": TIMELOCK,
                "value": 0,
                "data": interface.EmergencyProtectedTimelock(TIMELOCK).setGovernance.encode_input(NEW_DUAL_GOVERNANCE),
            },
            {
                "target": DUAL_GOVERNANCE,
                "value": 0,
                "data": interface.DualGovernance(DUAL_GOVERNANCE).setConfigProvider.encode_input(
                    interface.IDualGovernanceConfigProvider(CONFIG_PROVIDER_FOR_DISCONNECTED_DUAL_GOVERNANCE)
                ),
            },
            {
                "target": DG_UPGRADE_STATE_VERIFIER,
                "value": 0,
                "data": interface.DGLaunchVerifier(DG_UPGRADE_STATE_VERIFIER).verify.encode_input(),
            },
        ],
        emitted_by=[TIMELOCK, DUAL_GOVERNANCE],
    )

    validate_dual_governance_tiebreaker_activation_timeout_set_event(
        dg_events[0],
        timeout=TIEBREAKER_ACTIVATION_TIMEOUT,
        emitted_by=NEW_DUAL_GOVERNANCE,
    )

    validate_dual_governance_tiebreaker_committee_set_event(
        dg_events[1],
        committee=NEW_TIEBREAKER_COMMITTEE,
        emitted_by=NEW_DUAL_GOVERNANCE,
    )

    validate_dual_governance_tiebreaker_sealable_withdrawal_blocker_added_event(
        dg_events[2],
        blocker=WITHDRAWAL_QUEUE,
        emitted_by=NEW_DUAL_GOVERNANCE,
    )

    validate_dual_governance_tiebreaker_sealable_withdrawal_blocker_added_event(
        dg_events[3],
        blocker=VALIDATORS_EXIT_BUS_ORACLE,
        emitted_by=NEW_DUAL_GOVERNANCE,
    )

    validate_dual_governance_tiebreaker_sealable_withdrawal_blocker_added_event(
        dg_events[4],
        blocker=TRIGGERABLE_WITHDRAWALS_GATEWAY,
        emitted_by=NEW_DUAL_GOVERNANCE,
    )

    validate_dual_governance_proposer_registered_event(
        dg_events[5],
        proposer=VOTING,
        executor=ADMIN_EXECUTOR,
        emitted_by=NEW_DUAL_GOVERNANCE,
    )

    validate_dual_governance_proposals_canceller_set_event(
        dg_events[6],
        canceller=VOTING,
        emitted_by=NEW_DUAL_GOVERNANCE,
    )

    validate_dual_governance_reseal_committee_set_event(
        dg_events[7],
        committee=RESEAL_COMMITTEE,
        emitted_by=NEW_DUAL_GOVERNANCE,
    )

    validate_dual_governance_governance_set_event(
        dg_events[8],
        governance=NEW_DUAL_GOVERNANCE,
        proposals_cancelled_till=expected_dg_proposal_id,
        emitted_by=TIMELOCK,
    )

    validate_dual_governance_config_provider_set_event(
        dg_events[9],
        config_provider=CONFIG_PROVIDER_FOR_DISCONNECTED_DUAL_GOVERNANCE,
        min_assets_lock_duration=MIN_ASSETS_LOCK_DURATION,
        emitted_by=DUAL_GOVERNANCE,
    )

    validate_dual_governance_state_verified_event(
        dg_events[10],
        emitted_by=DG_UPGRADE_STATE_VERIFIER,
    )


def validate_dual_governance_state_verified_event(event: EventDict, emitted_by: str = None) -> None:
    _events_chain = ["DGUpgradeConfigurationValidated", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("DGUpgradeConfigurationValidated") == 1

    assert web3.to_checksum_address(
        event["DGUpgradeConfigurationValidated"]["_emitted_by"]
    ) == web3.to_checksum_address(emitted_by), "Wrong event emitter"
