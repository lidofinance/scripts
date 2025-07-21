from brownie import interface, chain, convert
from brownie.network.transaction import TransactionReceipt

from scripts.vote_2025_07_16 import start_vote

from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.staking_router import validate_staking_module_update_event, StakingModuleItem
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.csm import validate_set_key_removal_charge_event
from utils.test.csm_helpers import csm_add_node_operator, get_ea_member

from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    validate_node_operator_reward_address_set_event,
    NodeOperatorNameSetItem,
    NodeOperatorRewardAddressSetItem,
)

from utils.config import (
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)

from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_removed_event,
)

from utils.test.event_validators.hash_consensus import (
    validate_hash_consensus_member_removed,
    validate_hash_consensus_member_added,
)

# Contract addresses
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
CSM = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"
CS_ACCOUNTING = "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da"
HASH_CONSENSUS_FOR_AO = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
HASH_CONSENSUS_FOR_VEBO = "0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"
CS_FEE_HASH_CONSENSUS = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
CSM_IMPL = "0x8daEa53b17a629918CDFAB785C5c74077c1D895B"
DUAL_GOVERNANCE = "0xcdF49b058D606AD34c5789FD8c3BF8B3E54bA2db"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
LIDO_AND_STETH = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"

PML_STABLECOINS_FACTORY = "0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D"
PML_STETH_FACTORY = "0xc5527396DDC353BD05bBA578aDAa1f5b6c721136"

ATC_STABLECOINS_FACTORY = "0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab"
ATC_STETH_FACTORY = "0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9"

RCC_STABLECOINS_FACTORY = "0x75bDecbb6453a901EBBB945215416561547dfDD4"
RCC_STETH_FACTORY = "0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35"

KYBER_ORACLE_MEMBER = "0xA7410857ABbf75043d61ea54e07D57A6EB6EF186"
CALIBER_ORACLE_MEMBER = "0x4118DAD7f348A4063bD15786c299De2f3B1333F3"

CS_VERIFIER_ADDRESS_OLD = "0x0c345dFa318f9F4977cdd4f33d80F9D0ffA38e8B"
CS_VERIFIER_ADDRESS_NEW = "0xeC6Cc185f671F627fb9b6f06C8772755F587b05d"

NODE_OPERATORS_REGISTRY = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"

P2P_NO_STAKING_REWARDS_ADDRESS_OLD = "0x9a66fd7948a6834176fbb1c4127c61cb6d349561"
P2P_NO_STAKING_REWARDS_ADDRESS_NEW = "0xfeef177E6168F9b7fd59e6C5b6c2d87FF398c6FD"

# Parameters

CSM_MODULE_ID = 3

KEY_REMOVAL_CHARGE_BEFORE = 0.02 * 10 ** 18
KEY_REMOVAL_CHARGE_AFTER = 0

CSM_STAKE_SHARE_LIMIT_BEFORE = 200
CSM_STAKE_SHARE_LIMIT_AFTER = 300

CSM_PRIORITY_EXIT_SHARE_THRESHOLD_BEFORE = 250
CSM_PRIORITY_EXIT_SHARE_THRESHOLD_AFTER = 375

CSM_TREASURY_FEE_BEFORE = 400
CSM_STAKING_MODULE_FEE_BEFORE = 600
CSM_MAX_DEPOSITS_PER_BLOCK_BEFORE = 30
CSM_MIN_DEPOSIT_BLOCK_DISTANCE_BEFORE = 25

HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM = 5


HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_NUMBER_OF_ORACLES = 9
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_NUMBER_OF_ORACLES = 9
HASH_CONSENSUS_FOR_CS_FEE_ORACLE_NUMBER_OF_ORACLES = 9


P2P_NO_ID = 2
P2P_NO_NAME_OLD = "P2P.ORG - P2P Validator"
P2P_NO_NAME_NEW = "P2P.org"

EXPECTED_VOTE_EVENTS_COUNT = 7  # 6 events after the vote + ProposalSubmitted event
EXPECTED_DG_EVENTS_COUNT = 14  # 14 vote items are going through DG
EXPECTED_TOTAL_EVENTS_COUNT = 21

