from brownie import chain, interface, web3, accounts, ZERO_ADDRESS, reverts
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
from utils.evm_script import encode_call_script, encode_error
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event

from utils.agent import agent_forward
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role, encode_permission_grant, encode_permission_revoke
from utils.easy_track import create_permissions
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.aragon import validate_aragon_grant_permission_event, validate_aragon_revoke_permission_event
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, validate_evmscript_factory_removed_event, EVMScriptFactoryAdded
from utils.test.event_validators.proxy import validate_proxy_upgrade_event
from utils.test.event_validators.staking_router import validate_staking_module_update_event, StakingModuleItem
from utils.test.easy_track_helpers import _encode_calldata, create_and_enact_motion
from utils.test.rpc_helpers import set_storage_at


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.upgrade_2026_01_20_v3_phase_2 import start_vote, get_vote_items


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
LIDO = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
OPERATOR_GRID = "0xC69685E89Cefc327b43B7234AC646451B27c544d"
VAULT_HUB = "0x1d201BE093d847f6446530Efb0E8Fb426d176709"
LAZY_ORACLE = "0x5DB427080200c235F2Ae8Cd17A7be87921f7AD6c"
ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
VAULTS_FACTORY = "0x02Ca7772FF14a9F6c1a08aF385aA96bb1b34175A"
CS_HASH_CONSENSUS = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"
CS_FEE_ORACLE = "0x4D4074628678Bd302921c20573EEa1ed38DdF7FB"
TWO_PHASE_FRAME_CONFIG_UPDATE = "0xb2B4DB1491cbe949ae85EfF01E0d3ee239f110C1"
PREDEPOSIT_GUARANTEE = "0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3"
PREDEPOSIT_GUARANTEE_NEW_IMPL = "0xE78717192C45736DF0E4be55c0219Ee7f9aDdd0D"

# CSM module parameters
CSM_MODULE_ID = 3
CSM_MODULE_NAME = "Community Staking"
CSM_MODULE_OLD_TARGET_SHARE_BP = 500  # 5%
CSM_MODULE_OLD_PRIORITY_EXIT_THRESHOLD_BP = 625  # 6.25%
CSM_MODULE_NEW_TARGET_SHARE_BP = 750  # 7.5%
CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 900  # 9%
CSM_MODULE_MODULE_FEE_BP = 600
CSM_MODULE_TREASURY_FEE_BP = 400
CSM_MODULE_MAX_DEPOSITS_PER_BLOCK = 30
CSM_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25

# Lido max external ratio
MAX_EXTERNAL_RATIO_BP = 3000  # 30%

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
NEW_VAULTS_ADAPTER = "0x28F9Ac198C4E0FA6A9Ad2c2f97CB38F1A3120f27"
NEW_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0x73f80240ad9363d5d3C5C3626953C351cA36Bfe9"
NEW_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY = "0xE73842AEbEC99Dacf2aAEec61409fD01A033f478"
NEW_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0xf23559De8ab37fF7a154384B0822dA867Cfa7Eac"
NEW_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x6a4f33F05E7412A11100353724Bb6a152Cf0D305"
NEW_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0xaf35A63a4114B7481589fDD9FDB3e35Fd65fAed7"
NEW_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6F5c0A5a824773E8f8285bC5aA59ea0Aab2A6400"
NEW_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0xDfA0bc38113B6d53c2881573FD764CEEFf468610"

# Test parameters
EXPECTED_VOTE_ID = None  # Set to None to create a new vote each test run
EXPECTED_DG_PROPOSAL_ID = 8
EXPECTED_VOTE_EVENTS_COUNT = 15
EXPECTED_DG_EVENTS_FROM_AGENT = 15  # 6 role revoke/grant + 1 CSM update + 1 CS HashConsensus role grant + 1 PDG impl upgrade + 3 PDG unpause (grant RESUME_ROLE, resume, revoke RESUME_ROLE) + 3 set max external ratio (grant STAKING_CONTROL_ROLE, set ratio, revoke STAKING_CONTROL_ROLE)
EXPECTED_DG_EVENTS_COUNT = 15
IPFS_DESCRIPTION_HASH = ""  # TODO: Update after IPFS upload

