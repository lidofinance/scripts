from brownie import chain, interface, web3, convert, accounts, reverts, ZERO_ADDRESS
from brownie.network.transaction import TransactionReceipt
import pytest

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
OPERATOR_GRID = "0xC69685E89Cefc327b43B7234AC646451B27c544d"
VAULT_HUB = "0x1d201BE093d847f6446530Efb0E8Fb426d176709"
LAZY_ORACLE = "0x5DB427080200c235F2Ae8Cd17A7be87921f7AD6c"
ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
VAULTS_FACTORY = "0x02Ca7772FF14a9F6c1a08aF385aA96bb1b34175A"

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
REGISTER_TIERS_IN_OPERATOR_GRID_FACTORY = "0x5292A1284e4695B95C0840CF8ea25A818751C17F"
UPDATE_GROUPS_SHARE_LIMIT_IN_OPERATOR_GRID_FACTORY = "0x8Bdc726a3147D8187820391D7c6F9F942606aEe6"  # TODO update address after deployment
SET_JAIL_STATUS_IN_OPERATOR_GRID_FACTORY = "0x93F1DEE4473Ee9F42c8257C201e33a6Da30E5d67"  # TODO update address after deployment
SOCIALIZE_BAD_DEBT_IN_VAULT_HUB_FACTORY = "0x1dF50522A1D868C12bF71747Bb6F24A18Fe6d32C"  # TODO update address after deployment
FORCE_VALIDATOR_EXITS_IN_VAULT_HUB_FACTORY = "0x6C968cD89CA358fbAf57B18e77a8973Fa869a6aA"  # TODO update address after deployment
UPDATE_VAULTS_FEES_IN_OPERATOR_GRID_FACTORY = "0x5C3bDFa3E7f312d8cf72F56F2b797b026f6B471c"  # TODO update address after deployment

# Test parameters
EXPECTED_VOTE_ID = None  # Set to None if vote is not created yet
EXPECTED_DG_PROPOSAL_ID = None  # Set to None if DG proposal is not created yet
EXPECTED_VOTE_EVENTS_COUNT = 15
EXPECTED_DG_EVENTS_FROM_AGENT = 6
EXPECTED_DG_EVENTS_COUNT = 6
IPFS_DESCRIPTION_HASH = ""  # TODO: Update after IPFS upload


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    """Returns list of dual governance proposal calls for events checking"""

    operator_grid = interface.OperatorGrid(OPERATOR_GRID)
    vault_hub = interface.VaultHub(VAULT_HUB)

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

    registry_role = web3.keccak(text="vaults.OperatorsGrid.Registry")
    validator_exit_role = web3.keccak(text="vaults.VaultHub.ValidatorExitRole")
    bad_debt_master_role = web3.keccak(text="vaults.VaultHub.BadDebtMasterRole")


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


        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # Step 1.1. Check old VaultsAdapter does not have REGISTRY_ROLE on OperatorGrid
        assert not operator_grid.hasRole(registry_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should not have REGISTRY_ROLE on OperatorGrid after upgrade"

        # Step 1.2. Check new VaultsAdapter has REGISTRY_ROLE on OperatorGrid
        assert operator_grid.hasRole(registry_role, VAULTS_ADAPTER), "New VaultsAdapter should have REGISTRY_ROLE on OperatorGrid after upgrade"

        # Step 1.3. Check old VaultsAdapter does not have VALIDATOR_EXIT_ROLE on VaultHub
        assert not vault_hub.hasRole(validator_exit_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should not have VALIDATOR_EXIT_ROLE on VaultHub after upgrade"

        # Step 1.4. Check new VaultsAdapter has VALIDATOR_EXIT_ROLE on VaultHub
        assert vault_hub.hasRole(validator_exit_role, VAULTS_ADAPTER), "New VaultsAdapter should have VALIDATOR_EXIT_ROLE on VaultHub after upgrade"

        # Step 1.5. Check old VaultsAdapter does not have BAD_DEBT_MASTER_ROLE on VaultHub
        assert not vault_hub.hasRole(bad_debt_master_role, OLD_VAULTS_ADAPTER), "Old VaultsAdapter should not have BAD_DEBT_MASTER_ROLE on VaultHub after upgrade"

        # Step 1.6. Check new VaultsAdapter has BAD_DEBT_MASTER_ROLE on VaultHub
        assert vault_hub.hasRole(bad_debt_master_role, VAULTS_ADAPTER), "New VaultsAdapter should have BAD_DEBT_MASTER_ROLE on VaultHub after upgrade"
