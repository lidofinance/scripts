from brownie import chain, interface, web3, convert, accounts, reverts, ZERO_ADDRESS
from brownie.network.transaction import TransactionReceipt
import pytest

from brownie.network import state
from brownie.network.contract import Contract
import json

from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events
)
from utils.evm_script import encode_call_script
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event

from utils.agent import agent_forward
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.easy_track import create_permissions
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, validate_evmscript_factory_removed_event, EVMScriptFactoryAdded
from utils.test.easy_track_helpers import _encode_calldata, create_and_enact_motion


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.upgrade_2026_01_19_v3_phase_2 import start_vote, get_vote_items


# ============================================================================
# ============================== Constants ===================================
# ============================================================================

# Voting addresses
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
EASYTRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
EASYTRACK_EVMSCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

# Lido addresses
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
OPERATOR_GRID = "0xC69685E89Cefc327b43B7234AC646451B27c544d"
VAULT_HUB = "0x1d201BE093d847f6446530Efb0E8Fb426d176709"
LAZY_ORACLE = "0x5DB427080200c235F2Ae8Cd17A7be87921f7AD6c"
ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
VAULTS_FACTORY = "0x02Ca7772FF14a9F6c1a08aF385aA96bb1b34175A"
CS_HASH_CONSENSUS = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"
TWO_PHASE_FRAME_CONFIG_UPDATE = "0xb2B4DB1491cbe949ae85EfF01E0d3ee239f110C1"

# CSM module parameters
CSM_MODULE_ID = 3
CSM_MODULE_OLD_TARGET_SHARE_BP = 500  # 5%
CSM_MODULE_OLD_PRIORITY_EXIT_THRESHOLD_BP = 625  # 6.25%
CSM_MODULE_NEW_TARGET_SHARE_BP = 750  # 7.5%
CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 900  # 9%
CSM_MODULE_MODULE_FEE_BP = 600
CSM_MODULE_TREASURY_FEE_BP = 400
CSM_MODULE_MAX_DEPOSITS_PER_BLOCK = 30
CSM_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25

# Old Easy Track factories
ST_VAULTS_COMMITTEE = "0x18A1065c81b0Cc356F1b1C843ddd5E14e4AefffF"
OLD_VAULTS_ADAPTER = "0xe2DE6d2DefF15588a71849c0429101F8ca9FB14D"
OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0xa29173C7BCf39dA48D5E404146A652d7464aee14"
OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY = "0x194A46DA1947E98c9D79af13E06Cfbee0D8610cC"
OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0x8Bdc726a3147D8187820391D7c6F9F942606aEe6"
OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x93F1DEE4473Ee9F42c8257C201e33a6Da30E5d67"
OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0x1dF50522A1D868C12bF71747Bb6F24A18Fe6d32C"
OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6C968cD89CA358fbAf57B18e77a8973Fa869a6aA"
OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0x5C3bDFa3E7f312d8cf72F56F2b797b026f6B471c"

# New Easy Track factories
VAULTS_ADAPTER = "0xe2DE6d2DefF15588a71849c0429101F8ca9FB14D"  # TODO update address after deployment
ALTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0xa29173C7BCf39dA48D5E404146A652d7464aee14"  # TODO update address after deployment
REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY = "0x194A46DA1947E98c9D79af13E06Cfbee0D8610cC"  # TODO update address after deployment
UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0x8Bdc726a3147D8187820391D7c6F9F942606aEe6"  # TODO update address after deployment
SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x93F1DEE4473Ee9F42c8257C201e33a6Da30E5d67"  # TODO update address after deployment
SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0x1dF50522A1D868C12bF71747Bb6F24A18Fe6d32C"  # TODO update address after deployment
FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6C968cD89CA358fbAf57B18e77a8973Fa869a6aA"  # TODO update address after deployment
UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0x5C3bDFa3E7f312d8cf72F56F2b797b026f6B471c"  # TODO update address after deployment