# Storage slot for lastProcessingRefSlot in CSFeeOracle
LAST_PROCESSING_REF_SLOT_STORAGE_KEY = web3.keccak(text="lido.BaseOracle.lastProcessingRefSlot").hex()


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    """Returns list of dual governance proposal calls for events checking"""

    lido = interface.Lido(LIDO)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    vault_hub = interface.VaultHub(VAULT_HUB)
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)
    predeposit_guarantee_proxy = interface.OssifiableProxy(PREDEPOSIT_GUARANTEE)
    predeposit_guarantee = interface.PredepositGuarantee(PREDEPOSIT_GUARANTEE)

    dg_items = [
        # ======================== EasyTrack ========================
        # 1.1. Revoke REGISTRY_ROLE on OperatorGrid from old VaultsAdapter
        agent_forward([
            encode_oz_revoke_role(operator_grid, "vaults.OperatorsGrid.Registry", OLD_VAULTS_ADAPTER)
        ]),

        # 1.2. Grant REGISTRY_ROLE on OperatorGrid to new VaultsAdapter
        agent_forward([
            encode_oz_grant_role(operator_grid, "vaults.OperatorsGrid.Registry", NEW_VAULTS_ADAPTER)
        ]),

        # 1.3. Revoke VALIDATOR_EXIT_ROLE on VaultHub from old VaultsAdapter
        agent_forward([
            encode_oz_revoke_role(vault_hub, "vaults.VaultHub.ValidatorExitRole", OLD_VAULTS_ADAPTER)
        ]),

        # 1.4. Grant VALIDATOR_EXIT_ROLE on VaultHub to new VaultsAdapter
        agent_forward([
            encode_oz_grant_role(vault_hub, "vaults.VaultHub.ValidatorExitRole", NEW_VAULTS_ADAPTER)
        ]),

        # 1.5. Revoke BAD_DEBT_MASTER_ROLE on VaultHub from old VaultsAdapter
        agent_forward([
            encode_oz_revoke_role(vault_hub, "vaults.VaultHub.BadDebtMasterRole", OLD_VAULTS_ADAPTER)
        ]),

        # 1.6. Grant BAD_DEBT_MASTER_ROLE on VaultHub to new VaultsAdapter
        agent_forward([
            encode_oz_grant_role(vault_hub, "vaults.VaultHub.BadDebtMasterRole", NEW_VAULTS_ADAPTER)
        ]),

        # ======================== PDG ========================
        # 1.7. Update PredepositGuarantee implementation
        agent_forward([
            (
                predeposit_guarantee_proxy.address,
                predeposit_guarantee_proxy.proxy__upgradeTo.encode_input(PREDEPOSIT_GUARANTEE_NEW_IMPL),
            )
        ]),

        # 1.8. Grant RESUME_ROLE on PredepositGuarantee to Agent
        agent_forward([
            encode_oz_grant_role(predeposit_guarantee, "PausableUntilWithRoles.ResumeRole", AGENT)
        ]),

        # 1.9. Unpause PredepositGuarantee
        agent_forward([
            (
                PREDEPOSIT_GUARANTEE,
                predeposit_guarantee.resume.encode_input(),
            )
        ]),

        # 1.10. Revoke RESUME_ROLE on PredepositGuarantee from Agent
        agent_forward([
            encode_oz_revoke_role(predeposit_guarantee, "PausableUntilWithRoles.ResumeRole", AGENT)
        ]),

        # ======================== Lido ========================
        # 1.11. Grant STAKING_CONTROL_ROLE on Lido to Agent
        agent_forward([
            encode_permission_grant(lido, "STAKING_CONTROL_ROLE", AGENT)
        ]),

        # 1.12. Set max external ratio to 30%
        agent_forward([
            (
                lido.address,
                lido.setMaxExternalRatioBP.encode_input(MAX_EXTERNAL_RATIO_BP),
            )
        ]),

        # 1.13. Revoke STAKING_CONTROL_ROLE on Lido from Agent
        agent_forward([
            encode_permission_revoke(lido, "STAKING_CONTROL_ROLE", AGENT)
        ]),

        # ======================== CSM ========================
        # 1.14. Raise CSM (MODULE_ID = 3) stake share limit from 500 BP to 750 BP and priority exit threshold from 625 BP to 900 BP
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

        # 1.15. Grant MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus to TwoPhaseFrameConfigUpdate
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

    lido = interface.Lido(LIDO)
    vault_hub = interface.VaultHub(VAULT_HUB)
    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    lazy_oracle = interface.LazyOracle(LAZY_ORACLE)
    vault_factory = interface.VaultFactory(VAULTS_FACTORY)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)
    vaults_adapter = interface.IVaultsAdapter(NEW_VAULTS_ADAPTER)

    registry_role = web3.keccak(text="vaults.OperatorsGrid.Registry")
    validator_exit_role = web3.keccak(text="vaults.VaultHub.ValidatorExitRole")
    bad_debt_master_role = web3.keccak(text="vaults.VaultHub.BadDebtMasterRole")
    manage_frame_config_role = web3.keccak(text="MANAGE_FRAME_CONFIG_ROLE")
    resume_role = web3.keccak(text="PausableUntilWithRoles.ResumeRole")
    staking_control_role = web3.keccak(text="STAKING_CONTROL_ROLE")


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
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()


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

        # Check new factories are not present yet
        assert NEW_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY not in initial_factories
        assert NEW_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY not in initial_factories
        assert NEW_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY not in initial_factories
        assert NEW_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY not in initial_factories
        assert NEW_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY not in initial_factories
        assert NEW_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY not in initial_factories
        assert NEW_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY not in initial_factories

        # TODO Check IPFS description hash
        # assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        new_factories = easy_track.getEVMScriptFactories()

        # Check old factories are removed
        assert OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY not in new_factories
        assert OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY not in new_factories
        assert OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY not in new_factories
        assert OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY not in new_factories
        assert OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY not in new_factories
        assert OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY not in new_factories
        assert OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY not in new_factories

        # Check new factories are added
        assert NEW_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new ALTER_TIERS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert NEW_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert NEW_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert NEW_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY factory after vote"
        assert NEW_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY in new_factories, "EasyTrack should have new SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY factory after vote"
        assert NEW_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY in new_factories, "EasyTrack should have new FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY factory after vote"
        assert NEW_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY in new_factories, "EasyTrack should have new UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY factory after vote"

        # Since we remove 7 and add 7, the count should remain the same
        assert len(initial_factories) == len(new_factories), f"Factory count changed: {len(initial_factories)} -> {len(new_factories)}"

        # Check that all old factories (except the ones being replaced) are still present
        # Use sets because order of vaults' factories changes when removing and adding
        old_factories_to_remove = {
            OLD_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY,
            OLD_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY,
            OLD_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY,
            OLD_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY,
            OLD_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY,
            OLD_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY,
            OLD_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY,
        }
        new_factories_added = {
            NEW_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY,
            NEW_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY,
            NEW_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY,
            NEW_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY,
            NEW_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY,
            NEW_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY,
            NEW_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY,
        }

        # Check that all other factories remained
        factories_that_should_remain = set(initial_factories) - old_factories_to_remove
        factories_in_new_list = set(new_factories) - new_factories_added
        assert factories_that_should_remain == factories_in_new_list, "All other factories should remain unchanged"

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata="Activate Lido V3 Phase 2, raise CSM stake share limit to 7.5% and priority exit threshold to 9%, grant MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus to TwoPhaseFrameConfigUpdate contract",
                proposal_calls=dual_governance_proposal_calls,
            )

            # Validate EasyTrack factory removal/addition events
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
                    factory_addr=NEW_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY,
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
                    factory_addr=NEW_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY,
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
                    factory_addr=NEW_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY,
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
                    factory_addr=NEW_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY,
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
                    factory_addr=NEW_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY,
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
                    factory_addr=NEW_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY,
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
                    factory_addr=NEW_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY,
                    permissions=create_permissions(vaults_adapter, "updateVaultFees")
                ),
                emitted_by=easy_track,
            )


    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    csm_module_before = None
    if EXPECTED_DG_PROPOSAL_ID is not None:
        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================

            # Step 1.1. Check old VaultsAdapter has REGISTRY_ROLE on OperatorGrid
            assert operator_grid.hasRole(registry_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should have REGISTRY_ROLE on OperatorGrid before upgrade"

            # Step 1.2. Check new VaultsAdapter does not have REGISTRY_ROLE on OperatorGrid
            if NEW_VAULTS_ADAPTER != OLD_VAULTS_ADAPTER:
                assert not operator_grid.hasRole(registry_role, NEW_VAULTS_ADAPTER), "New VaultsAdapter should not have REGISTRY_ROLE on OperatorGrid before upgrade"

            # Step 1.3. Check old VaultsAdapter has VALIDATOR_EXIT_ROLE on VaultHub
            assert vault_hub.hasRole(validator_exit_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should have VALIDATOR_EXIT_ROLE on VaultHub before upgrade"

            # Step 1.4. Check new VaultsAdapter does not have VALIDATOR_EXIT_ROLE on VaultHub
            if NEW_VAULTS_ADAPTER != OLD_VAULTS_ADAPTER:
                assert not vault_hub.hasRole(validator_exit_role, NEW_VAULTS_ADAPTER), "New VaultsAdapter should not have VALIDATOR_EXIT_ROLE on VaultHub before upgrade"

            # Step 1.5. Check old VaultsAdapter has BAD_DEBT_MASTER_ROLE on VaultHub
            assert vault_hub.hasRole(bad_debt_master_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should have BAD_DEBT_MASTER_ROLE on VaultHub before upgrade"

            # Step 1.6. Check new VaultsAdapter does not have BAD_DEBT_MASTER_ROLE on VaultHub
            if NEW_VAULTS_ADAPTER != OLD_VAULTS_ADAPTER:
                assert not vault_hub.hasRole(bad_debt_master_role, NEW_VAULTS_ADAPTER), "New VaultsAdapter should not have BAD_DEBT_MASTER_ROLE on VaultHub before upgrade"

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

            # Test that executeOffsetPhase reverts with permission denied error before enactment
            chain.snapshot()
            two_phase_frame_config_update_revert_no_permission_test(stranger)
            chain.revert()

            # Step 1.9. Check PredepositGuarantee implementation before upgrade
            predeposit_guarantee_proxy = interface.OssifiableProxy(PREDEPOSIT_GUARANTEE)
            predeposit_guarantee_impl_before = str(predeposit_guarantee_proxy.proxy__getImplementation()).lower()
            assert predeposit_guarantee_impl_before != PREDEPOSIT_GUARANTEE_NEW_IMPL.lower(), "PredepositGuarantee should have old implementation before upgrade"

            # Step 1.10-1.12. Check PredepositGuarantee is paused before upgrade
            predeposit_guarantee = interface.PredepositGuarantee(PREDEPOSIT_GUARANTEE)
            assert predeposit_guarantee.isPaused(), "PredepositGuarantee should be paused before upgrade"

            # Step 1.13. Check max external ratio before upgrade
            max_external_ratio_before = lido.getMaxExternalRatioBP()
            assert max_external_ratio_before == 300, "Lido max external ratio should be 3% (300 BP) before upgrade"

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

                # ======================== EasyTrack items ========================
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
                    grant_to=NEW_VAULTS_ADAPTER,
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
                    grant_to=NEW_VAULTS_ADAPTER,
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
                    grant_to=NEW_VAULTS_ADAPTER,
                    sender=AGENT,
                    emitted_by=vault_hub,
                )

                # ======================== PDG items ========================
                # 1.7. Validate PredepositGuarantee implementation upgrade
                validate_proxy_upgrade_event(
                    dg_events[6],
                    implementation=PREDEPOSIT_GUARANTEE_NEW_IMPL,
                    emitted_by=PREDEPOSIT_GUARANTEE,
                )

                # 1.8. Validate grant RESUME_ROLE on PredepositGuarantee to Agent
                validate_grant_role_event(
                    dg_events[7],
                    role=resume_role.hex(),
                    grant_to=AGENT,
                    sender=AGENT,
                    emitted_by=predeposit_guarantee,
                )

                # 1.9. Validate PredepositGuarantee unpause (Resumed event)
                assert "Resumed" in dg_events[8], "No Resumed event found for PredepositGuarantee"
                assert dg_events[8]["Resumed"][0]["_emitted_by"] == PREDEPOSIT_GUARANTEE, "Wrong emitter for Resumed event"

                # 1.10. Validate revoke RESUME_ROLE on PredepositGuarantee from Agent
                validate_revoke_role_event(
                    dg_events[9],
                    role=resume_role.hex(),
                    revoke_from=AGENT,
                    sender=AGENT,
                    emitted_by=predeposit_guarantee,
                )

                # ======================== External share items ========================
                # 1.11. Validate grant STAKING_CONTROL_ROLE on Lido to Agent
                validate_aragon_grant_permission_event(
                    dg_events[10],
                    entity=AGENT,
                    app=LIDO,
                    role=staking_control_role.hex(),
                    emitted_by=ACL,
                )

                # 1.12. Validate MaxExternalRatioBPSet event
                assert "MaxExternalRatioBPSet" in dg_events[11], "No MaxExternalRatioBPSet event found"
                assert dg_events[11]["MaxExternalRatioBPSet"]["maxExternalRatioBP"] == MAX_EXTERNAL_RATIO_BP, "Wrong max external ratio in event"
                assert dg_events[11]["MaxExternalRatioBPSet"]["_emitted_by"] == LIDO, "Wrong event emitter for MaxExternalRatioBPSet"

                # 1.13. Validate revoke STAKING_CONTROL_ROLE on Lido from Agent
                validate_aragon_revoke_permission_event(
                    dg_events[12],
                    entity=AGENT,
                    app=LIDO,
                    role=staking_control_role.hex(),
                    emitted_by=ACL,
                )

                # ======================== CSM items ========================
                # 1.14. Validate CSM staking module update events
                validate_staking_module_update_event(
                    event=dg_events[13],
                    module_item=StakingModuleItem(
                        id=CSM_MODULE_ID,
                        address=None,
                        name=CSM_MODULE_NAME,
                        target_share=CSM_MODULE_NEW_TARGET_SHARE_BP,
                        module_fee=CSM_MODULE_MODULE_FEE_BP,
                        treasury_fee=CSM_MODULE_TREASURY_FEE_BP,
                        priority_exit_share=CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
                    ),
                    emitted_by=STAKING_ROUTER,
                )

                # 1.15. Grant MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus to TwoPhaseFrameConfigUpdate
                validate_grant_role_event(
                    dg_events[14],
                    role=manage_frame_config_role.hex(),
                    grant_to=TWO_PHASE_FRAME_CONFIG_UPDATE,
                    sender=AGENT,
                    emitted_by=cs_hash_consensus,
                )


        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # Step 1.1. Check old VaultsAdapter does not have REGISTRY_ROLE on OperatorGrid
        assert not operator_grid.hasRole(registry_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should not have REGISTRY_ROLE on OperatorGrid after upgrade"

        # Step 1.2. Check new VaultsAdapter has REGISTRY_ROLE on OperatorGrid
        assert operator_grid.hasRole(registry_role, NEW_VAULTS_ADAPTER), "New VaultsAdapter should have REGISTRY_ROLE on OperatorGrid after upgrade"

        # Step 1.3. Check old VaultsAdapter does not have VALIDATOR_EXIT_ROLE on VaultHub
        assert not vault_hub.hasRole(validator_exit_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should not have VALIDATOR_EXIT_ROLE on VaultHub after upgrade"

        # Step 1.4. Check new VaultsAdapter has VALIDATOR_EXIT_ROLE on VaultHub
        assert vault_hub.hasRole(validator_exit_role, NEW_VAULTS_ADAPTER), "New VaultsAdapter should have VALIDATOR_EXIT_ROLE on VaultHub after upgrade"

        # Step 1.5. Check old VaultsAdapter does not have BAD_DEBT_MASTER_ROLE on VaultHub
        assert not vault_hub.hasRole(bad_debt_master_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should not have BAD_DEBT_MASTER_ROLE on VaultHub after upgrade"

        # Step 1.6. Check new VaultsAdapter has BAD_DEBT_MASTER_ROLE on VaultHub
        assert vault_hub.hasRole(bad_debt_master_role, NEW_VAULTS_ADAPTER), "New VaultsAdapter should have BAD_DEBT_MASTER_ROLE on VaultHub after upgrade"

        # Step 1.7. Check CSM module parameters after upgrade
        csm_module_after = staking_router.getStakingModule(CSM_MODULE_ID)
        assert csm_module_after["stakeShareLimit"] == CSM_MODULE_NEW_TARGET_SHARE_BP, "CSM module should have new stake share limit after upgrade"
        assert csm_module_after["priorityExitShareThreshold"] == CSM_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP, "CSM module should have new priority exit threshold after upgrade"

        # Compare all fields with before values, except for the two that must differ
        if csm_module_before is not None:
            changed_fields = {"stakeShareLimit", "priorityExitShareThreshold"}
            for key in csm_module_before.keys():
                if key not in changed_fields:
                    assert csm_module_after[key] == csm_module_before[key], f"CSM module {key} should be unchanged after upgrade"

        # Step 1.8. Check TwoPhaseFrameConfigUpdate has MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus after upgrade
        assert cs_hash_consensus.hasRole(manage_frame_config_role, TWO_PHASE_FRAME_CONFIG_UPDATE), "TwoPhaseFrameConfigUpdate should have MANAGE_FRAME_CONFIG_ROLE on CS HashConsensus after upgrade"

        # Step 1.9. Check PredepositGuarantee implementation after upgrade
        predeposit_guarantee_proxy = interface.OssifiableProxy(PREDEPOSIT_GUARANTEE)
        assert str(predeposit_guarantee_proxy.proxy__getImplementation()).lower() == PREDEPOSIT_GUARANTEE_NEW_IMPL.lower(), "PredepositGuarantee should have new implementation after upgrade"

        # Step 1.10-1.12. Check PredepositGuarantee is unpaused after upgrade and Agent does not have RESUME_ROLE
        predeposit_guarantee = interface.PredepositGuarantee(PREDEPOSIT_GUARANTEE)
        assert not predeposit_guarantee.isPaused(), "PredepositGuarantee should be unpaused after upgrade"
        assert not predeposit_guarantee.hasRole(resume_role, AGENT), "Agent should not have RESUME_ROLE on PredepositGuarantee after upgrade"

        # Step 1.13. Check max external ratio after upgrade
        assert lido.getMaxExternalRatioBP() == MAX_EXTERNAL_RATIO_BP, "Lido max external ratio should be 30% after upgrade"

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

        # Scenario test for TwoPhaseFrameConfigUpdate contract
        chain.snapshot()
        two_phase_frame_config_update_test(stranger)
        chain.revert()

        # Test that executeOffsetPhase reverts with wrong slot error after enactment
        chain.snapshot()
        two_phase_frame_config_update_revert_wrong_slot_test(stranger)
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

    create_and_enact_motion(easy_track, trusted_address, NEW_REGISTER_GROUPS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

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

    create_and_enact_motion(easy_track, trusted_address, NEW_ALTER_TIERS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

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

    create_and_enact_motion(easy_track, trusted_address, NEW_UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

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

    create_and_enact_motion(easy_track, trusted_address, NEW_SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY, calldata, stranger)

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
    tx = easy_track.createMotion(NEW_UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY, calldata, {"from": trusted_address})
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
    stranger.transfer(NEW_VAULTS_ADAPTER, 10**18)

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
    tx = easy_track.createMotion(NEW_FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY, calldata, {"from": trusted_address})
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
    assert event["refundRecipient"] == NEW_VAULTS_ADAPTER


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
    tx = easy_track.createMotion(NEW_SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY, calldata, {"from": trusted_address})
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


def two_phase_frame_config_update_test(stranger):
    """
    Test scenario for TwoPhaseFrameConfigUpdate contract:
    - call executeOffsetPhase
    - assert changes are applied
    - call executeRestorePhase
    - assert changes are applied
    - assert role was renounced from TWO_PHASE_FRAME_CONFIG_UPDATE

    To avoid the hassle of simulating oracle reports, we set lastProcessingRefSlot in CSFeeOracle to match expected slots.
    """
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)
    cs_fee_oracle = interface.CSFeeOracle(CS_FEE_ORACLE)
    two_phase_update = interface.TwoPhaseFrameConfigUpdate(TWO_PHASE_FRAME_CONFIG_UPDATE)

    manage_frame_config_role = cs_hash_consensus.MANAGE_FRAME_CONFIG_ROLE()

    # Get phase configs from the contract
    offset_phase = two_phase_update.offsetPhase()
    restore_phase = two_phase_update.restorePhase()

    [offset_expected_ref_slot, _, offset_epochs_per_frame, offset_fast_lane_length, is_offset_phase_executed] = offset_phase
    [restore_expected_ref_slot, _, restore_epochs_per_frame, restore_fast_lane_length, is_restore_phase_executed] = restore_phase

    assert cs_hash_consensus.hasRole(manage_frame_config_role, TWO_PHASE_FRAME_CONFIG_UPDATE), "TwoPhaseFrameConfigUpdate should have MANAGE_FRAME_CONFIG_ROLE"
    assert is_offset_phase_executed == False, "Offset phase should not be executed yet"
    assert is_restore_phase_executed == False, "Restore phase should not be executed yet"

    # =========================================================================
    # Phase 1: Execute Offset Phase
    # =========================================================================

    # Set lastProcessingRefSlot in CSFeeOracle to match offset phase expected slot
    set_storage_at(cs_fee_oracle.address, LAST_PROCESSING_REF_SLOT_STORAGE_KEY, "0x" + offset_expected_ref_slot.to_bytes(32, "big").hex())
    assert cs_fee_oracle.getLastProcessingRefSlot() == offset_expected_ref_slot, "CSFeeOracle lastProcessingRefSlot should be set to offset phase expected slot"
    assert two_phase_update.isReadyForOffsetPhase(), "Should be ready for offset phase"

    offset_tx = two_phase_update.executeOffsetPhase({"from": stranger})
    assert len(offset_tx.events["OffsetPhaseExecuted"]) == 1, "OffsetPhaseExecuted event should be emitted"

    # Check offset phase changes are applied
    assert two_phase_update.offsetPhase()[4] == True, "Offset phase should be marked as executed"
    [_, frame_config_epochs_per_frame, frame_config_fast_lane_length] = cs_hash_consensus.getFrameConfig()
    assert frame_config_epochs_per_frame == offset_epochs_per_frame, f"Epochs per frame should be {offset_epochs_per_frame} after offset phase"
    assert frame_config_fast_lane_length == offset_fast_lane_length, f"Fast lane length should be {offset_fast_lane_length} after offset phase"

    # =========================================================================
    # Phase 2: Execute Restore Phase
    # =========================================================================

    # Set lastProcessingRefSlot in CSFeeOracle to match restore phase expected slot
    set_storage_at(cs_fee_oracle.address, LAST_PROCESSING_REF_SLOT_STORAGE_KEY, "0x" + restore_expected_ref_slot.to_bytes(32, "big").hex())
    assert cs_fee_oracle.getLastProcessingRefSlot() == restore_expected_ref_slot, "CSFeeOracle lastProcessingRefSlot should be set to restore phase expected slot"
    assert two_phase_update.isReadyForRestorePhase(), "Should be ready for restore phase"

    restore_tx = two_phase_update.executeRestorePhase({"from": stranger})
    assert len(restore_tx.events["RestorePhaseExecuted"]) == 1, "RestorePhaseExecuted event should be emitted"

    # Check restore phase changes are applied
    assert two_phase_update.restorePhase()[4] == True, "Restore phase should be marked as executed"
    [_, frame_config_epochs_per_frame, frame_config_fast_lane_length] = cs_hash_consensus.getFrameConfig()
    assert frame_config_epochs_per_frame == restore_epochs_per_frame, f"Epochs per frame should be {restore_epochs_per_frame} after restore phase"
    assert frame_config_fast_lane_length == restore_fast_lane_length, f"Fast lane length should be {restore_fast_lane_length} after restore phase"

    # =========================================================================
    # Role renouncement
    # =========================================================================

    # Check MANAGE_FRAME_CONFIG_ROLE was renounced from TwoPhaseFrameConfigUpdate
    assert not cs_hash_consensus.hasRole(manage_frame_config_role, TWO_PHASE_FRAME_CONFIG_UPDATE), "TwoPhaseFrameConfigUpdate should NOT have MANAGE_FRAME_CONFIG_ROLE after restore phase"

    # Check RoleRevoked event was emitted for the renouncement
    assert len(restore_tx.events["RoleRevoked"]) == 1, "RoleRevoked event should be emitted"
    role_revoked_event = restore_tx.events["RoleRevoked"][0]
    assert role_revoked_event["role"] == manage_frame_config_role, "Role revoked should be MANAGE_FRAME_CONFIG_ROLE"
    assert role_revoked_event["account"] == TWO_PHASE_FRAME_CONFIG_UPDATE, "Account should be TwoPhaseFrameConfigUpdate"


def two_phase_frame_config_update_revert_wrong_slot_test(stranger):
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)
    cs_fee_oracle = interface.CSFeeOracle(CS_FEE_ORACLE)
    two_phase_update = interface.TwoPhaseFrameConfigUpdate(TWO_PHASE_FRAME_CONFIG_UPDATE)

    # Verify the contract has the role (after DG proposal execution)
    manage_frame_config_role = cs_hash_consensus.MANAGE_FRAME_CONFIG_ROLE()
    assert cs_hash_consensus.hasRole(manage_frame_config_role, TWO_PHASE_FRAME_CONFIG_UPDATE), "TwoPhaseFrameConfigUpdate should have MANAGE_FRAME_CONFIG_ROLE"

    # Get required slots and current slot
    offset_expected_ref_slot = two_phase_update.offsetPhase()[0]
    restore_expected_ref_slot = two_phase_update.restorePhase()[0]
    current_slot = cs_fee_oracle.getLastProcessingRefSlot()

    # Check that current slot is lower than required slots
    assert current_slot < offset_expected_ref_slot, f"Current slot {current_slot} should be lower than offset required slot {offset_expected_ref_slot}"
    assert current_slot < restore_expected_ref_slot, f"Current slot {current_slot} should be lower than restore required slot {restore_expected_ref_slot}"

    # executeOffsetPhase should revert with UnexpectedLastProcessingRefSlot
    assert not two_phase_update.isReadyForOffsetPhase(), "Should not be ready for offset phase without correct slot"

    with reverts(f"UnexpectedLastProcessingRefSlot: {current_slot}, {offset_expected_ref_slot}"):
        two_phase_update.executeOffsetPhase({"from": stranger})

    # Execute offset phase first (restore phase requires offset to be done first)
    set_storage_at(cs_fee_oracle.address, LAST_PROCESSING_REF_SLOT_STORAGE_KEY, "0x" + offset_expected_ref_slot.to_bytes(32, "big").hex())
    two_phase_update.executeOffsetPhase({"from": stranger})

    # Reset to a slot lower than restore expected slot to test the wrong slot error
    set_storage_at(cs_fee_oracle.address, LAST_PROCESSING_REF_SLOT_STORAGE_KEY, "0x" + current_slot.to_bytes(32, "big").hex())

    # Without setting the correct slot, executeRestorePhase should revert with UnexpectedLastProcessingRefSlot
    assert not two_phase_update.isReadyForRestorePhase(), "Should not be ready for restore phase without correct slot"

    with reverts(f"UnexpectedLastProcessingRefSlot: {current_slot}, {restore_expected_ref_slot}"):
        two_phase_update.executeRestorePhase({"from": stranger})


def two_phase_frame_config_update_revert_no_permission_test(stranger):
    cs_hash_consensus = interface.CSHashConsensus(CS_HASH_CONSENSUS)
    cs_fee_oracle = interface.CSFeeOracle(CS_FEE_ORACLE)
    two_phase_update = interface.TwoPhaseFrameConfigUpdate(TWO_PHASE_FRAME_CONFIG_UPDATE)

    manage_frame_config_role = cs_hash_consensus.MANAGE_FRAME_CONFIG_ROLE()

    # Verify the contract does NOT have the role (before DG proposal execution)
    assert not cs_hash_consensus.hasRole(manage_frame_config_role, TWO_PHASE_FRAME_CONFIG_UPDATE), "TwoPhaseFrameConfigUpdate should NOT have MANAGE_FRAME_CONFIG_ROLE before enactment"

    # Test offset phase: set the correct slot manually
    offset_expected_ref_slot = two_phase_update.offsetPhase()[0]
    set_storage_at(cs_fee_oracle.address, LAST_PROCESSING_REF_SLOT_STORAGE_KEY, "0x" + offset_expected_ref_slot.to_bytes(32, "big").hex())

    # Even with correct slot, should revert due to missing permission (AccessControlUnauthorizedAccount)
    with reverts(encode_error("AccessControlUnauthorizedAccount(address,bytes32)", [TWO_PHASE_FRAME_CONFIG_UPDATE.lower(), bytes(manage_frame_config_role)])):
        two_phase_update.executeOffsetPhase({"from": stranger})
