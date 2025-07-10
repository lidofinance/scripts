from brownie import interface, chain, convert
from brownie.network.transaction import TransactionReceipt

from scripts.vote_2025_07_16 import start_vote

from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.staking_router import validate_staking_module_update_event, StakingModuleItem
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event, \
    validate_dual_governance_grant_role_event
from utils.test.event_validators.csm import validate_set_key_removal_charge_event
from utils.test.csm_helpers import csm_add_node_operator, get_ea_member

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
CSM_MIN_DEPOSIT_BLOCK_DISTANCE = 25

# To be defined
IPFS_DESCRIPTION_HASH = ''


def test_vote(helpers, accounts, vote_ids_from_env, stranger):
    # Contracts definition
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
    lido = interface.Lido(LIDO_AND_STETH)
    accounting = interface.CSAccounting(CS_ACCOUNTING)

# CSM roles
    csm_verifier_role = csm.VERIFIER_ROLE()
    csm_module_manager_role = csm.MODULE_MANAGER_ROLE()

    # =======================================================================
    # ========================= Before voting tests =========================
    # =======================================================================

    # I. PML, ATC, RCC ET Factories Removal (Vote items #1 - #6)
    validate_factories_existence_before_vote(easy_track)

    # II. Kyber Oracle Rotation (Vote items #7 - #12)
    validate_kyber_oracle_rotation_before_vote(
        hash_consensus_for_accounting_oracle,
        hash_consensus_for_validators_exit_bus_oracle,
        cs_fee_hash_consensus
    )

    # III. CSM Parameters Change
    # Vote item #13 - validate parameters before changing on Staking Router for CSModule
    validate_staking_module_parameters_before_vote(staking_router)

    # Vote items #14, #16 - validate agent has no MODULE_MANAGER_ROLE on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) before vote
    assert not csm.hasRole(csm_module_manager_role, agent)

    # Vote item #15 - validate keyRemovalCharge value on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) before vote
    assert csm.keyRemovalCharge() == KEY_REMOVAL_CHARGE_BEFORE

    # IV. CS Verifier rotation (Vote items #17 - #18)
    validate_cs_verifier_rotation_before_vote(csm, csm_verifier_role)

    # =======================================================================
    # ========================= Voting and Events ===========================
    # =======================================================================

    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
    vote_tx = helpers.execute_vote(accounts, vote_id, voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    proposal_id = vote_tx.events["ProposalSubmitted"][1]["proposalId"]
    print(f"proposalId = {proposal_id}")

    display_voting_events(vote_tx)

    voting_events = group_voting_events(vote_tx)

    # Uncomment when the IPFS description is defined

    # metadata = find_metadata_by_vote_id(vote_id)
    # assert get_lido_vote_cid_from_str(metadata) == IPFS_DESCRIPTION_HASH

    # =======================================================================
    # ====================== After voting validation ========================
    # =======================================================================

    # There's 6 vote items not going through DG + ProposalSubmitted events
    assert len(voting_events) == 7

    # I. PML, ATC, RCC ET Factories Removal (Vote items #1 - #6)
    validate_factories_removal_after_vote(easy_track, voting_events[0:6])


    # =======================================================================
    # ==================== DG Proposal Submit => Execute ====================
    # =======================================================================

    chain.sleep(emergency_protected_timelock.getAfterSubmitDelay() + 1)

    dual_governance.scheduleProposal(proposal_id, {"from": stranger})

    chain.sleep(emergency_protected_timelock.getAfterScheduleDelay() + 1)

    dg_tx: TransactionReceipt = emergency_protected_timelock.execute(proposal_id, {"from": stranger})

    display_dg_events(dg_tx)
    dg_events = group_dg_events(dg_tx)

    # 12 Vote items are going through DG
    assert len(dg_events) == 12

    # =======================================================================
    # ================= After proposal execution validation =================
    # =======================================================================

    # II. Kyber Oracle Rotation (Vote items #7 - #12)
    validate_kyber_oracle_rotation_after_proposal_execution(
        hash_consensus_for_accounting_oracle,
        hash_consensus_for_validators_exit_bus_oracle,
        cs_fee_hash_consensus,
        dg_events[0:6],
    )

    # III. CSM Parameters Change (Vote items #13 - #16)
    validate_csm_parameters_change_after_proposal_execution(
        staking_router,
        csm,
        csm_module_manager_role,
        agent,
        accounting,
        dg_events[6:10],
    )

    # IV. CS Verifier rotation (Vote items #17 - #18)
    validate_cs_verifier_rotation_after_proposal_execution(csm, csm_verifier_role, agent, dg_events[10:])

    # Validating events
    count_vote_items_by_voting_events = count_vote_items_by_events(vote_tx, voting)
    count_vote_items_by_agent_events = count_vote_items_by_events(dg_tx, agent)

    assert count_vote_items_by_voting_events + count_vote_items_by_agent_events == 19, "Incorrect voting items count"

# =======================================================================
# ========================= Before voting validators ====================
# =======================================================================

"""
Vote items #1 - #6

Validate PML, ATC, RCC ET Factories existence before removal

- Check if PML stablecoins factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D exists on Easy Track
- Check if PML stETH factory 0xc5527396DDC353BD05bBA578aDAa1f5b6c721136 exists on Easy Track
- Check if ATC stablecoins factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab exists on Easy Track
- Check if ATC stETH factory 0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9 exists on Easy Track
- Check if RCC stablecoins factory 0x75bDecbb6453a901EBBB945215416561547dfDD4 exists on Easy Track
- Check if RCC stETH factory 0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35 exists on Easy Track
"""
def validate_factories_existence_before_vote(easy_track):
    evm_script_factories_before = easy_track.getEVMScriptFactories()

    assert PML_STABLECOINS_FACTORY in evm_script_factories_before
    assert PML_STETH_FACTORY in evm_script_factories_before
    assert ATC_STABLECOINS_FACTORY in evm_script_factories_before
    assert ATC_STETH_FACTORY in evm_script_factories_before
    assert RCC_STABLECOINS_FACTORY in evm_script_factories_before
    assert RCC_STETH_FACTORY in evm_script_factories_before

"""
Vote items #7 - #12

Validate Kyber oracle member existence on:
- HashConsensus(0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288) for AccountingOracle(0x852deD011285fe67063a08005c71a85690503Cee),
- HashConsensus(0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a) for ValidatorsExitBusOracle(0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e),
- CSHashConsensus(0x71093efF8D8599b5fA340D665Ad60fA7C80688e4) for CSFeeOracle(0x4D4074628678Bd302921c20573EEa1ed38DdF7FB)

Validate Caliber oracle member doesn't exist on:
- HashConsensus(0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288) for AccountingOracle(0x852deD011285fe67063a08005c71a85690503Cee),
- HashConsensus(0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a) for ValidatorsExitBusOracle(0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e),
- CSHashConsensus(0x71093efF8D8599b5fA340D665Ad60fA7C80688e4) for CSFeeOracle(0x4D4074628678Bd302921c20573EEa1ed38DdF7FB)
"""
def validate_kyber_oracle_rotation_before_vote(
    hash_consensus_for_accounting_oracle,
    hash_consensus_for_validators_exit_bus_oracle,
    cs_fee_hash_consensus
):
    assert hash_consensus_for_accounting_oracle.getIsMember(KYBER_ORACLE_MEMBER)
    assert hash_consensus_for_validators_exit_bus_oracle.getIsMember(KYBER_ORACLE_MEMBER)
    assert cs_fee_hash_consensus.getIsMember(KYBER_ORACLE_MEMBER)

    assert not hash_consensus_for_accounting_oracle.getIsMember(CALIBER_ORACLE_MEMBER)
    assert not hash_consensus_for_validators_exit_bus_oracle.getIsMember(CALIBER_ORACLE_MEMBER)
    assert not cs_fee_hash_consensus.getIsMember(CALIBER_ORACLE_MEMBER)
"""
Vote item #13

Validate parameters before changing stakeShareLimit from 200 BP to 300 BP and priorityExitShareThreshold from 250 to 375
on Staking Router(0xFdDf38947aFB03C621C71b06C9C70bce73f12999) for CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F)
"""
def validate_staking_module_parameters_before_vote(staking_router):
    assert staking_router.getStakingModule(CSM_MODULE_ID)["stakeShareLimit"] == CSM_STAKE_SHARE_LIMIT_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["priorityExitShareThreshold"] == CSM_PRIORITY_EXIT_SHARE_THRESHOLD_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["stakingModuleFee"] == CSM_STAKING_MODULE_FEE_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["treasuryFee"] == CSM_TREASURY_FEE_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["maxDepositsPerBlock"] == CSM_MAX_DEPOSITS_PER_BLOCK_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["minDepositBlockDistance"] == CSM_MIN_DEPOSIT_BLOCK_DISTANCE

"""
Vote items #17 - #18

- Validate old CS Verifier(0x0c345dFa318f9F4977cdd4f33d80F9D0ffA38e8B) has VERIFIER_ROLE on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) before vote
- Validate new CS Verifier(0xeC6Cc185f671F627fb9b6f06C8772755F587b05d) doesn't have VERIFIER_ROLE on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) before vote
"""
def validate_cs_verifier_rotation_before_vote(csm, csm_verifier_role):
    assert csm.hasRole(csm_verifier_role, CS_VERIFIER_ADDRESS_OLD)
    assert not csm.hasRole(csm_verifier_role, CS_VERIFIER_ADDRESS_NEW)


# =======================================================================
# ============ After voting / proposal execution validators =============
# =======================================================================

"""
Vote items #1 - #6

Validate PML, ATC, RCC ET Factories don't exist after vite

- Check if PML stablecoins factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D is removed from Easy Track
- Check if PML stETH factory 0xc5527396DDC353BD05bBA578aDAa1f5b6c721136 is removed from Easy Track
- Check if ATC stablecoins factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab is removed from Easy Track
- Check if ATC stETH factory 0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9 is removed from Easy Track
- Check if RCC stablecoins factory 0x75bDecbb6453a901EBBB945215416561547dfDD4 is removed from Easy Track
- Check if RCC stETH factory 0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35 is removed from Easy Track

- Validate PML, ATC, RCC ET Factories removal events
"""
def validate_factories_removal_after_vote(easy_track, events):
    evm_script_factories_after = easy_track.getEVMScriptFactories()

    assert not PML_STABLECOINS_FACTORY in evm_script_factories_after
    assert not PML_STETH_FACTORY in evm_script_factories_after
    assert not ATC_STABLECOINS_FACTORY in evm_script_factories_after
    assert not ATC_STETH_FACTORY in evm_script_factories_after
    assert not RCC_STABLECOINS_FACTORY in evm_script_factories_after
    assert not RCC_STETH_FACTORY in evm_script_factories_after

    validate_evmscript_factory_removed_event(events[0], PML_STABLECOINS_FACTORY)
    validate_evmscript_factory_removed_event(events[1], PML_STETH_FACTORY)
    validate_evmscript_factory_removed_event(events[2], ATC_STABLECOINS_FACTORY)
    validate_evmscript_factory_removed_event(events[3], ATC_STETH_FACTORY)
    validate_evmscript_factory_removed_event(events[4], RCC_STABLECOINS_FACTORY)
    validate_evmscript_factory_removed_event(events[5], RCC_STETH_FACTORY)


"""
Vote items #7 - #12

Validate Kyber oracle member doesn't exist on:
- HashConsensus(0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288) for AccountingOracle(0x852deD011285fe67063a08005c71a85690503Cee),
- HashConsensus(0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a) for ValidatorsExitBusOracle(0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e),
- CSHashConsensus(0x71093efF8D8599b5fA340D665Ad60fA7C80688e4) for CSFeeOracle(0x4D4074628678Bd302921c20573EEa1ed38DdF7FB)

Validate Caliber oracle member existence on:
- HashConsensus(0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288) for AccountingOracle(0x852deD011285fe67063a08005c71a85690503Cee),
- HashConsensus(0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a) for ValidatorsExitBusOracle(0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e),
- CSHashConsensus(0x71093efF8D8599b5fA340D665Ad60fA7C80688e4) for CSFeeOracle(0x4D4074628678Bd302921c20573EEa1ed38DdF7FB)

- Validate oracle rotation events
"""
def validate_kyber_oracle_rotation_after_proposal_execution(
    hash_consensus_for_accounting_oracle,
    hash_consensus_for_validators_exit_bus_oracle,
    cs_fee_hash_consensus,
    events
):
    assert not hash_consensus_for_accounting_oracle.getIsMember(KYBER_ORACLE_MEMBER)
    assert not hash_consensus_for_validators_exit_bus_oracle.getIsMember(KYBER_ORACLE_MEMBER)
    assert not cs_fee_hash_consensus.getIsMember(KYBER_ORACLE_MEMBER)

    assert hash_consensus_for_accounting_oracle.getIsMember(CALIBER_ORACLE_MEMBER)
    assert hash_consensus_for_validators_exit_bus_oracle.getIsMember(CALIBER_ORACLE_MEMBER)
    assert cs_fee_hash_consensus.getIsMember(CALIBER_ORACLE_MEMBER)

    validate_hash_consensus_member_removed(
        events[0],
        KYBER_ORACLE_MEMBER,
        5,
        new_total_members=8,
    )
    validate_hash_consensus_member_removed(
        events[1],
        KYBER_ORACLE_MEMBER,
        5,
        new_total_members=8,
    )
    validate_hash_consensus_member_removed(
        events[2],
        KYBER_ORACLE_MEMBER,
        5,
        new_total_members=8,
    )
    validate_hash_consensus_member_added(
        events[3],
        CALIBER_ORACLE_MEMBER,
        5,
        new_total_members=9,
    )
    validate_hash_consensus_member_added(
        events[4],
        CALIBER_ORACLE_MEMBER,
        5,
        new_total_members=9,
    )
    validate_hash_consensus_member_added(
        events[5],
        CALIBER_ORACLE_MEMBER,
        5,
        new_total_members=9,
    )


"""
Vote items #13 - #16

Vote item #13:
- Validate stakeShareLimit has changed from 200 BP to 300 BP and priorityExitShareThreshold from 250 to 375
on Staking Router(0xFdDf38947aFB03C621C71b06C9C70bce73f12999) for CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F)
and the rest of the values stood the same

- Validate CSM update event

Vote item #14-16:
- Validate grant MODULE_MANAGER_ROLE role event on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) to Aragon Agent(0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c)
- Validate keyRemovalCharge update from 0.02 to 0 ETH on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F event
- Validate keyRemovalCharge new value
- Validate revoke MODULE_MANAGER_ROLE role event on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) from Aragon Agent(0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c)
- Validate agent has no MODULE_MANAGER_ROLE on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) after proposal execution
"""

def validate_csm_parameters_change_after_proposal_execution(
    staking_router,
    csm,
    csm_module_manager_role,
    agent,
    accounting,
    events
):
    # stakeShareLimit and priorityExitShareThreshold updates
    assert staking_router.getStakingModule(CSM_MODULE_ID)["stakeShareLimit"] == CSM_STAKE_SHARE_LIMIT_AFTER
    assert staking_router.getStakingModule(CSM_MODULE_ID)["priorityExitShareThreshold"] == CSM_PRIORITY_EXIT_SHARE_THRESHOLD_AFTER
    assert staking_router.getStakingModule(CSM_MODULE_ID)["stakingModuleFee"] == CSM_STAKING_MODULE_FEE_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["treasuryFee"] == CSM_TREASURY_FEE_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["maxDepositsPerBlock"] == CSM_MAX_DEPOSITS_PER_BLOCK_BEFORE
    assert staking_router.getStakingModule(CSM_MODULE_ID)["minDepositBlockDistance"] == CSM_MIN_DEPOSIT_BLOCK_DISTANCE

    expected_staking_module_item = StakingModuleItem(
        id=CSM_MODULE_ID,
        name="Community Staking",
        address=None,
        target_share=CSM_STAKE_SHARE_LIMIT_AFTER,
        module_fee=CSM_STAKING_MODULE_FEE_BEFORE,
        treasury_fee=CSM_TREASURY_FEE_BEFORE,
        priority_exit_share=CSM_PRIORITY_EXIT_SHARE_THRESHOLD_AFTER,
    )

    validate_staking_module_update_event(events[0], expected_staking_module_item)

    # Grant MODULE_MANAGER_ROLE event
    validate_grant_role_event(events[1], csm_module_manager_role, agent, agent.address)

    # keyRemovalCharge update event
    validate_set_key_removal_charge_event(events[2], KEY_REMOVAL_CHARGE_AFTER, emitted_by=CSM_IMPL)

    # keyRemovalCharge new value
    assert csm.keyRemovalCharge() == KEY_REMOVAL_CHARGE_AFTER

    # Revoke MODULE_MANAGER_ROLE event
    validate_revoke_role_event(events[3], csm_module_manager_role, agent, agent.address)

    # scenario
    address, proof = get_ea_member()
    node_operator = csm_add_node_operator(csm, accounting, address, proof)

    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]

    tx = csm.removeKeys(node_operator, 0, 1, {"from": manager_address})

    assert "SigningKeyRemoved" in tx.events
    assert "TotalSigningKeysCountChanged" in tx.events
    assert "VettedSigningKeysCountChanged" in tx.events
    assert "DepositableSigningKeysCountChanged" in tx.events

    # Verify charge-related events are NOT emitted when charge = 0
    assert "KeyRemovalChargeApplied" not in tx.events, "KeyRemovalChargeApplied should not be emitted when charge is 0"
    assert "BondCharged" not in tx.events, "BondCharged should not be emitted when charge is 0"


"""
Vote items #17 - #18

- Validate old CS Verifier(0x0c345dFa318f9F4977cdd4f33d80F9D0ffA38e8B) doesn't have VERIFIER_ROLE on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) after proposal execution
- Validate new CS Verifier(0xeC6Cc185f671F627fb9b6f06C8772755F587b05d) has VERIFIER_ROLE on CSModule(0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F) after proposal execution

- Validate CS Verifier rotation events
"""
def validate_cs_verifier_rotation_after_proposal_execution(csm, csm_verifier_role, agent, events):
    assert not csm.hasRole(csm_verifier_role, CS_VERIFIER_ADDRESS_OLD)
    assert csm.hasRole(csm_verifier_role, CS_VERIFIER_ADDRESS_NEW)

    validate_revoke_role_event(events[0], csm_verifier_role, CS_VERIFIER_ADDRESS_OLD, agent, CSM_IMPL)
    validate_dual_governance_grant_role_event(events[1], csm_verifier_role, CS_VERIFIER_ADDRESS_NEW, agent,
                                              CSM_IMPL)