# Test parameters
EXPECTED_VOTE_ID = 198
EXPECTED_DG_PROPOSAL_ID = 8
EXPECTED_VOTE_EVENTS_COUNT = 15
EXPECTED_DG_EVENTS_FROM_AGENT = 8  # 6 role revoke/grant + 1 CSM update + 1 CS HashConsensus role grant
EXPECTED_DG_EVENTS_COUNT = 8
IPFS_DESCRIPTION_HASH = ""  # TODO: Update after IPFS upload


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    """Returns list of dual governance proposal calls for events checking"""

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    vault_hub = interface.VaultHub(VAULT_HUB)
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)

    dg_items = [
        # 1.1. Revoke REGISTRY_ROLE on OperatorGrid from old VaultsAdapter
        agent_forward([
            encode_oz_revoke_role(operator_grid, "vaults.OperatorsGrid.Registry", OLD_VAULTS_ADAPTER)
        ]),

        # 1.2. Grant REGISTRY_ROLE on OperatorGrid to new VaultsAdapter
        agent_forward([
            encode_oz_grant_role(operator_grid, "vaults.OperatorsGrid.Registry", VAULTS_ADAPTER)
        ]),

        # 1.3. Revoke VALIDATOR_EXIT_ROLE on VaultHub from old VaultsAdapter
        agent_forward([
            encode_oz_revoke_role(vault_hub, "vaults.VaultHub.ValidatorExitRole", OLD_VAULTS_ADAPTER)
        ]),

        # 1.4. Grant VALIDATOR_EXIT_ROLE on VaultHub to new VaultsAdapter
        agent_forward([
            encode_oz_grant_role(vault_hub, "vaults.VaultHub.ValidatorExitRole", VAULTS_ADAPTER)
        ]),

        # 1.5. Revoke BAD_DEBT_MASTER_ROLE on VaultHub from old VaultsAdapter
        agent_forward([
            encode_oz_revoke_role(vault_hub, "vaults.VaultHub.BadDebtMasterRole", OLD_VAULTS_ADAPTER)
        ]),

        # 1.6. Grant BAD_DEBT_MASTER_ROLE on VaultHub to new VaultsAdapter
        agent_forward([
            encode_oz_grant_role(vault_hub, "vaults.VaultHub.BadDebtMasterRole", VAULTS_ADAPTER)
        ]),

        # 1.7. Raise CSM (MODULE_ID = 3) stake share limit from 500 BP to 750 BP and priority exit threshold from 625 BP to 900 BP
        agent_forward([
            (
                staking_router.address,
                staking_router.updateStakingModule.encode_input(
                    CSM_MODULE_ID,
                    CSM_MODULE_NEW_TARGET_SHARE_BP,
                    CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
                    CSM_MODULE_MODULE_FEE_BP,
                    CSM_MODULE_TREASURY_FEE_BP,
                    CSM_MODULE_MAX_DEPOSITS_PER_BLOCK,
                    CSM_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
                ),
            ),
        ]),

        # 1.8. Grant MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus to TwoPhaseFrameConfigUpdate
        agent_forward([
            encode_oz_grant_role(
                contract=cs_hash_consensus,
                role_name="MANAGE_FRAME_CONFIG_ROLE",
                grant_to=TWO_PHASE_FRAME_CONFIG_UPDATE,
            )
        ]),
    ]

    # Convert each dg_item to the expected format
    proposal_calls = []
    for dg_item in dg_items:
        target, data = dg_item  # agent_forward returns (target, data)
        proposal_calls.append({
            "target": target,
            "value": 0,
            "data": data
        })

    return proposal_calls


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    easy_track = interface.EasyTrack(EASYTRACK)

    vault_hub = interface.VaultHub(VAULT_HUB)
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    lazy_oracle = interface.LazyOracle(LAZY_ORACLE)
    vault_factory = interface.VaultFactory(VAULTS_FACTORY)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)

    registry_role = web3.keccak(text="vaults.OperatorsGrid.Registry")
    validator_exit_role = web3.keccak(text="vaults.VaultHub.ValidatorExitRole")
    bad_debt_master_role = web3.keccak(text="vaults.VaultHub.BadDebtMasterRole")
    manage_frame_config_role = web3.keccak(text="MANAGE_FRAME_CONFIG_ROLE")


    # =========================================================================
    # ======================== Identify or Create vote ========================
    # =========================================================================
    if vote_ids_from_env:
        vote_id = vote_ids_from_env[0]
        if EXPECTED_VOTE_ID is not None:
            assert vote_id == EXPECTED_VOTE_ID
    elif EXPECTED_VOTE_ID is not None and voting.votesLength() > EXPECTED_VOTE_ID:
        vote_id = EXPECTED_VOTE_ID
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    _, call_script_items = get_vote_items()
    onchain_script = voting.getVote(vote_id)["script"]
    assert onchain_script == encode_call_script(call_script_items)


    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        # Check old factories are present
        initial_factories = easy_track.getEVMScriptFactories()
        assert OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY in initial_factories, "EasyTrack should have OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY in initial_factories, "EasyTrack should have OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY in initial_factories, "EasyTrack should have OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY in initial_factories, "EasyTrack should have OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY factory before vote"
        assert OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY in initial_factories, "EasyTrack should have OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY factory before vote"
        assert OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY in initial_factories, "EasyTrack should have OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY factory before vote"
        assert OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY in initial_factories, "EasyTrack should have OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY factory before vote"

        # TODO Check new factories are not present yet (uncomment when new addresses are deployed)
        # assert ALTER_TIERS_IN_OPERATOR_GRID_FACTORY not in initial_factories
        # assert REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY not in initial_factories
        # assert UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY not in initial_factories
        # assert SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY not in initial_factories
        # assert SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY not in initial_factories
        # assert FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY not in initial_factories
        # assert UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY not in initial_factories

        # TODO Check IPFS description hash
        # assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        new_factories = easy_track.getEVMScriptFactories()

        # TODO Check old factories are removed (uncomment when testing on real vote)
        # assert OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY not in new_factories
        # assert OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY not in new_factories
        # assert OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY not in new_factories
        # assert OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY not in new_factories
        # assert OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY not in new_factories
        # assert OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY not in new_factories
        # assert OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY not in new_factories

        # Check new factories are added
        assert ALTER_TIERS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new ALTER_TIERS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY in new_factories, "EasyTrack should have new SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY factory after vote"
        assert FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY in new_factories, "EasyTrack should have new FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY factory after vote"
        assert UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY factory after vote"

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata="TODO DG proposal description",
                proposal_calls=dual_governance_proposal_calls,
            )

            # Validate EasyTrack factory removal/addition events
            vaults_adapter = interface.IVaultsAdapter(VAULTS_ADAPTER)

            # 2. Remove old ALTER_TIERS_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_removed_event(
                vote_events[1],
                factory_addr=OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY,
                emitted_by=easy_track,
            )

            # 3. Add new ALTER_TIERS_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_added_event(
                event=vote_events[2],
                p=EVMScriptFactoryAdded(
                    factory_addr=ALTER_TIERS_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(operator_grid, "alterTiers")
                ),
                emitted_by=easy_track,
            )

            # 4. Remove old REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_removed_event(
                vote_events[3],
                factory_addr=OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY,
                emitted_by=easy_track,
            )

            # 5. Add new REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_added_event(
                event=vote_events[4],
                p=EVMScriptFactoryAdded(
                    factory_addr=REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(operator_grid, "registerGroup") + create_permissions(operator_grid, "registerTiers")[2:]
                ),
                emitted_by=easy_track,
            )

            # 6. Remove old UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_removed_event(
                vote_events[5],
                factory_addr=OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY,
                emitted_by=easy_track,
            )

            # 7. Add new UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_added_event(
                event=vote_events[6],
                p=EVMScriptFactoryAdded(
                    factory_addr=UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(operator_grid, "updateGroupShareLimit")
                ),
                emitted_by=easy_track,
            )

            # 8. Remove old SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_removed_event(
                vote_events[7],
                factory_addr=OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY,
                emitted_by=easy_track,
            )

            # 9. Add new SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_added_event(
                event=vote_events[8],
                p=EVMScriptFactoryAdded(
                    factory_addr=SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(vaults_adapter, "setVaultJailStatus")
                ),
                emitted_by=easy_track,
            )

            # 10. Remove old SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY
            validate_evmscript_factory_removed_event(
                vote_events[9],
                factory_addr=OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY,
                emitted_by=easy_track,
            )

            # 11. Add new SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY
            validate_evmscript_factory_added_event(
                event=vote_events[10],
                p=EVMScriptFactoryAdded(
                    factory_addr=SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY,
                    permissions=create_permissions(vaults_adapter, "socializeBadDebt")
                ),
                emitted_by=easy_track,
            )

            # 12. Remove old FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY
            validate_evmscript_factory_removed_event(
                vote_events[11],
                factory_addr=OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY,
                emitted_by=easy_track,
            )

            # 13. Add new FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY
            validate_evmscript_factory_added_event(
                event=vote_events[12],
                p=EVMScriptFactoryAdded(
                    factory_addr=FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY,
                    permissions=create_permissions(vaults_adapter, "forceValidatorExit")
                ),
                emitted_by=easy_track,
            )

            # 14. Remove old UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_removed_event(
                vote_events[13],
                factory_addr=OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY,
                emitted_by=easy_track,
            )

            # 15. Add new UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY
            validate_evmscript_factory_added_event(
                event=vote_events[14],
                p=EVMScriptFactoryAdded(
                    factory_addr=UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(vaults_adapter, "updateVaultFees")
                ),
                emitted_by=easy_track,
            )


    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    if EXPECTED_DG_PROPOSAL_ID is not None:
        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================

            # Step 1.1. Check old VaultsAdapter has REGISTRY_ROLE on OperatorGrid
            assert operator_grid.hasRole(registry_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should have REGISTRY_ROLE on OperatorGrid before upgrade"

            # Step 1.2. Check new VaultsAdapter does not have REGISTRY_ROLE on OperatorGrid
            if VAULTS_ADAPTER != OLD_VAULTS_ADAPTER:
                assert not operator_grid.hasRole(registry_role, VAULTS_ADAPTER), "New VaultsAdapter should not have REGISTRY_ROLE on OperatorGrid before upgrade"

            # Step 1.3. Check old VaultsAdapter has VALIDATOR_EXIT_ROLE on VaultHub
            assert vault_hub.hasRole(validator_exit_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should have VALIDATOR_EXIT_ROLE on VaultHub before upgrade"

            # Step 1.4. Check new VaultsAdapter does not have VALIDATOR_EXIT_ROLE on VaultHub
            if VAULTS_ADAPTER != OLD_VAULTS_ADAPTER:
                assert not vault_hub.hasRole(validator_exit_role, VAULTS_ADAPTER), "New VaultsAdapter should not have VALIDATOR_EXIT_ROLE on VaultHub before upgrade"

            # Step 1.5. Check old VaultsAdapter has BAD_DEBT_MASTER_ROLE on VaultHub
            assert vault_hub.hasRole(bad_debt_master_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should have BAD_DEBT_MASTER_ROLE on VaultHub before upgrade"

            # Step 1.6. Check new VaultsAdapter does not have BAD_DEBT_MASTER_ROLE on VaultHub
            if VAULTS_ADAPTER != OLD_VAULTS_ADAPTER:
                assert not vault_hub.hasRole(bad_debt_master_role, VAULTS_ADAPTER), "New VaultsAdapter should not have BAD_DEBT_MASTER_ROLE on VaultHub before upgrade"

            # Step 1.7. Check CSM module parameters before upgrade
            csm_module_before = staking_router.getStakingModule(CSM_MODULE_ID)
            assert csm_module_before["stakeShareLimit"] == CSM_MODULE_OLD_TARGET_SHARE_BP, "CSM module should have old stake share limit before upgrade"
            assert csm_module_before["priorityExitShareThreshold"] == CSM_MODULE_OLD_PRIORITY_EXIT_THRESHOLD_BP, "CSM module should have old priority exit threshold before upgrade"
            assert csm_module_before["stakingModuleFee"] == CSM_MODULE_MODULE_FEE_BP, "CSM module fee should be unchanged before upgrade"
            assert csm_module_before["treasuryFee"] == CSM_MODULE_TREASURY_FEE_BP, "CSM treasury fee should be unchanged before upgrade"
            assert csm_module_before["maxDepositsPerBlock"] == CSM_MODULE_MAX_DEPOSITS_PER_BLOCK, "CSM max deposits per block should be unchanged before upgrade"
            assert csm_module_before["minDepositBlockDistance"] == CSM_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE, "CSM min deposit block distance should be unchanged before upgrade"

            # Step 1.8. Check TwoPhaseFrameConfigUpdate does not have MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus before upgrade
            assert not cs_hash_consensus.hasRole(manage_frame_config_role, TWO_PHASE_FRAME_CONFIG_UPDATE), "TwoPhaseFrameConfigUpdate should not have MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus before upgrade"

            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)

                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
                assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

                # === DG EXECUTION EVENTS VALIDATION ===

                # 1.1. Revoke REGISTRY_ROLE on OperatorGrid from old VaultsAdapter
                validate_revoke_role_event(
                    dg_events[0],
                    role=registry_role.hex(),
                    revoke_from=OLD_VAULTS_ADAPTER,
                    sender=AGENT,
                    emitted_by=operator_grid,
                )

                # 1.2. Grant REGISTRY_ROLE on OperatorGrid to new VaultsAdapter
                validate_grant_role_event(
                    dg_events[1],
                    role=registry_role.hex(),
                    grant_to=VAULTS_ADAPTER,
                    sender=AGENT,
                    emitted_by=operator_grid,
                )

                # 1.3. Revoke VALIDATOR_EXIT_ROLE on VaultHub from old VaultsAdapter
                validate_revoke_role_event(
                    dg_events[2],
                    role=validator_exit_role.hex(),
                    revoke_from=OLD_VAULTS_ADAPTER,
                    sender=AGENT,
                    emitted_by=vault_hub,
                )

                # 1.4. Grant VALIDATOR_EXIT_ROLE on VaultHub to new VaultsAdapter
                validate_grant_role_event(
                    dg_events[3],
                    role=validator_exit_role.hex(),
                    grant_to=VAULTS_ADAPTER,
                    sender=AGENT,
                    emitted_by=vault_hub,
                )

                # 1.5. Revoke BAD_DEBT_MASTER_ROLE on VaultHub from old VaultsAdapter
                validate_revoke_role_event(
                    dg_events[4],
                    role=bad_debt_master_role.hex(),
                    revoke_from=OLD_VAULTS_ADAPTER,
                    sender=AGENT,
                    emitted_by=vault_hub,
                )

                # 1.6. Grant BAD_DEBT_MASTER_ROLE on VaultHub to new VaultsAdapter
                validate_grant_role_event(
                    dg_events[5],
                    role=bad_debt_master_role.hex(),
                    grant_to=VAULTS_ADAPTER,
                    sender=AGENT,
                    emitted_by=vault_hub,
                )

                # 1.7. Validate CSM staking module update events
                assert "StakingModuleShareLimitSet" in dg_events[6], "No StakingModuleShareLimitSet event found"
                assert dg_events[6]["StakingModuleShareLimitSet"]["stakingModuleId"] == CSM_MODULE_ID
                assert dg_events[6]["StakingModuleShareLimitSet"]["stakeShareLimit"] == CSM_MODULE_NEW_TARGET_SHARE_BP
                assert dg_events[6]["StakingModuleShareLimitSet"]["priorityExitShareThreshold"] == CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP

                # 1.8. Grant MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus to TwoPhaseFrameConfigUpdate
                validate_grant_role_event(
                    dg_events[7],
                    role=manage_frame_config_role.hex(),
                    grant_to=TWO_PHASE_FRAME_CONFIG_UPDATE,
                    sender=AGENT,
                    emitted_by=cs_hash_consensus,
                )


        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # TODO Step 1.1. Check old VaultsAdapter does not have REGISTRY_ROLE on OperatorGrid
        # assert not operator_grid.hasRole(registry_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should not have REGISTRY_ROLE on OperatorGrid after upgrade"

        # Step 1.2. Check new VaultsAdapter has REGISTRY_ROLE on OperatorGrid
        assert operator_grid.hasRole(registry_role, VAULTS_ADAPTER), "New VaultsAdapter should have REGISTRY_ROLE on OperatorGrid after upgrade"

        # TODO Step 1.3. Check old VaultsAdapter does not have VALIDATOR_EXIT_ROLE on VaultHub
        # assert not vault_hub.hasRole(validator_exit_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should not have VALIDATOR_EXIT_ROLE on VaultHub after upgrade"

        # Step 1.4. Check new VaultsAdapter has VALIDATOR_EXIT_ROLE on VaultHub
        assert vault_hub.hasRole(validator_exit_role, VAULTS_ADAPTER), "New VaultsAdapter should have VALIDATOR_EXIT_ROLE on VaultHub after upgrade"

        # TODO Step 1.5. Check old VaultsAdapter does not have BAD_DEBT_MASTER_ROLE on VaultHub
        # assert not vault_hub.hasRole(bad_debt_master_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should not have BAD_DEBT_MASTER_ROLE on VaultHub after upgrade"

        # Step 1.6. Check new VaultsAdapter has BAD_DEBT_MASTER_ROLE on VaultHub
        assert vault_hub.hasRole(bad_debt_master_role, VAULTS_ADAPTER), "New VaultsAdapter should have BAD_DEBT_MASTER_ROLE on VaultHub after upgrade"

        # Step 1.7. Check CSM module parameters after upgrade
        csm_module_after = staking_router.getStakingModule(CSM_MODULE_ID)
        assert csm_module_after["stakeShareLimit"] == CSM_MODULE_NEW_TARGET_SHARE_BP, "CSM module should have new stake share limit after upgrade"
        assert csm_module_after["priorityExitShareThreshold"] == CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP, "CSM module should have new priority exit threshold after upgrade"
        assert csm_module_after["stakingModuleFee"] == CSM_MODULE_MODULE_FEE_BP, "CSM module fee should be unchanged after upgrade"
        assert csm_module_after["treasuryFee"] == CSM_MODULE_TREASURY_FEE_BP, "CSM treasury fee should be unchanged after upgrade"
        assert csm_module_after["maxDepositsPerBlock"] == CSM_MODULE_MAX_DEPOSITS_PER_BLOCK, "CSM max deposits per block should be unchanged after upgrade"
        assert csm_module_after["minDepositBlockDistance"] == CSM_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE, "CSM min deposit block distance should be unchanged after upgrade"

        # Step 1.8. Check TwoPhaseFrameConfigUpdate has MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus after upgrade
        assert cs_hash_consensus.hasRole(manage_frame_config_role, TWO_PHASE_FRAME_CONFIG_UPDATE), "TwoPhaseFrameConfigUpdate should have MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus after upgrade"

        # Scenario tests for Easy Track factories behavior after the vote ----------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------------
        trusted_address = accounts.at(ST_VAULTS_COMMITTEE, force=True)

        chain.snapshot()
        register_groups_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid)
        alter_tiers_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid)
        update_groups_share_limit_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid)
        set_jail_status_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid, vault_factory)
        update_vaults_fees_in_operator_grid_test(easy_track, trusted_address, stranger, lazy_oracle, vault_hub, vault_factory)

        # Register VaultHub contract for event decoding - brownie will not find ForcedValidatorExitTriggered and BadDebtSocialized events otherwise
        with open("interfaces/VaultHub.json") as fp:
            abi = json.load(fp)
        vault_hub_for_events = Contract.from_abi("VaultHub", VAULT_HUB, abi)
        state._add_contract(vault_hub_for_events)

        force_validator_exits_in_vault_hub_test(easy_track, trusted_address, stranger, lazy_oracle, vault_hub, vault_factory)
        socialize_bad_debt_in_vault_hub_test(easy_track, trusted_address, stranger, operator_grid, lazy_oracle, vault_hub, vault_factory)
        chain.revert()


