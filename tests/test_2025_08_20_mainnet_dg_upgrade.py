import pytest
import os

from brownie import chain, interface, ZERO_ADDRESS, reverts, web3
from brownie.network.transaction import TransactionReceipt

from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import *
from utils.evm_script import encode_call_script
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import LDO_HOLDER_ADDRESS_FOR_TESTS

from scripts.vote_2025_08_20_mainnet_dg_upgrade import start_vote, get_vote_items

VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
DUAL_GOVERNANCE = "0xcdF49b058D606AD34c5789FD8c3BF8B3E54bA2db"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
WITHDRAWAL_QUEUE = "0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1"
VALIDATORS_EXIT_BUS_ORACLE = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
RESEAL_COMMITTEE = "0xFFe21561251c49AdccFad065C94Fb4931dF49081"
TIEBREAKER_ACTIVATION_TIMEOUT = 31536000  # 1 year
CONFIG_PROVIDER_FOR_ACTIVE_DUAL_GOVERNANCE = "0xa1692Af6FDfdD1030E4E9c4Bc429986FA64CB5EF"

MIN_ASSETS_LOCK_DURATION = 1

NEW_DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
NEW_TIEBREAKER_COMMITTEE = "0xf65614d73952Be91ce0aE7Dd9cFf25Ba15bEE2f5"
CONFIG_PROVIDER_FOR_DISCONNECTED_DUAL_GOVERNANCE = "0xc934E90E76449F09f2369BB85DCEa056567A327a"
DG_UPGRADE_STATE_VERIFIER = "0x6782e5c1e3D37b5ed5a076069B5b2438B9CED5B4"

MATIC_TOKEN = "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0"
LABS_BORG_FOUNDATION = "0x95B521B4F55a447DB89f6a27f951713fC2035f3F"
MATIC_BALANCE_TO_TRANSFER = 508_106_165781175837137177

EXPECTED_VOTE_ID = 191
EXPECTED_DG_PROPOSAL_ID = 4
EXPECTED_VOTE_EVENTS_COUNT = 1
EXPECTED_DG_EVENTS_COUNT = 11
IPFS_DESCRIPTION_HASH = "bafkreibwrhhgakpf5n676cee2x6kc62f7xikaj52dot5bylonoajhdbu7e"