EXPECTED_DG_PROPOSAL_ID = 3

# TODO: To be defined
IPFS_DESCRIPTION_HASH = ''


def test_vote(helpers, accounts, vote_ids_from_env, stranger):
    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================

    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    easy_track = interface.EasyTrack(EASY_TRACK)
    csm = interface.CSModule(CSM)
    hash_consensus_for_accounting_oracle = interface.HashConsensus(HASH_CONSENSUS_FOR_AO)
    hash_consensus_for_validators_exit_bus_oracle = interface.HashConsensus(HASH_CONSENSUS_FOR_VEBO)
    cs_fee_hash_consensus = interface.HashConsensus(CS_FEE_HASH_CONSENSUS)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    emergency_protected_timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    accounting = interface.CSAccounting(CS_ACCOUNTING)
    no_registry = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)

    # CSM roles
    csm_verifier_role = csm.VERIFIER_ROLE()
    csm_module_manager_role = csm.MODULE_MANAGER_ROLE()

    # =======================================================================
    # ========================= Before voting tests =========================
    # =======================================================================

    """
    V. PML, ATC, RCC ET Factories Removal

    Vote items #15 - #20

    Validate PML, ATC, RCC ET Factories existence before removal
    """
    evm_script_factories_before = easy_track.getEVMScriptFactories()

    assert PML_STABLECOINS_FACTORY in evm_script_factories_before
    assert PML_STETH_FACTORY in evm_script_factories_before
    assert ATC_STABLECOINS_FACTORY in evm_script_factories_before
    assert ATC_STETH_FACTORY in evm_script_factories_before
    assert RCC_STABLECOINS_FACTORY in evm_script_factories_before
    assert RCC_STETH_FACTORY in evm_script_factories_before

    # =======================================================================
    # ============================== Voting =================================
    # =======================================================================

    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx: TransactionReceipt = helpers.execute_vote(accounts, vote_id, voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    proposal_id = vote_tx.events["ProposalSubmitted"][1]["proposalId"]
    print(f"proposalId = {proposal_id}")

    assert proposal_id == EXPECTED_DG_PROPOSAL_ID

    display_voting_events(vote_tx)
    voting_events = group_voting_events(vote_tx)

    # =======================================================================
    # ========================= After voting tests ==========================
    # =======================================================================

    """
    V. PML, ATC, RCC ET Factories Removal

    Vote items #15 - #20

    Validate PML, ATC, RCC ET Factories don't exist after vote
    """
    evm_script_factories_after = easy_track.getEVMScriptFactories()

    assert not PML_STABLECOINS_FACTORY in evm_script_factories_after
    assert not PML_STETH_FACTORY in evm_script_factories_after
    assert not ATC_STABLECOINS_FACTORY in evm_script_factories_after
    assert not ATC_STETH_FACTORY in evm_script_factories_after
    assert not RCC_STABLECOINS_FACTORY in evm_script_factories_after
    assert not RCC_STETH_FACTORY in evm_script_factories_after

    assert len(evm_script_factories_after) == len(evm_script_factories_before) - 6

    # =======================================================================
    # ====================== Before DG Proposal tests =======================
    # =======================================================================

    """
    I. Kyber Oracle Rotation

    Vote items #1 - #6

    Validate Kyber oracle member existence on:
    - HashConsensus(0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288) for AccountingOracle(0x852deD011285fe67063a08005c71a85690503Cee),
    - HashConsensus(0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a) for ValidatorsExitBusOracle(0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e),
    - CSHashConsensus(0x71093efF8D8599b5fA340D665Ad60fA7C80688e4) for CSFeeOracle(0x4D4074628678Bd302921c20573EEa1ed38DdF7FB)

    Validate Caliber oracle member doesn't exist on:
    - HashConsensus(0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288) for AccountingOracle(0x852deD011285fe67063a08005c71a85690503Cee),
    - HashConsensus(0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a) for ValidatorsExitBusOracle(0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e),
    - CSHashConsensus(0x71093efF8D8599b5fA340D665Ad60fA7C80688e4) for CSFeeOracle(0x4D4074628678Bd302921c20573EEa1ed38DdF7FB)
    """
    assert hash_consensus_for_accounting_oracle.getIsMember(KYBER_ORACLE_MEMBER)
    assert hash_consensus_for_validators_exit_bus_oracle.getIsMember(KYBER_ORACLE_MEMBER)
    assert cs_fee_hash_consensus.getIsMember(KYBER_ORACLE_MEMBER)

    assert not hash_consensus_for_accounting_oracle.getIsMember(CALIBER_ORACLE_MEMBER)
    assert not hash_consensus_for_validators_exit_bus_oracle.getIsMember(CALIBER_ORACLE_MEMBER)
    assert not cs_fee_hash_consensus.getIsMember(CALIBER_ORACLE_MEMBER)

    hash_consensus_for_accounting_oracle_quorum_before = hash_consensus_for_accounting_oracle.getQuorum()
    hash_consensus_for_validators_exit_bus_oracle_quorum_before = hash_consensus_for_validators_exit_bus_oracle.getQuorum()
    cs_fee_hash_consensus_quorum_before = cs_fee_hash_consensus.getQuorum()

    assert hash_consensus_for_accounting_oracle_quorum_before == HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
    assert hash_consensus_for_validators_exit_bus_oracle_quorum_before == HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM
    assert cs_fee_hash_consensus_quorum_before == HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM

    hash_consensus_for_accounting_oracle_number_of_oracles_before = len(hash_consensus_for_accounting_oracle.getMembers()[0])
    hash_consensus_for_validators_exit_bus_oracle_number_of_oracles_before = len(hash_consensus_for_validators_exit_bus_oracle.getMembers()[0])
    cs_fee_hash_consensus_quorum_before_number_of_oracles_before = len(cs_fee_hash_consensus.getMembers()[0])

    assert hash_consensus_for_accounting_oracle_number_of_oracles_before == HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_NUMBER_OF_ORACLES
    assert hash_consensus_for_validators_exit_bus_oracle_number_of_oracles_before == HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_NUMBER_OF_ORACLES
    assert cs_fee_hash_consensus_quorum_before_number_of_oracles_before == HASH_CONSENSUS_FOR_CS_FEE_ORACLE_NUMBER_OF_ORACLES

    """
    II. CSM Parameters Change

    Vote item #7 - Validate parameters before changing on Staking Router for CSModule
    Vote items #8, #10 - validate agent has no MODULE_MANAGER_ROLE on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) before vote
    Vote item #9 - validate keyRemovalCharge value on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) before vote
    """

    # Vote item 7
    assert staking_router.getStakingModule(CSM_MODULE_ID)["stakeShareLimit"] == CSM_STAKE_SHARE_LIMIT_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)[
               "priorityExitShareThreshold"] == CSM_PRIORITY_EXIT_SHARE_THRESHOLD_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["stakingModuleFee"] == CSM_STAKING_MODULE_FEE_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["treasuryFee"] == CSM_TREASURY_FEE_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["maxDepositsPerBlock"] == CSM_MAX_DEPOSITS_PER_BLOCK_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)[
               "minDepositBlockDistance"] == CSM_MIN_DEPOSIT_BLOCK_DISTANCE_BEFORE

    # Vote items #8, #10
    assert not csm.hasRole(csm_module_manager_role, agent)

    # Vote item #9
    assert csm.keyRemovalCharge() == KEY_REMOVAL_CHARGE_BEFORE

    """
    III. CS Verifier rotation

    Vote items #11 - #12 - verify roles before vote
    """
    assert csm.hasRole(csm_verifier_role, CS_VERIFIER_ADDRESS_OLD)
    assert not csm.hasRole(csm_verifier_role, CS_VERIFIER_ADDRESS_NEW)

    """
    IV. Change staking reward address and name for P2P.org Node Operator

    Vote items #13, #14
    """

    p2p_no_data_before = no_registry.getNodeOperator(P2P_NO_ID, True)

    # Vote item #13
    assert p2p_no_data_before["rewardAddress"] == P2P_NO_STAKING_REWARDS_ADDRESS_OLD

    # Vote item #14
    assert p2p_no_data_before["name"] == P2P_NO_NAME_OLD

    # =======================================================================
    # ==================== DG Proposal Submit => Execute ====================
    # =======================================================================

    chain.sleep(emergency_protected_timelock.getAfterSubmitDelay() + 1)
    dual_governance.scheduleProposal(proposal_id, {"from": stranger})
    chain.sleep(emergency_protected_timelock.getAfterScheduleDelay() + 1)
    dg_tx: TransactionReceipt = emergency_protected_timelock.execute(proposal_id, {"from": stranger})

    display_dg_events(dg_tx)
    dg_events = group_dg_events_from_receipt(dg_tx, timelock=EMERGENCY_PROTECTED_TIMELOCK, admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR)

    # =======================================================================
    # ================= After DG proposal execution tests ===================
    # =======================================================================

    """I. Kyber Oracle Rotation"""
    assert not hash_consensus_for_accounting_oracle.getIsMember(KYBER_ORACLE_MEMBER)
    assert not hash_consensus_for_validators_exit_bus_oracle.getIsMember(KYBER_ORACLE_MEMBER)
    assert not cs_fee_hash_consensus.getIsMember(KYBER_ORACLE_MEMBER)

    assert hash_consensus_for_accounting_oracle.getIsMember(CALIBER_ORACLE_MEMBER)
    assert hash_consensus_for_validators_exit_bus_oracle.getIsMember(CALIBER_ORACLE_MEMBER)
    assert cs_fee_hash_consensus.getIsMember(CALIBER_ORACLE_MEMBER)

    hash_consensus_for_accounting_oracle_quorum_after = hash_consensus_for_accounting_oracle.getQuorum()
    hash_consensus_for_validators_exit_bus_oracle_quorum_after = hash_consensus_for_validators_exit_bus_oracle.getQuorum()
    cs_fee_hash_consensus_quorum_after = cs_fee_hash_consensus.getQuorum()

    assert hash_consensus_for_accounting_oracle_quorum_after == HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
    assert hash_consensus_for_validators_exit_bus_oracle_quorum_after == HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM
    assert cs_fee_hash_consensus_quorum_after == HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM

    hash_consensus_for_accounting_oracle_number_of_oracles_after = len(hash_consensus_for_accounting_oracle.getMembers()[0])
    hash_consensus_for_validators_exit_bus_oracle_number_of_oracles_after = len(hash_consensus_for_validators_exit_bus_oracle.getMembers()[0])
    cs_fee_hash_consensus_quorum_before_number_of_oracles_after = len(cs_fee_hash_consensus.getMembers()[0])

    assert hash_consensus_for_accounting_oracle_number_of_oracles_after == HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_NUMBER_OF_ORACLES
    assert hash_consensus_for_validators_exit_bus_oracle_number_of_oracles_after == HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_NUMBER_OF_ORACLES
    assert cs_fee_hash_consensus_quorum_before_number_of_oracles_after == HASH_CONSENSUS_FOR_CS_FEE_ORACLE_NUMBER_OF_ORACLES

    """II. CSM Parameters Change (Vote items #7 - #10)"""

    # Vote item #7
    # stakeShareLimit and priorityExitShareThreshold updates
    assert staking_router.getStakingModule(CSM_MODULE_ID)["stakeShareLimit"] == CSM_STAKE_SHARE_LIMIT_AFTER
    assert staking_router.getStakingModule(CSM_MODULE_ID)["priorityExitShareThreshold"] == CSM_PRIORITY_EXIT_SHARE_THRESHOLD_AFTER
    assert staking_router.getStakingModule(CSM_MODULE_ID)["stakingModuleFee"] == CSM_STAKING_MODULE_FEE_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["treasuryFee"] == CSM_TREASURY_FEE_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["maxDepositsPerBlock"] == CSM_MAX_DEPOSITS_PER_BLOCK_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["minDepositBlockDistance"] == CSM_MIN_DEPOSIT_BLOCK_DISTANCE_BEFORE

    # Vote item #9
    # Validate new keyRemovalCharge value
    assert csm.keyRemovalCharge() == KEY_REMOVAL_CHARGE_AFTER

    # Vote item #10
    # Validate Agent doesn't have MODULE_MANAGER_ROLE on CSM
    assert not csm.hasRole(csm_module_manager_role, agent)

    # Scenario
    address, proof = get_ea_member()
    node_operator = csm_add_node_operator(csm, accounting, address, proof)

    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]

    remove_keys_tx = csm.removeKeys(node_operator, 0, 1, {"from": manager_address})

    assert "SigningKeyRemoved" in remove_keys_tx.events
    assert "TotalSigningKeysCountChanged" in remove_keys_tx.events
    assert "VettedSigningKeysCountChanged" in remove_keys_tx.events
    assert "DepositableSigningKeysCountChanged" in remove_keys_tx.events

    # Verify charge-related events are NOT emitted when charge == 0
    assert "KeyRemovalChargeApplied" not in remove_keys_tx.events, "KeyRemovalChargeApplied should not be emitted when charge is 0"
    assert "BondCharged" not in remove_keys_tx.events, "BondCharged should not be emitted when charge is 0"

    """IV. CS Verifier rotation (Vote items #11 - #12)"""

    # Validate CS Verifier rotation
    assert not csm.hasRole(csm_verifier_role, CS_VERIFIER_ADDRESS_OLD)
    assert csm.hasRole(csm_verifier_role, CS_VERIFIER_ADDRESS_NEW)

    """
    V. Change staking reward address and name for P2P.org Node Operator

    Vote items #13, #14
    """

    p2p_no_data_after = no_registry.getNodeOperator(P2P_NO_ID, True)

    # Vote item #13
    assert p2p_no_data_after["rewardAddress"] == P2P_NO_STAKING_REWARDS_ADDRESS_NEW

    # Vote item #14
    assert p2p_no_data_after["name"] == P2P_NO_NAME_NEW


    # =======================================================================
    # ======================== IPFS & events checks =========================
    # =======================================================================

    # TODO: Uncomment when the IPFS description is defined
    # metadata = find_metadata_by_vote_id(vote_id)
    # assert get_lido_vote_cid_from_str(metadata) == IPFS_DESCRIPTION_HASH

    """Validating events"""

    # Validate after voting events count
    count_vote_items_by_voting_events = count_vote_items_by_events(vote_tx, voting)
    assert count_vote_items_by_voting_events == EXPECTED_VOTE_EVENTS_COUNT
    # There's 6 vote items not going through DG + ProposalSubmitted event
    assert len(voting_events) == EXPECTED_VOTE_EVENTS_COUNT

    # Validate after DG proposal execution events count
    count_vote_items_by_agent_events = count_vote_items_by_events(dg_tx, agent)
    assert count_vote_items_by_agent_events == EXPECTED_DG_EVENTS_COUNT
    # 14 Vote items are going through DG
    assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

    # Validate total events count
    assert count_vote_items_by_voting_events + count_vote_items_by_agent_events == EXPECTED_TOTAL_EVENTS_COUNT, "Incorrect voting items count"

    # Validate PML, ATC, RCC ET Factories removal events
    validate_evmscript_factory_removed_event(voting_events[1], PML_STABLECOINS_FACTORY, emitted_by=EASY_TRACK)
    validate_evmscript_factory_removed_event(voting_events[2], PML_STETH_FACTORY, emitted_by=EASY_TRACK)
    validate_evmscript_factory_removed_event(voting_events[3], ATC_STABLECOINS_FACTORY, emitted_by=EASY_TRACK)
    validate_evmscript_factory_removed_event(voting_events[4], ATC_STETH_FACTORY, emitted_by=EASY_TRACK)
    validate_evmscript_factory_removed_event(voting_events[5], RCC_STABLECOINS_FACTORY, emitted_by=EASY_TRACK)
    validate_evmscript_factory_removed_event(voting_events[6], RCC_STETH_FACTORY, emitted_by=EASY_TRACK)

    # Validate oracle rotation events
    validate_hash_consensus_member_removed(
        dg_events[0],
        KYBER_ORACLE_MEMBER,
        5,
        new_total_members=8,
        emitted_by=HASH_CONSENSUS_FOR_AO,
        is_dg_event=True
    )
    validate_hash_consensus_member_removed(
        dg_events[1],
        KYBER_ORACLE_MEMBER,
        5,
        new_total_members=8,
        emitted_by=HASH_CONSENSUS_FOR_VEBO,
        is_dg_event=True
    )
    validate_hash_consensus_member_removed(
        dg_events[2],
        KYBER_ORACLE_MEMBER,
        5,
        new_total_members=8,
        emitted_by=CS_FEE_HASH_CONSENSUS,
        is_dg_event=True
    )
    validate_hash_consensus_member_added(
        dg_events[3],
        CALIBER_ORACLE_MEMBER,
        5,
        emitted_by=HASH_CONSENSUS_FOR_AO,
        new_total_members=9,
        is_dg_event=True
    )
    validate_hash_consensus_member_added(
        dg_events[4],
        CALIBER_ORACLE_MEMBER,
        5,
        new_total_members=9,
        emitted_by=HASH_CONSENSUS_FOR_VEBO,
        is_dg_event=True
    )
    validate_hash_consensus_member_added(
        dg_events[5],
        CALIBER_ORACLE_MEMBER,
        5,
        new_total_members=9,
        emitted_by=CS_FEE_HASH_CONSENSUS,
        is_dg_event=True
    )

    # Validate keyRemovalCharge update from 0.02 to 0 ETH
    expected_staking_module_item = StakingModuleItem(
        id=CSM_MODULE_ID,
        name="Community Staking",
        address=None,
        target_share=CSM_STAKE_SHARE_LIMIT_AFTER,
        module_fee=CSM_STAKING_MODULE_FEE_BEFORE,
        treasury_fee=CSM_TREASURY_FEE_BEFORE,
        priority_exit_share=CSM_PRIORITY_EXIT_SHARE_THRESHOLD_AFTER,
    )
    validate_staking_module_update_event(dg_events[6], expected_staking_module_item, emitted_by=STAKING_ROUTER,
                                         is_dg_event=True)

    # Validate grant MODULE_MANAGER_ROLE event
    validate_grant_role_event(dg_events[7], csm_module_manager_role, agent, agent.address, emitted_by=CSM,
                              is_dg_event=True)

    # Validate keyRemovalCharge update event
    validate_set_key_removal_charge_event(dg_events[8], KEY_REMOVAL_CHARGE_AFTER, emitted_by=CSM, is_dg_event=True)

    # Validate revoke MODULE_MANAGER_ROLE event
    validate_revoke_role_event(dg_events[9], csm_module_manager_role, agent, agent.address, emitted_by=CSM,
                               is_dg_event=True)

    # Validate old CS Verifier doesn't have VERIFIER_ROLE
    validate_revoke_role_event(dg_events[10], csm_verifier_role, CS_VERIFIER_ADDRESS_OLD, agent, emitted_by=CSM,
                               is_dg_event=True)

    # Validate new CS Verifier has VERIFIER_ROLE
    validate_grant_role_event(dg_events[11], csm_verifier_role, CS_VERIFIER_ADDRESS_NEW, agent,
                              emitted_by=CSM, is_dg_event=True)

    # Validate P2P NO rewards address change
    validate_node_operator_reward_address_set_event(
        dg_events[12],
        NodeOperatorRewardAddressSetItem(
            nodeOperatorId=P2P_NO_ID,
            reward_address=P2P_NO_STAKING_REWARDS_ADDRESS_NEW
        ),
        emitted_by=no_registry,
        is_dg_event=True
    )

    # Validate P2P NO name change
    validate_node_operator_name_set_event(
        dg_events[13], NodeOperatorNameSetItem(nodeOperatorId=P2P_NO_ID, name=P2P_NO_NAME_NEW), emitted_by=no_registry, is_dg_event=True
    )