def register_groups_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid):

    operator_addresses = [
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
    ]
    share_limits = [1000, 5000]
    tiers_params_array = [
        [(500, 200, 100, 50, 40, 10), (800, 200, 100, 50, 40, 10)],
        [(800, 200, 100, 50, 40, 10), (800, 200, 100, 50, 40, 10)],
    ]

    calldata = _encode_calldata(
        ["address[]", "uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[][]"],
        [operator_addresses, share_limits, tiers_params_array]
    )

    # Check initial state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == ZERO_ADDRESS  # operator
        assert group[1] == 0  # shareLimit
        assert len(group[3]) == 0  # tiersId array should be empty

    create_and_enact_motion(easy_track, trusted_address, REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

    # Check final state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == share_limits[i]  # shareLimit
        assert len(group[3]) == len(tiers_params_array[i])  # tiersId array should have the same length as tiers_params

        # Check tier details
        for j, tier_id in enumerate(group[3]):
            tier = operator_grid.tier(tier_id)
            assert tier[1] == tiers_params_array[i][j][0]  # shareLimit
            assert tier[3] == tiers_params_array[i][j][1]  # reserveRatioBP
            assert tier[4] == tiers_params_array[i][j][2]  # forcedRebalanceThresholdBP
            assert tier[5] == tiers_params_array[i][j][3]  # infraFeeBP
            assert tier[6] == tiers_params_array[i][j][4]  # liquidityFeeBP
            assert tier[7] == tiers_params_array[i][j][5]  # reservationFeeBP


def alter_tiers_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid):

    # Define new tier parameters
    # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, infraFeeBP, liquidityFeeBP, reservationFeeBP)
    new_tier_params = [(2000, 300, 150, 75, 60, 20), (3000, 400, 200, 100, 80, 30)]

    # First register a group and tier to alter
    executor = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)
    operator_address = "0x0000000000000000000000000000000000000005"
    operator_grid.registerGroup(operator_address, 10000, {"from": executor})
    initial_tier_params = [(1000, 200, 100, 50, 40, 10), (1000, 200, 100, 50, 40, 10)]
    operator_grid.registerTiers(operator_address, initial_tier_params, {"from": executor})

    tiers_count = operator_grid.tiersCount()
    tier_ids = [tiers_count - 2, tiers_count - 1]

    # Check initial state
    for i, tier_id in enumerate(tier_ids):
        tier = operator_grid.tier(tier_id)
        assert tier[1] == initial_tier_params[i][0]  # shareLimit
        assert tier[3] == initial_tier_params[i][1]  # reserveRatioBP
        assert tier[4] == initial_tier_params[i][2]  # forcedRebalanceThresholdBP
        assert tier[5] == initial_tier_params[i][3]  # infraFeeBP
        assert tier[6] == initial_tier_params[i][4]  # liquidityFeeBP
        assert tier[7] == initial_tier_params[i][5]  # reservationFeeBP

    calldata = _encode_calldata(["uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[]"], [tier_ids, new_tier_params])

    create_and_enact_motion(easy_track, trusted_address, ALTER_TIERS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

    # Check final state
    for i, tier_id in enumerate(tier_ids):
        tier = operator_grid.tier(tier_id)
        assert tier[1] == new_tier_params[i][0]  # shareLimit
        assert tier[3] == new_tier_params[i][1]  # reserveRatioBP
        assert tier[4] == new_tier_params[i][2]  # forcedRebalanceThresholdBP
        assert tier[5] == new_tier_params[i][3]  # infraFeeBP
        assert tier[6] == new_tier_params[i][4]  # liquidityFeeBP
        assert tier[7] == new_tier_params[i][5]  # reservationFeeBP


def update_groups_share_limit_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid):

    operator_addresses = ["0x0000000000000000000000000000000000000006", "0x0000000000000000000000000000000000000007"]
    new_share_limits = [2000, 3000]

    # First register the group to update
    executor = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)
    for i, operator_address in enumerate(operator_addresses):
        operator_grid.registerGroup(operator_address, new_share_limits[i]*2, {"from": executor})

    # Check initial state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == new_share_limits[i]*2  # shareLimit

    calldata = _encode_calldata(
        ["address[]", "uint256[]"],
        [operator_addresses, new_share_limits]
    )

    create_and_enact_motion(easy_track, trusted_address, UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

    # Check final state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == new_share_limits[i] # shareLimit


def set_jail_status_in_operator_grid_test(easy_track, trusted_address, stranger, operator_grid, vault_factory):

    # First create the vaults
    vaults = []
    for i in range(2):
        creation_tx = vault_factory.createVaultWithDashboard(
            stranger,
            stranger,
            stranger,
            100,
            3600, # 1 hour
            [],
            {"from": stranger, "value": "1 ether"},
        )
        vaults.append(creation_tx.events["VaultCreated"][0]["vault"])

    # Check initial state
    for vault in vaults:
        is_in_jail = operator_grid.isVaultInJail(vault)
        assert is_in_jail == False

    calldata = _encode_calldata(["address[]", "bool[]"], [vaults, [True, True]])

    create_and_enact_motion(easy_track, trusted_address, SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

    # Check final state
    for i, vault in enumerate(vaults):
        is_in_jail = operator_grid.isVaultInJail(vault)
        assert is_in_jail == True


def update_vaults_fees_in_operator_grid_test(easy_track, trusted_address, stranger, lazy_oracle, vault_hub, vault_factory):

    initial_total_value = 2 * 10**18

    # First create the vault
    creation_tx = vault_factory.createVaultWithDashboard(
        stranger,
        stranger,
        stranger,
        100,
        3600, # 1 hour
        [],
        {"from": stranger, "value": initial_total_value},
    )
    vault = creation_tx.events["VaultCreated"][0]["vault"]

    # Check initial state
    connection = vault_hub.vaultConnection(vault)
    assert connection[6] != 1 # infraFeeBP
    assert connection[7] != 1 # liquidityFeeBP
    assert connection[8] == 0 # reservationFeeBP

    calldata = _encode_calldata(["address[]", "uint256[]", "uint256[]", "uint256[]"], [[vault], [1], [1], [0]])

    motions_before = easy_track.getMotions()
    tx = easy_track.createMotion(UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY, calldata, {"from": trusted_address})
    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    (
        motion_id,
        _,
        _,
        motion_duration,
        motion_start_date,
        _,
        _,
        _,
        _,
    ) = motions[-1]

    chain.mine(1, motion_start_date + motion_duration + 1)

    # bring fresh report for vault
    current_time = chain.time()
    accounting_oracle = accounts.at(ACCOUNTING_ORACLE, force=True)
    lazy_oracle.updateReportData(
        current_time,
        1000,
        "0x00",
        "0x00",
        {"from": accounting_oracle})

    lazy_oracle_account = accounts.at(LAZY_ORACLE, force=True)
    vault_hub.applyVaultReport(
        vault,
        current_time,
        initial_total_value,
        initial_total_value,
        0,
        0,
        0,
        0,
        {"from": lazy_oracle_account})

    easy_track.enactMotion(
        motion_id,
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    # Check final state
    connection = vault_hub.vaultConnection(vault)
    assert connection[6] == 1 # infraFeeBP
    assert connection[7] == 1 # liquidityFeeBP
    assert connection[8] == 0 # reservationFeeBP


def force_validator_exits_in_vault_hub_test(easy_track, trusted_address, stranger, lazy_oracle, vault_hub, vault_factory):

    initial_total_value = 2 * 10**18

    # top up VAULTS_ADAPTER
    stranger.transfer(VAULTS_ADAPTER, 10**18)

    pubkey = b"01" * 48
    # First create the vault
    creation_tx = vault_factory.createVaultWithDashboard(
        stranger,
        stranger,
        stranger,
        100,
        3600, # 1 hour
        [],
        {"from": stranger, "value": initial_total_value},
    )
    vault = creation_tx.events["VaultCreated"][0]["vault"]

    calldata = _encode_calldata(["address[]", "bytes[]"], [[vault], [pubkey]])

    motions_before = easy_track.getMotions()
    tx = easy_track.createMotion(FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY, calldata, {"from": trusted_address})
    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    (
        motion_id,
        _,
        _,
        motion_duration,
        motion_start_date,
        _,
        _,
        _,
        _,
    ) = motions[-1]

    chain.mine(1, motion_start_date + motion_duration + 1)

    # bring fresh report for vault
    current_time = chain.time()
    accounting_oracle = accounts.at(ACCOUNTING_ORACLE, force=True)
    lazy_oracle.updateReportData(
        current_time,
        1000,
        "0x00",
        "0x00",
        {"from": accounting_oracle})

    # make vault unhealthy
    lazy_oracle_account = accounts.at(LAZY_ORACLE, force=True)
    vault_hub.applyVaultReport(
        vault,
        current_time,
        initial_total_value,
        initial_total_value,
        4 * initial_total_value,
        0,
        0,
        0,
        {"from": lazy_oracle_account})

    tx = easy_track.enactMotion(
        motion_id,
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    # Check event was emitted
    assert len(tx.events["ForcedValidatorExitTriggered"]) == 1
    event = tx.events["ForcedValidatorExitTriggered"][0]
    assert event["vault"] == vault
    assert event["pubkeys"] == "0x" + pubkey.hex()
    assert event["refundRecipient"] == VAULTS_ADAPTER


def socialize_bad_debt_in_vault_hub_test(easy_track, trusted_address, stranger, operator_grid, lazy_oracle, vault_hub, vault_factory):

    initial_total_value = 2 * 10**18
    max_shares_to_socialize = 2 * 10**16

    # Enable minting in default group
    executor = accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)
    operator_grid.alterTiers([0], [(100_000 * 10**18, 300, 250, 50, 40, 10)], {"from": executor})

    # First create the vaults
    creation_tx = vault_factory.createVaultWithDashboard(
        stranger,
        stranger,
        stranger,
        100,
        3600, # 1 hour
        [],
        {"from": stranger, "value": initial_total_value},
    )
    bad_debt_vault = creation_tx.events["VaultCreated"][0]["vault"]

    # Fresh report for bad debt vault
    current_time = chain.time()
    accounting_oracle = accounts.at(ACCOUNTING_ORACLE, force=True)
    lazy_oracle.updateReportData(current_time, 1000, "0x00", "0x00", {"from": accounting_oracle})
    lazy_oracle_account = accounts.at(LAZY_ORACLE, force=True)
    vault_hub.applyVaultReport(
        bad_debt_vault,
        current_time,
        initial_total_value,
        initial_total_value,
        0,
        0,
        0,
        0,
        {"from": lazy_oracle_account})

    bad_debt_dashboard = accounts.at(creation_tx.events["DashboardCreated"][0]["dashboard"], force=True)
    vault_hub.mintShares(bad_debt_vault, stranger, 10 * max_shares_to_socialize, {"from": bad_debt_dashboard})

    creation_tx = vault_factory.createVaultWithDashboard(
        stranger,
        stranger,
        stranger,
        100,
        3600, # 1 hour
        [],
        {"from": stranger, "value": initial_total_value},
    )
    vault_acceptor = creation_tx.events["VaultCreated"][0]["vault"]

    calldata = _encode_calldata(["address[]", "address[]", "uint256[]"], [[bad_debt_vault], [vault_acceptor], [max_shares_to_socialize]])

    motions_before = easy_track.getMotions()
    tx = easy_track.createMotion(SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY, calldata, {"from": trusted_address})
    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    (
        motion_id,
        _,
        _,
        motion_duration,
        motion_start_date,
        _,
        _,
        _,
        _,
    ) = motions[-1]

    chain.mine(1, motion_start_date + motion_duration + 1)

    # Bring fresh report for vaults
    current_time = chain.time()
    lazy_oracle.updateReportData(current_time, 1000, "0x00", "0x00", {"from": accounting_oracle})

    # Fresh report for acceptor vault
    vault_hub.applyVaultReport(
        vault_acceptor,
        current_time,
        initial_total_value,
        initial_total_value,
        0,
        0,
        0,
        0,
        {"from": lazy_oracle_account})

    # Make bad debt on second vault
    vault_hub.applyVaultReport(
        bad_debt_vault,
        current_time,
        10 * max_shares_to_socialize,
        initial_total_value,
        0,
        initial_total_value,
        0,
        0,
        {"from": lazy_oracle_account})

    bad_debt_record_before = vault_hub.vaultRecord(bad_debt_vault)
    bad_liability_before = bad_debt_record_before[2]
    acceptor_record_before = vault_hub.vaultRecord(vault_acceptor)
    acceptor_liability_before = acceptor_record_before[2]

    tx = easy_track.enactMotion(
        motion_id,
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    bad_debt_record_after = vault_hub.vaultRecord(bad_debt_vault)
    bad_liability_after = bad_debt_record_after[2]
    acceptor_record_after = vault_hub.vaultRecord(vault_acceptor)
    acceptor_liability_after = acceptor_record_after[2]

    assert bad_liability_after == bad_liability_before - max_shares_to_socialize
    assert acceptor_liability_after == acceptor_liability_before + max_shares_to_socialize

    # Check that events were emitted for failed socializations
    assert len(tx.events["BadDebtSocialized"]) == 1
    event = tx.events["BadDebtSocialized"][0]
    assert event["vaultDonor"] == bad_debt_vault
    assert event["vaultAcceptor"] == vault_acceptor
    assert event["badDebtShares"] == max_shares_to_socialize