STETH_TOKEN = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
STETH_WHALE = "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0"


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    return [
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
            "data": interface.DualGovernance(NEW_DUAL_GOVERNANCE).addTiebreakerSealableWithdrawalBlocker.encode_input(
                WITHDRAWAL_QUEUE
            ),
        },
        {
            "target": NEW_DUAL_GOVERNANCE,
            "value": 0,
            "data": interface.DualGovernance(NEW_DUAL_GOVERNANCE).addTiebreakerSealableWithdrawalBlocker.encode_input(
                VALIDATORS_EXIT_BUS_ORACLE
            ),
        },
        {
            "target": NEW_DUAL_GOVERNANCE,
            "value": 0,
            "data": interface.DualGovernance(NEW_DUAL_GOVERNANCE).registerProposer.encode_input(VOTING, ADMIN_EXECUTOR),
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
            "target": EMERGENCY_PROTECTED_TIMELOCK,
            "value": 0,
            "data": interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK).setGovernance.encode_input(
                NEW_DUAL_GOVERNANCE
            ),
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
        {
            "target": AGENT,
            "value": 0,
            "data": interface.Agent(AGENT).forward.encode_input(
                encode_call_script(
                    [
                        (
                            MATIC_TOKEN,
                            interface.ERC20(MATIC_TOKEN).transfer.encode_input(
                                LABS_BORG_FOUNDATION, MATIC_BALANCE_TO_TRANSFER
                            ),
                        )
                    ]
                )
            ),
        },
    ]


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):

    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    emergency_protected_timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    voting = interface.Voting(VOTING)
    steth_token = interface.ERC20(STETH_TOKEN)

    new_dual_governance = interface.DualGovernance(NEW_DUAL_GOVERNANCE)

    # =======================================================================
    # ======================== Identifying voting ===========================
    # =======================================================================

    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
        assert vote_id == EXPECTED_VOTE_ID
    elif voting.votesLength() > EXPECTED_VOTE_ID:
        vote_id = EXPECTED_VOTE_ID
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_script_onchain = voting.getVote(vote_id)["script"]
    _, call_script_items = get_vote_items()
    assert vote_script_onchain == encode_call_script(call_script_items)

    is_voting_executed = voting.getVote(vote_id)["executed"]

    if is_voting_executed:
        print("Voting already executed. Skipping Aragon Voting phase tests.")

    if not is_voting_executed:
        # =======================================================================
        # ========================= Before voting tests =========================
        # =======================================================================

        # No executable actions at Aragon Voting phase

        # =======================================================================
        # ========================= Voting Execution ============================
        # =======================================================================

        vote_id = (
            vote_ids_from_env[0]
            if vote_ids_from_env
            else start_vote({"from": ldo_holder, "force": True}, silent=True)[0]
        )

        last_dual_governance_proposal_id = emergency_protected_timelock.getProposalsCount()
        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)

        vote_events = group_voting_events_from_receipt(vote_tx)

        expected_dg_proposal_id = last_dual_governance_proposal_id + 1

        assert expected_dg_proposal_id == emergency_protected_timelock.getProposalsCount()

        # =======================================================================
        # ========================= Validate voting events ======================
        # =======================================================================

        # Validate after voting events count
        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT

        validate_dual_governance_submit_event(
            vote_events[0],
            proposal_id=expected_dg_proposal_id,
            proposer=VOTING,
            executor=ADMIN_EXECUTOR,
            metadata="1.1 - 1.10 Proposal to upgrade Dual Governance contract on Mainnet (Immunefi reported vulnerability fix), 1.11 DAO treasury management",
            proposal_calls=dual_governance_proposal_calls,
            emitted_by=[EMERGENCY_PROTECTED_TIMELOCK, DUAL_GOVERNANCE],
        )

    # =======================================================================
    # ========================= After voting tests ==========================
    # =======================================================================
    metadata = find_metadata_by_vote_id(vote_id)
    assert get_lido_vote_cid_from_str(metadata) == IPFS_DESCRIPTION_HASH

    dg_proposal_calls = emergency_protected_timelock.getProposalCalls(EXPECTED_DG_PROPOSAL_ID)

    # Convert expected calls from dict format into tuple format (target, value, data)
    expected_calls = [(item["target"], item["value"], item["data"]) for item in dual_governance_proposal_calls]
    assert dg_proposal_calls == expected_calls

    dg_proposal_details = emergency_protected_timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)

    if dg_proposal_details["status"] == 3:
        print("DG proposal already executed. Skipping DG Proposal tests.")

    # Check if DG proposal is not executed
    if dg_proposal_details["status"] != 3:
        # =======================================================================
        # ========================= Before DG Proposal tests ====================
        # =======================================================================

        assert emergency_protected_timelock.getGovernance() == DUAL_GOVERNANCE
        assert dual_governance.getConfigProvider() == CONFIG_PROVIDER_FOR_ACTIVE_DUAL_GOVERNANCE

        assert new_dual_governance.getConfigProvider() == CONFIG_PROVIDER_FOR_ACTIVE_DUAL_GOVERNANCE
        assert new_dual_governance.getResealCommittee() == ZERO_ADDRESS
        assert new_dual_governance.getProposalsCanceller() == ZERO_ADDRESS
        assert len(new_dual_governance.getProposers()) == 0
        assert new_dual_governance.getTiebreakerDetails() == (False, ZERO_ADDRESS, 0, [])

        # =======================================================================
        # ======================== DG Proposal Execution ========================
        # =======================================================================
        if emergency_protected_timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == 1:
            chain.sleep(emergency_protected_timelock.getAfterSubmitDelay() + 1)
            dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

        if emergency_protected_timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == 2:
            chain.sleep(emergency_protected_timelock.getAfterScheduleDelay() + 1)
            dg_tx: TransactionReceipt = emergency_protected_timelock.execute(
                EXPECTED_DG_PROPOSAL_ID, {"from": stranger}
            )

            display_dg_events(dg_tx)
            dg_events = group_dg_events_from_receipt(
                dg_tx, timelock=EMERGENCY_PROTECTED_TIMELOCK, admin_executor=ADMIN_EXECUTOR
            )

        assert emergency_protected_timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == 3

        # =======================================================================
        # ========================= DG Events checks ============================
        # =======================================================================

        # Validate after DG proposal execution events count
        assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

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

        validate_dual_governance_proposer_registered_event(
            dg_events[4],
            proposer=VOTING,
            executor=ADMIN_EXECUTOR,
            emitted_by=NEW_DUAL_GOVERNANCE,
        )

        validate_dual_governance_proposals_canceller_set_event(
            dg_events[5],
            canceller=VOTING,
            emitted_by=NEW_DUAL_GOVERNANCE,
        )

        validate_dual_governance_reseal_committee_set_event(
            dg_events[6],
            committee=RESEAL_COMMITTEE,
            emitted_by=NEW_DUAL_GOVERNANCE,
        )

        validate_timelock_governance_set_event(
            dg_events[7],
            governance=NEW_DUAL_GOVERNANCE,
            proposals_cancelled_till=expected_dg_proposal_id,
            emitted_by=EMERGENCY_PROTECTED_TIMELOCK,
        )

        validate_dual_governance_config_provider_set_event(
            dg_events[8],
            config_provider=CONFIG_PROVIDER_FOR_DISCONNECTED_DUAL_GOVERNANCE,
            min_assets_lock_duration=MIN_ASSETS_LOCK_DURATION,
            emitted_by=DUAL_GOVERNANCE,
        )

        validate_dual_governance_state_verified_event(
            dg_events[9],
            emitted_by=DG_UPGRADE_STATE_VERIFIER,
        )

        validate_dual_governance_agent_forward_token_transfer_event(
            dg_events[10],
            amount=MATIC_BALANCE_TO_TRANSFER,
            from_address=AGENT,
            to_address=LABS_BORG_FOUNDATION,
            emitted_by=MATIC_TOKEN,
        )

    # =======================================================================
    # ================= After DG proposal execution tests ===================
    # =======================================================================

    assert emergency_protected_timelock.getGovernance() == NEW_DUAL_GOVERNANCE
    assert dual_governance.getConfigProvider() == CONFIG_PROVIDER_FOR_DISCONNECTED_DUAL_GOVERNANCE

    assert new_dual_governance.getConfigProvider() == CONFIG_PROVIDER_FOR_ACTIVE_DUAL_GOVERNANCE
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
        [WITHDRAWAL_QUEUE, VALIDATORS_EXIT_BUS_ORACLE],
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

    last_proposal_id_before = emergency_protected_timelock.getProposalsCount()
    # Test that new DG can submit proposals
    new_dual_governance.submitProposal(some_proposal_calls, "This should not revert", {"from": VOTING})
    assert emergency_protected_timelock.getProposalsCount() == last_proposal_id_before + 1

    # Test that old escrow won't get into Rage Quit if lock amount above previous 2nd seal
    old_escrow = interface.DualGovernanceEscrow(dual_governance.getVetoSignallingEscrow())
    new_escrow = interface.DualGovernanceEscrow(new_dual_governance.getVetoSignallingEscrow())

    disconnected_dual_governance_second_seal = interface.IDualGovernanceConfigProvider(
        dual_governance.getConfigProvider()
    ).SECOND_SEAL_RAGE_QUIT_SUPPORT()
    assert (
        disconnected_dual_governance_second_seal
        == interface.IDualGovernanceConfigProvider(
            CONFIG_PROVIDER_FOR_DISCONNECTED_DUAL_GOVERNANCE
        ).SECOND_SEAL_RAGE_QUIT_SUPPORT()
    )

    new_dual_governance_second_seal = interface.IDualGovernanceConfigProvider(
        new_dual_governance.getConfigProvider()
    ).SECOND_SEAL_RAGE_QUIT_SUPPORT()

    steth_total_supply = steth_token.totalSupply()

    # 20% steth of total supply is greater than previous 2nd seal - 10%
    steth_to_lock = steth_total_supply * 0.2

    # wstETH address as whale
    steth_whale = accounts.at(STETH_WHALE, force=True)
    steth_token.approve(old_escrow.address, steth_to_lock, {"from": steth_whale})

    old_dual_governance_rage_quit_support_before = old_escrow.getRageQuitSupport()
    new_dual_governance_rage_quit_support_before = new_escrow.getRageQuitSupport()

    old_escrow.lockStETH(steth_to_lock, {"from": steth_whale})

    assert old_escrow.getRageQuitSupport() > old_dual_governance_rage_quit_support_before
    assert new_escrow.getRageQuitSupport() == new_dual_governance_rage_quit_support_before

    assert old_escrow.getRageQuitSupport() < disconnected_dual_governance_second_seal
    assert old_escrow.getRageQuitSupport() > new_dual_governance_second_seal

    chain.sleep(old_escrow.getMinAssetsLockDuration() + 1)
    old_escrow.unlockStETH({"from": steth_whale})

    assert old_escrow.getRageQuitSupport() == old_dual_governance_rage_quit_support_before


def validate_dual_governance_agent_forward_token_transfer_event(
    event: EventDict, amount: int, from_address: str, to_address: str, emitted_by: str
) -> None:
    _events_chain = ["LogScriptCall", "Transfer", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("Transfer") == 1

    assert event["Transfer"]["_from"] == from_address
    assert event["Transfer"]["_to"] == to_address
    assert event["Transfer"]["_amount"] == amount

    assert web3.to_checksum_address(event["Transfer"]["_emitted_by"]) == web3.to_checksum_address(
        emitted_by
    ), "Wrong event emitter"


def validate_dual_governance_state_verified_event(event: EventDict, emitted_by: str) -> None:
    _events_chain = ["DGUpgradeConfigurationValidated", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("DGUpgradeConfigurationValidated") == 1

    assert web3.to_checksum_address(
        event["DGUpgradeConfigurationValidated"]["_emitted_by"]
    ) == web3.to_checksum_address(emitted_by), "Wrong event emitter"
