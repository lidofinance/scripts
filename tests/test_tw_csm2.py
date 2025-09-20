from typing import Optional
from brownie.network.transaction import TransactionReceipt

from utils.dsm import encode_remove_guardian, encode_add_guardian
from utils.test.tx_tracing_helpers import (
    count_vote_items_by_events,
    display_dg_events,
)

from brownie.exceptions import VirtualMachineError
from brownie import interface, reverts, chain, convert, web3, ZERO_ADDRESS  # type: ignore
from brownie.network.event import EventDict
from utils.easy_track import create_permissions
from utils.evm_script import encode_call_script
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.tx_tracing_helpers import display_voting_events
from utils.dual_governance import PROPOSAL_STATUS, wait_for_time_window
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    validate_node_operator_reward_address_set_event,
    NodeOperatorNameSetItem,
    NodeOperatorRewardAddressSetItem,
)
from utils.test.tx_tracing_helpers import group_voting_events_from_receipt, group_dg_events_from_receipt
from utils.test.event_validators.easy_track import validate_evmscript_factory_added_event, EVMScriptFactoryAdded
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.config import contracts

CS_MODULE_ID = 3
CS_MODULE_MODULE_FEE_BP = 600
CS_MODULE_MAX_DEPOSITS_PER_BLOCK = 30
CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CS_MODULE_TREASURY_FEE_BP = 400
CS_GATE_SEAL_ADDRESS = "0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0"


def validate_proxy_upgrade_event(event: EventDict, implementation: str, emitted_by: Optional[str] = None):
    assert "Upgraded" in event, "No Upgraded event found"

    assert event["Upgraded"][0]["implementation"] == implementation, "Wrong implementation address"

    if emitted_by is not None:
        assert convert.to_address(event["Upgraded"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_consensus_version_set_event(event: EventDict, new_version: int, prev_version: int, emitted_by: Optional[str] = None):
    assert "ConsensusVersionSet" in event, "No ConsensusVersionSet event found"

    assert event["ConsensusVersionSet"][0]["version"] == new_version, "Wrong new version"

    assert event["ConsensusVersionSet"][0]["prevVersion"] == prev_version, "Wrong previous version"

    if emitted_by is not None:
        assert convert.to_address(event["ConsensusVersionSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_role_grant_event(event: EventDict, role_hash: str, account: str, emitted_by: Optional[str] = None):
    assert "RoleGranted" in event, "No RoleGranted event found"

    # Strip 0x prefix for consistent comparison
    expected_role_hash = role_hash.replace('0x', '')
    actual_role_hash = event["RoleGranted"][0]["role"].hex().replace('0x', '')

    assert actual_role_hash == expected_role_hash, "Wrong role hash"

    assert convert.to_address(event["RoleGranted"][0]["account"]) == convert.to_address(account), "Wrong account"

    if emitted_by is not None:
        assert convert.to_address(event["RoleGranted"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_role_revoke_event(event: EventDict, role_hash: str, account: str, emitted_by: Optional[str] = None):
    assert "RoleRevoked" in event, "No RoleRevoked event found"

    # Strip 0x prefix for consistent comparison
    expected_role_hash = role_hash.replace('0x', '')
    actual_role_hash = event["RoleRevoked"][0]["role"].hex().replace('0x', '')

    assert actual_role_hash == expected_role_hash, "Wrong role hash"

    assert convert.to_address(event["RoleRevoked"][0]["account"]) == convert.to_address(account), "Wrong account"

    if emitted_by is not None:
        assert convert.to_address(event["RoleRevoked"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_contract_version_set_event(event: EventDict, version: int, emitted_by: Optional[str] = None):
    assert "ContractVersionSet" in event, "No ContractVersionSet event found"

    assert event["ContractVersionSet"][0]["version"] == version, "Wrong version"

    if emitted_by is not None:
        assert convert.to_address(event["ContractVersionSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_bond_curve_added_event(event: EventDict, curve_id: int, emitted_by: Optional[str] = None):
    assert "BondCurveAdded" in event, "No BondCurveAdded event found"

    assert event["BondCurveAdded"][0]["curveId"] == curve_id, "Wrong curve ID"
    # FIXME: Where is the intervals check?

    if emitted_by is not None:
        assert convert.to_address(event["BondCurveAdded"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"

def validate_remove_guardian_event(event: EventDict, guardian_address: str, emitted_by: Optional[str] = None):
    assert "GuardianRemoved" in event, "No GuardianRemoved event found"

    assert event["GuardianRemoved"][0]["guardian"] == guardian_address, "Wrong guardian address"

    if emitted_by is not None:
        assert convert.to_address(event["GuardianRemoved"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"

def validate_add_guardian_event(event: EventDict, guardian_address: str, emitted_by: Optional[str] = None):
    assert "GuardianAdded" in event, "No GuardianAdded event found"

    assert event["GuardianAdded"][0]["guardian"] == guardian_address, "Wrong guardian address"

    if emitted_by is not None:
        assert convert.to_address(event["GuardianAdded"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_staking_module_update_event(
    event: EventDict,
    module_id: int,
    share_limit: int,
    priority_share_threshold: int,
    module_fee_points_bp: int,
    treasury_fee_points_bp: int,
    max_deposits_per_block: int,
    min_deposit_block_distance: int,
    emitted_by: Optional[str] = None
):
    assert "StakingModuleShareLimitSet" in event, "No StakingModuleShareLimitSet event found"
    assert "StakingModuleFeesSet" in event, "No StakingModuleFeesSet event found"
    assert "StakingModuleMaxDepositsPerBlockSet" in event, "No StakingModuleMaxDepositsPerBlockSet event found"
    assert "StakingModuleMinDepositBlockDistanceSet" in event, "No StakingModuleMinDepositBlockDistanceSet event found"

    assert len(event["StakingModuleShareLimitSet"]) == 1, "Multiple StakingModuleShareLimitSet events found"
    assert len(event["StakingModuleFeesSet"]) == 1, "Multiple StakingModuleFeesSet events found"
    assert len(event["StakingModuleMaxDepositsPerBlockSet"]) == 1, "Multiple StakingModuleMaxDepositsPerBlockSet events found"
    assert len(event["StakingModuleMinDepositBlockDistanceSet"]) == 1, "Multiple StakingModuleMinDepositBlockDistanceSet events found"

    assert event["StakingModuleShareLimitSet"][0]["stakingModuleId"] == module_id, "Wrong module ID"
    assert event["StakingModuleShareLimitSet"][0]["stakeShareLimit"] == share_limit, "Wrong share limit"
    assert event["StakingModuleShareLimitSet"][0]["priorityExitShareThreshold"] == priority_share_threshold, "Wrong priority threshold"

    assert event["StakingModuleFeesSet"][0]["stakingModuleFee"] == module_fee_points_bp, "Wrong fee points"
    assert event["StakingModuleFeesSet"][0]["treasuryFee"] == treasury_fee_points_bp, "Wrong treasury fee points"

    assert event["StakingModuleMaxDepositsPerBlockSet"][0]["maxDepositsPerBlock"] == max_deposits_per_block, "Wrong max deposits"

    assert event["StakingModuleMinDepositBlockDistanceSet"][0]["minDepositBlockDistance"] == min_deposit_block_distance, "Wrong min distance"

    if emitted_by is not None:
        assert convert.to_address(event["StakingModuleShareLimitSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"
        assert convert.to_address(event["StakingModuleFeesSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"
        assert convert.to_address(event["StakingModuleMaxDepositsPerBlockSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"
        assert convert.to_address(event["StakingModuleMinDepositBlockDistanceSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def get_ossifiable_proxy_impl(proxy_address):
    """Get implementation address from an OssifiableProxy"""
    proxy = interface.OssifiableProxy(proxy_address)
    return proxy.proxy__getImplementation()


def get_wv_contract_proxy_impl(proxy_address):
    """Get implementation address from an WithdrawalContractProxy"""
    proxy = interface.WithdrawalContractProxy(proxy_address)
    return proxy.implementation()


# FIXME: no method for WV?
def check_proxy_implementation(proxy_address, expected_impl):
    """Check that proxy has expected implementation"""
    actual_impl = get_ossifiable_proxy_impl(proxy_address)
    assert actual_impl == expected_impl, f"Expected impl {expected_impl}, got {actual_impl}"


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.upgrade_tw_csm2 import start_vote, get_vote_items, encode_wv_proxy_upgrade_to, \
    NETHERMIND_NEW_REWARD_ADDRESS

# ============================================================================
# ============================== Constants ===================================
# ============================================================================
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
ARAGON_KERNEL = "0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc"
STETH = "0xAE7ab96520DE3A18E5e111B5EaAb095312D7fE84"

# New core contracts implementations
LIDO_LOCATOR_IMPL = "0x2C298963FB763f74765829722a1ebe0784f4F5Cf"
ACCOUNTING_ORACLE_IMPL = "0xE9906E543274cebcd335d2C560094089e9547e8d"
VALIDATORS_EXIT_BUS_ORACLE_IMPL = "0x905A211eD6830Cfc95643f0bE2ff64E7f3bf9b94"
WITHDRAWAL_VAULT_IMPL = "0x7D2BAa6094E1C4B60Da4cbAF4A77C3f4694fD53D"
STAKING_ROUTER_IMPL = "0x226f9265CBC37231882b7409658C18bB7738173A"
NODE_OPERATORS_REGISTRY_IMPL = "0x6828b023e737f96B168aCd0b5c6351971a4F81aE"

TRIGGERABLE_WITHDRAWALS_GATEWAY = "0xDC00116a0D3E064427dA2600449cfD2566B3037B"
VALIDATOR_EXIT_VERIFIER = "0xbDb567672c867DB533119C2dcD4FB9d8b44EC82f"

# Add missing constants
OLD_GATE_SEAL_ADDRESS = "0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178"
NEW_WQ_GATE_SEAL = "0x8A854C4E750CDf24f138f34A9061b2f556066912"
NEW_TW_GATE_SEAL = "0xA6BC802fAa064414AA62117B4a53D27fFfF741F1"
RESEAL_MANAGER = "0x7914b5a1539b97Bd0bbd155757F25FD79A522d24"
DUAL_GOVERNANCE_TIME_CONSTRAINTS = "0x2a30F5aC03187674553024296bed35Aa49749DDa"

# Add EasyTrack constants
EASYTRACK_EVMSCRIPT_EXECUTOR = "0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E"
EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0xAa3D6A8B52447F272c1E8FAaA06EA06658bd95E2"
EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x397206ecdbdcb1A55A75e60Fc4D054feC72E5f63"

# Oracle consensus versions
AO_CONSENSUS_VERSION = 4
VEBO_CONSENSUS_VERSION = 4
CSM_CONSENSUS_VERSION = 3

EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS = 14 * 7200

NOR_EXIT_DEADLINE_IN_SEC = 172800

# CSM
CS_MODULE_NEW_TARGET_SHARE_BP = 3500  # 3.5%
CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 3750  # 3.75%

CS_ACCOUNTING_IMPL_V2_ADDRESS = "0x6f09d2426c7405C5546413e6059F884D2D03f449"
CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS = "0x5DCF7cF7c6645E9E822a379dF046a8b0390251A1"
CS_FEE_ORACLE_IMPL_V2_ADDRESS = "0xe0B234f99E413E27D9Bc31aBba9A49A3e570Da97"
CSM_IMPL_V2_ADDRESS = "0x1eB6d4da13ca9566c17F526aE0715325d7a07665"

CS_GATE_SEAL_V2_ADDRESS = "0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3"

# CSM consensus version
CSM_CONSENSUS_VERSION = 3

# Bond curves for CS Accounting
CS_CURVES = [
    ([1, 2.4 * 10 ** 18], [2, 1.3 * 10 ** 18]),  # Default Curve
    ([1, 1.5 * 10 ** 18], [2, 1.3 * 10 ** 18]),  # Legacy EA Curve
]
CS_ICS_GATE_BOND_CURVE = ([1, 1.5 * 10 ** 18], [2, 1.3 * 10 ** 18])  # Identified Community Stakers Gate Bond Curve

# CSM committee and config addresses (imported from config in actual script)
CSM_COMMITTEE_MS = "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f"
CS_GATE_SEAL_ADDRESS = "0x16Dbd4B85a448bE564f1742d5c8cCdD2bB3185D0"

# CSM staking module constants (from config)
CS_ORACLE_EPOCHS_PER_FRAME = 225 * 28  # 28 days
CS_MODULE_ID = 3
CS_MODULE_NAME = "Community Staking"
CS_MODULE_MODULE_FEE_BP = 600
CS_MODULE_TREASURY_FEE_BP = 400
CS_MODULE_TARGET_SHARE_BP = 300 # Updated from 200 to 300 in vote 2025/07/16
CS_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD = 375 # Updated from 250 to 375 in vote 2025/07/16
CS_MODULE_MAX_DEPOSITS_PER_BLOCK = 30
CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CS_EJECTOR_ADDRESS = "0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C"
CS_PERMISSIONLESS_GATE_ADDRESS = "0xcF33a38111d0B1246A3F38a838fb41D626B454f0"
CS_VETTED_GATE_ADDRESS = "0xB314D4A76C457c93150d308787939063F4Cc67E0"
CS_VERIFIER_V2_ADDRESS = "0xdC5FE1782B6943f318E05230d688713a560063DC"

CS_VERIFIER_ADDRESS_OLD = "0xeC6Cc185f671F627fb9b6f06C8772755F587b05d"

CS_CURVES = [
    ([1, 2.4 * 10 ** 18], [2, 1.3 * 10 ** 18]),  # Default Curve
    ([1, 1.5 * 10 ** 18], [2, 1.3 * 10 ** 18]),  # Legacy EA Curve
]
CS_ICS_GATE_BOND_CURVE = ([1, 1.5 * 10 ** 18], [2, 1.3 * 10 ** 18])  # Identified Community Stakers Gate Bond Curve

# Contract versions expected after upgrade
CSM_V2_VERSION = 2
CS_ACCOUNTING_V2_VERSION = 2
CS_FEE_ORACLE_V2_VERSION = 2
CS_FEE_DISTRIBUTOR_V2_VERSION = 2

EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY = "0xBc5642bDD6F2a54b01A75605aAe9143525D97308"

EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = 5
EXPECTED_VOTE_EVENTS_COUNT = 4
EXPECTED_DG_EVENTS_FROM_AGENT = 69
EXPECTED_DG_EVENTS_COUNT = 71
IPFS_DESCRIPTION_HASH = "bafkreih5app23xbevhswk56r6d2cjdqui5tckki6szo7loi7xe25bfgol4"

NETHERMIND_NO_ID = 25
NETHERMIND_NO_NAME_OLD = "Nethermind"
NETHERMIND_NO_NAME_NEW = "Twinstake"
NETHERMIND_NO_STAKING_REWARDS_ADDRESS_OLD = "0x237DeE529A47750bEcdFa8A59a1D766e3e7B5F91"
NETHERMIND_NO_STAKING_REWARDS_ADDRESS_NEW = "0x36201ed66DbC284132046ee8d99272F8eEeb24c8"
NODE_OPERATORS_REGISTRY_ADDRESS = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"

NODE_OPERATORS_REGISTRY_ARAGON_APP_ID = "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d"
SIMPLE_DVT_ARAGON_APP_ID = "0xe1635b63b5f7b5e545f2a637558a4029dea7905361a2f0fc28c66e9136cf86a4"

OLD_KILN_ADDRESS = "0x14D5d5B71E048d2D75a39FfC5B407e3a3AB6F314"
NEW_KILN_ADDRESS = "0x6d22aE126eB2c37F67a1391B37FF4f2863e61389"
MAX_VALIDATORS_PER_REPORT = 600
MAX_EXIT_REQUESTS_LIMIT = 11200
EXITS_PER_FRAME = 1
FRAME_DURATION_IN_SEC = 48

import pytest
from utils.agent import agent_forward
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.node_operators import encode_set_node_operator_name, encode_set_node_operator_reward_address


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    """Returns list of dual governance proposal calls for events checking"""

    # Helper function to encode proxy upgrades
    def encode_proxy_upgrade_to(proxy_contract, new_impl_address):
        return (proxy_contract.address, proxy_contract.proxy__upgradeTo.encode_input(new_impl_address))

    # Helper function to encode oracle consensus upgrades
    def encode_oracle_upgrade_consensus(oracle_contract, new_version):
        return (oracle_contract.address, oracle_contract.setConsensusVersion.encode_input(new_version))

    # Cast contracts to OssifiableProxy interface to access proxy methods
    _ = interface.StETH(STETH) # Loading ABI to parse DG events
    lido_locator_proxy = interface.OssifiableProxy(contracts.lido_locator.address)
    vebo_proxy = interface.OssifiableProxy(contracts.validators_exit_bus_oracle.address)
    withdrawal_vault_proxy = interface.OssifiableProxy(contracts.withdrawal_vault.address)
    accounting_oracle_proxy = interface.OssifiableProxy(contracts.accounting_oracle.address)
    staking_router_proxy = interface.OssifiableProxy(contracts.staking_router.address)
    csm_proxy = interface.OssifiableProxy(contracts.csm.address)
    cs_accounting_proxy = interface.OssifiableProxy(contracts.cs_accounting.address)
    cs_fee_oracle_proxy = interface.OssifiableProxy(contracts.cs_fee_oracle.address)
    cs_fee_distributor_proxy = interface.OssifiableProxy(contracts.cs_fee_distributor.address)

    # Create all the dual governance calls that match the voting script
    dg_items = [
        # 1. Update locator implementation
        agent_forward([encode_proxy_upgrade_to(lido_locator_proxy, LIDO_LOCATOR_IMPL)]),

        # 2. Update VEBO implementation
        agent_forward([encode_proxy_upgrade_to(vebo_proxy, VALIDATORS_EXIT_BUS_ORACLE_IMPL)]),

        # 3. Call finalizeUpgrade_v2 on VEBO
        agent_forward([
            (contracts.validators_exit_bus_oracle.address,
             contracts.validators_exit_bus_oracle.finalizeUpgrade_v2.encode_input(MAX_VALIDATORS_PER_REPORT,
                                                                                  MAX_EXIT_REQUESTS_LIMIT,
                                                                                  EXITS_PER_FRAME,
                                                                                  FRAME_DURATION_IN_SEC))
        ]),

        # 4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.validators_exit_bus_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                grant_to=contracts.agent
            )
        ]),

        # 5. Bump VEBO consensus version to 4
        agent_forward([encode_oracle_upgrade_consensus(contracts.validators_exit_bus_oracle, VEBO_CONSENSUS_VERSION)]),

        # 6. Revoke VEBO role MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.validators_exit_bus_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                revoke_from=contracts.agent
            )
        ]),

        # 7. Grant SUBMIT_REPORT_HASH_ROLE on VEBO to EasyTrack executor
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.validators_exit_bus_oracle,
                role_name="SUBMIT_REPORT_HASH_ROLE",
                grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR
            )
        ]),

        # 8. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to CS Ejector
        agent_forward([
            encode_oz_grant_role(
                contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                grant_to=CS_EJECTOR_ADDRESS
            )
        ]),

        # 9. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to VEBO
        agent_forward([
            encode_oz_grant_role(
                contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                grant_to=contracts.validators_exit_bus_oracle.address
            )
        ]),

        # 10. Connect TWG to Dual Governance tiebreaker
        (
            interface.DualGovernance(DUAL_GOVERNANCE).address,
            interface.DualGovernance(DUAL_GOVERNANCE).addTiebreakerSealableWithdrawalBlocker.encode_input(
                TRIGGERABLE_WITHDRAWALS_GATEWAY)
        ),

        # 11. Update WithdrawalVault implementation
        agent_forward([encode_wv_proxy_upgrade_to(withdrawal_vault_proxy, WITHDRAWAL_VAULT_IMPL)]),

        # 12. Call finalizeUpgrade_v2() on WithdrawalVault
        agent_forward([
            (contracts.withdrawal_vault.address, contracts.withdrawal_vault.finalizeUpgrade_v2.encode_input())
        ]),

        # 13. Update Accounting Oracle implementation
        agent_forward([encode_proxy_upgrade_to(accounting_oracle_proxy, ACCOUNTING_ORACLE_IMPL)]),

        # 14. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.accounting_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                grant_to=contracts.agent
            )
        ]),

        # 15. Bump AO consensus version to 4
        agent_forward([encode_oracle_upgrade_consensus(contracts.accounting_oracle, AO_CONSENSUS_VERSION)]),

        # 16. Revoke AO MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.accounting_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                revoke_from=contracts.agent
            )
        ]),

        # 17. Call finalizeUpgrade_v3() on AO
        agent_forward([
            (contracts.accounting_oracle.address, contracts.accounting_oracle.finalizeUpgrade_v3.encode_input())
        ]),

        # 18. Update SR implementation
        agent_forward([encode_proxy_upgrade_to(staking_router_proxy, STAKING_ROUTER_IMPL)]),

        # 19. Call finalizeUpgrade_v3() on SR
        agent_forward([
            (contracts.staking_router.address, contracts.staking_router.finalizeUpgrade_v3.encode_input())
        ]),

        # 20. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitVerifier
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.staking_router,
                role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                grant_to=VALIDATOR_EXIT_VERIFIER
            )
        ]),

        # 21. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.staking_router,
                role_name="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE",
                grant_to=TRIGGERABLE_WITHDRAWALS_GATEWAY
            )
        ]),

        # 22-27: Kernel and registry upgrades
        # 22. Grant APP_MANAGER_ROLE role to the AGENT
        agent_forward([
            (contracts.acl.address,
             contracts.acl.grantPermission.encode_input(
                 AGENT,
                 ARAGON_KERNEL,
                 web3.keccak(text="APP_MANAGER_ROLE")
             ))
        ]),

        # 23. Update NodeOperatorsRegistry implementation
        agent_forward([
            (contracts.kernel.address,
             contracts.kernel.setApp.encode_input(
                 contracts.kernel.APP_BASES_NAMESPACE(),
                 NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
                 NODE_OPERATORS_REGISTRY_IMPL
             ))
        ]),

        # 24. Call finalizeUpgrade_v4 on Curated Staking Module
        agent_forward([
            (interface.NodeOperatorsRegistry(contracts.node_operators_registry).address,
             interface.NodeOperatorsRegistry(contracts.node_operators_registry).finalizeUpgrade_v4.encode_input(
                 NOR_EXIT_DEADLINE_IN_SEC))
        ]),

        # 25. Update SDVT implementation
        agent_forward([
            (contracts.kernel.address,
             contracts.kernel.setApp.encode_input(
                 contracts.kernel.APP_BASES_NAMESPACE(),
                 SIMPLE_DVT_ARAGON_APP_ID,
                 NODE_OPERATORS_REGISTRY_IMPL
             ))
        ]),

        # 26. Call finalizeUpgrade_v4 on SDVT
        agent_forward([
            (interface.NodeOperatorsRegistry(contracts.simple_dvt).address,
             interface.NodeOperatorsRegistry(contracts.simple_dvt).finalizeUpgrade_v4.encode_input(
                 NOR_EXIT_DEADLINE_IN_SEC))
        ]),

        # 27. Revoke APP_MANAGER_ROLE role from the AGENT
        agent_forward([
            (contracts.acl.address,
             contracts.acl.revokePermission.encode_input(
                 AGENT,
                 ARAGON_KERNEL,
                 web3.keccak(text="APP_MANAGER_ROLE")
             ))
        ]),

        # 28-33: Oracle daemon config changes
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.oracle_daemon_config,
                role_name="CONFIG_MANAGER_ROLE",
                grant_to=contracts.agent
            )
        ]),

        agent_forward([
            (contracts.oracle_daemon_config.address,
             contracts.oracle_daemon_config.unset.encode_input('NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP'))
        ]),

        agent_forward([
            (contracts.oracle_daemon_config.address,
             contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS'))
        ]),

        agent_forward([
            (contracts.oracle_daemon_config.address,
             contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS'))
        ]),

        agent_forward([
            (contracts.oracle_daemon_config.address,
             contracts.oracle_daemon_config.set.encode_input('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS',
                                                             EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS))
        ]),

        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.oracle_daemon_config,
                role_name="CONFIG_MANAGER_ROLE",
                revoke_from=contracts.agent
            )
        ]),

        # CSM upgrades and role changes (steps 34-59)
        # 34. Upgrade CSM implementation on proxy
        agent_forward([encode_proxy_upgrade_to(csm_proxy, CSM_IMPL_V2_ADDRESS)]),

        # 35. Call finalizeUpgradeV2() on CSM contract
        agent_forward([(contracts.csm.address, contracts.csm.finalizeUpgradeV2.encode_input())]),

        # 36. Upgrade CSAccounting implementation on proxy
        agent_forward([encode_proxy_upgrade_to(cs_accounting_proxy, CS_ACCOUNTING_IMPL_V2_ADDRESS)]),

        # 37. Call finalizeUpgradeV2(bondCurves) on CSAccounting contract
        agent_forward([
            (contracts.cs_accounting.address,
             contracts.cs_accounting.finalizeUpgradeV2.encode_input(CS_CURVES))
        ]),

        # 38. Upgrade CSFeeOracle implementation on proxy
        agent_forward([encode_proxy_upgrade_to(cs_fee_oracle_proxy, CS_FEE_ORACLE_IMPL_V2_ADDRESS)]),

        # 39. Call finalizeUpgradeV2(consensusVersion) on CSFeeOracle contract
        agent_forward([
            (contracts.cs_fee_oracle.address,
             contracts.cs_fee_oracle.finalizeUpgradeV2.encode_input(CSM_CONSENSUS_VERSION))
        ]),

        # 40. Upgrade CSFeeDistributor implementation on proxy
        agent_forward([encode_proxy_upgrade_to(cs_fee_distributor_proxy, CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS)]),

        # 41. Call finalizeUpgradeV2(admin) on CSFeeDistributor contract
        agent_forward([
            (contracts.cs_fee_distributor.address,
             contracts.cs_fee_distributor.finalizeUpgradeV2.encode_input(contracts.agent))
        ]),

        # 42. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="SET_BOND_CURVE_ROLE",
                revoke_from=contracts.csm
            )
        ]),

        # 43. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="RESET_BOND_CURVE_ROLE",
                revoke_from=contracts.csm
            )
        ]),

        # 44. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="RESET_BOND_CURVE_ROLE",
                revoke_from=CSM_COMMITTEE_MS
            )
        ]),

        # 45. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.csm,
                role_name="CREATE_NODE_OPERATOR_ROLE",
                grant_to=CS_PERMISSIONLESS_GATE_ADDRESS
            )
        ]),

        # 46. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.csm,
                role_name="CREATE_NODE_OPERATOR_ROLE",
                grant_to=CS_VETTED_GATE_ADDRESS
            )
        ]),

        # 47. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.cs_accounting,
                role_name="SET_BOND_CURVE_ROLE",
                grant_to=CS_VETTED_GATE_ADDRESS
            )
        ]),

        # 48. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.csm,
                role_name="VERIFIER_ROLE",
                revoke_from=CS_VERIFIER_ADDRESS_OLD
            )
        ]),

        # 49. Grant role VERIFIER_ROLE to the new instance of the Verifier contract
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.csm,
                role_name="VERIFIER_ROLE",
                grant_to=CS_VERIFIER_V2_ADDRESS
            )
        ]),

        # 50. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.csm,
                role_name="PAUSE_ROLE",
                revoke_from=CS_GATE_SEAL_ADDRESS
            )
        ]),

        # 51. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="PAUSE_ROLE",
                revoke_from=CS_GATE_SEAL_ADDRESS
            )
        ]),

        # 52. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.cs_fee_oracle,
                role_name="PAUSE_ROLE",
                revoke_from=CS_GATE_SEAL_ADDRESS
            )
        ]),

        # 53. Grant CSM role PAUSE_ROLE for the new GateSeal instance
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.csm,
                role_name="PAUSE_ROLE",
                grant_to=CS_GATE_SEAL_V2_ADDRESS
            )
        ]),

        # 54. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.cs_accounting,
                role_name="PAUSE_ROLE",
                grant_to=CS_GATE_SEAL_V2_ADDRESS
            )
        ]),

        # 55. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.cs_fee_oracle,
                role_name="PAUSE_ROLE",
                grant_to=CS_GATE_SEAL_V2_ADDRESS
            )
        ]),

        # 56. Grant MANAGE_BOND_CURVES_ROLE to the AGENT
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.cs_accounting,
                role_name="MANAGE_BOND_CURVES_ROLE",
                grant_to=contracts.agent
            )
        ]),

        # 57. Add Identified Community Stakers Gate Bond Curve
        agent_forward([
            (contracts.cs_accounting.address,
             contracts.cs_accounting.addBondCurve.encode_input(CS_ICS_GATE_BOND_CURVE))
        ]),

        # 58. Revoke MANAGE_BOND_CURVES_ROLE from the AGENT
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="MANAGE_BOND_CURVES_ROLE",
                revoke_from=contracts.agent
            )
        ]),

        # 59. Increase CSM share in Staking Router from 15% to 16%
        agent_forward([
            (contracts.staking_router.address,
             contracts.staking_router.updateStakingModule.encode_input(
                 CS_MODULE_ID,
                 CS_MODULE_NEW_TARGET_SHARE_BP,
                 CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
                 CS_MODULE_MODULE_FEE_BP,
                 CS_MODULE_TREASURY_FEE_BP,
                 CS_MODULE_MAX_DEPOSITS_PER_BLOCK,
                 CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE
             ))
        ]),

        # Gate seals and node operator changes (steps 60-68)
        # 60. Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.withdrawal_queue,
                role_name="PAUSE_ROLE",
                revoke_from=OLD_GATE_SEAL_ADDRESS
            )
        ]),

        # 61. Revoke PAUSE_ROLE on ValidatorsExitBusOracle from the old GateSeal
        agent_forward([
            encode_oz_revoke_role(
                contract=contracts.validators_exit_bus_oracle,
                role_name="PAUSE_ROLE",
                revoke_from=OLD_GATE_SEAL_ADDRESS
            )
        ]),

        # 62. Grant PAUSE_ROLE on WithdrawalQueue to the new WithdrawalQueue GateSeal
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.withdrawal_queue,
                role_name="PAUSE_ROLE",
                grant_to=NEW_WQ_GATE_SEAL
            )
        ]),

        # 63. Grant PAUSE_ROLE on ValidatorsExitBusOracle to the new Triggerable Withdrawals GateSeal
        agent_forward([
            encode_oz_grant_role(
                contract=contracts.validators_exit_bus_oracle,
                role_name="PAUSE_ROLE",
                grant_to=NEW_TW_GATE_SEAL
            )
        ]),

        # 64. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to the new Triggerable Withdrawals GateSeal
        agent_forward([
            encode_oz_grant_role(
                contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                role_name="PAUSE_ROLE",
                grant_to=NEW_TW_GATE_SEAL
            )
        ]),

        # 65. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to ResealManager
        agent_forward([
            encode_oz_grant_role(
                contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                role_name="PAUSE_ROLE",
                grant_to=RESEAL_MANAGER
            )
        ]),

        # 66. Grant RESUME_ROLE on TriggerableWithdrawalsGateway to ResealManager
        agent_forward([
            encode_oz_grant_role(
                contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                role_name="RESUME_ROLE",
                grant_to=RESEAL_MANAGER
            )
        ]),

        # Node operator changes
        # 67. Rename Node Operator ID 25 from Nethermind to Twinstake
        agent_forward(
            [encode_set_node_operator_name(id=25, name="Twinstake", registry=contracts.node_operators_registry)]),

        # 68. Change Node Operator ID 17 reward address
        agent_forward([encode_set_node_operator_reward_address(id=25,
                                                               rewardAddress="0x36201ed66DbC284132046ee8d99272F8eEeb24c8",
                                                               registry=contracts.node_operators_registry)]),
        # "69. Remove Kiln guardian"
        agent_forward([
            encode_remove_guardian(dsm=contracts.deposit_security_module, guardian_address=OLD_KILN_ADDRESS, quorum_size=4),
        ]),
        # "70. Add new Kiln guardian"
        agent_forward([
            encode_add_guardian(dsm=contracts.deposit_security_module, guardian_address=NEW_KILN_ADDRESS, quorum_size=4),
        ]),
        # "71. Set time constraints for execution (13:00 to 19:00 UTC)"
        (
            DUAL_GOVERNANCE_TIME_CONSTRAINTS,
            interface.TimeConstraints(DUAL_GOVERNANCE_TIME_CONSTRAINTS).checkTimeWithinDayTimeAndEmit.encode_input(
                3600 * 13,  # 13:00 UTC
                3600 * 19   # 19:00 UTC
            ),
        ),
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
    # Save original implementations for comparison
    locator_impl_before = get_ossifiable_proxy_impl(contracts.lido_locator)
    accounting_oracle_impl_before = get_ossifiable_proxy_impl(contracts.accounting_oracle)
    vebo_impl_before = get_ossifiable_proxy_impl(contracts.validators_exit_bus_oracle)
    withdrawal_vault_impl_before = get_wv_contract_proxy_impl(contracts.withdrawal_vault)
    staking_router_impl_before = get_ossifiable_proxy_impl(contracts.staking_router)

    csm_impl_before = get_ossifiable_proxy_impl(contracts.csm.address)
    cs_accounting_impl_before = get_ossifiable_proxy_impl(contracts.cs_accounting.address)
    cs_fee_oracle_impl_before = get_ossifiable_proxy_impl(contracts.cs_fee_oracle.address)
    cs_fee_distributor_impl_before = get_ossifiable_proxy_impl(contracts.cs_fee_distributor.address)

    voting = interface.Voting(VOTING)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)

    # Not yet used by the protocol, but needed for the test
    triggerable_withdrawals_gateway = interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)
    cs_ejector = interface.CSEjector(CS_EJECTOR_ADDRESS)
    cs_permissionless_gate = interface.CSPermissionlessGate(CS_PERMISSIONLESS_GATE_ADDRESS)
    cs_vetted_gate = interface.CSVettedGate(CS_VETTED_GATE_ADDRESS)
    cs_verifier_v2 = interface.CSVerifierV2(CS_VERIFIER_V2_ADDRESS)

    no_registry = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY_ADDRESS)

    # START VOTE
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

    # ============================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================
        # CSM Step 65: EasyTrack factories before vote (pre-vote state)
        initial_factories = contracts.easy_track.getEVMScriptFactories()
        assert EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY not in initial_factories, "EasyTrack should not have CSMSetVettedGateTree factory before vote"
        assert EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY not in initial_factories, "EasyTrack should not have SDVT validator exit request hashes factory before vote"
        assert EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY not in initial_factories, "EasyTrack should not have Curated validator exit request hashes factory before vote"

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        #display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        # Step 65: Add EasyTrack factory for CSSetVettedGateTree
        new_factories = contracts.easy_track.getEVMScriptFactories()
        assert EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY in new_factories, "EasyTrack should have CSSetVettedGateTree factory after vote"

        # Steps 66-67: Validate EasyTrack factories for validator exit request hashes
        assert EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY in new_factories, "EasyTrack should have SDVT validator exit request hashes factory after vote"
        assert EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY in new_factories, "EasyTrack should have Curated validator exit request hashes factory after vote"

        # --- VALIDATE EVENTS ---
        voting_events = group_voting_events_from_receipt(vote_tx)
        # Validate voting events structure
        dg_voting_event, dg_bypass_voting_event1, dg_bypass_voting_event2, dg_bypass_voting_event3 = voting_events

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT, "Unexpected number of dual governance events"
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT
        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

            # Validate DG Proposal Submit event
            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata="Upgrade to CSM v2, enable Triggerable Withdrawals, migrate Nethermind → Twinstake, rotate Kiln Guardian",
                proposal_calls=dual_governance_proposal_calls,
                emitted_by=[EMERGENCY_PROTECTED_TIMELOCK, DUAL_GOVERNANCE],
            )

            # Validate EasyTrack bypass events for new factories
            validate_evmscript_factory_added_event(
                event=dg_bypass_voting_event1,
                p=EVMScriptFactoryAdded(
                    factory_addr=EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY,
                    permissions=create_permissions(interface.CSVettedGate(CS_VETTED_GATE_ADDRESS), "setTreeParams")
                ),
                emitted_by=contracts.easy_track,
            )

            validate_evmscript_factory_added_event(
                event=dg_bypass_voting_event2,
                p=EVMScriptFactoryAdded(
                    factory_addr=EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                    permissions=create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")
                ),
                emitted_by=contracts.easy_track,
            )

            validate_evmscript_factory_added_event(
                event=dg_bypass_voting_event3,
                p=EVMScriptFactoryAdded(
                    factory_addr=EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                    permissions=create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")
                ),
                emitted_by=contracts.easy_track,
            )

    if EXPECTED_DG_PROPOSAL_ID is not None:
        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================
            # Step 1: Check Lido Locator implementation initial state
            assert locator_impl_before != LIDO_LOCATOR_IMPL, "Locator implementation should be different before upgrade"

            # Step 2: Check VEBO implementation initial state
            assert vebo_impl_before != VALIDATORS_EXIT_BUS_ORACLE_IMPL, "VEBO implementation should be different before upgrade"

            # Step 3: Check VEBO finalizeUpgrade_v2 state
            try:  # FIXME: with reverts
                assert contracts.validators_exit_bus_oracle.getMaxValidatorsPerReport() != 600, "VEBO max validators per report should not be 600 before upgrade"  # FIXME: magic number
            except Exception:
                pass  # Function might not exist yet

            # Steps 4-6: Check VEBO consensus version management
            initial_vebo_consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
            assert initial_vebo_consensus_version < VEBO_CONSENSUS_VERSION, f"VEBO consensus version should be less than {VEBO_CONSENSUS_VERSION}"

            # Step 7: Check TWG role for CS Ejector initial state
            add_full_withdrawal_request_role = triggerable_withdrawals_gateway.ADD_FULL_WITHDRAWAL_REQUEST_ROLE()
            assert not triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role,
                                                               cs_ejector), "CS Ejector should not have ADD_FULL_WITHDRAWAL_REQUEST_ROLE before upgrade"

            # Step 8: Check TWG role for VEB initial state
            assert not triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role,
                                                               contracts.validators_exit_bus_oracle), "VEBO should not have ADD_FULL_WITHDRAWAL_REQUEST_ROLE before upgrade"

            # Step 9: Check EasyTrack VEB SUBMIT_REPORT_HASH_ROLE initial state
            submit_report_hash_role = web3.keccak(text="SUBMIT_REPORT_HASH_ROLE")
            assert not contracts.validators_exit_bus_oracle.hasRole(submit_report_hash_role,
                                                                    EASYTRACK_EVMSCRIPT_EXECUTOR), "EasyTrack executor should not have SUBMIT_REPORT_HASH_ROLE on VEBO before upgrade"

            # Step 10: Check DualGovernance tiebreaker initial state
            tiebreaker_details = contracts.dual_governance.getTiebreakerDetails()
            initial_tiebreakers = tiebreaker_details[3]  # sealableWithdrawalBlockers
            assert TRIGGERABLE_WITHDRAWALS_GATEWAY not in initial_tiebreakers, "TWG should not be in tiebreaker list before upgrade"

            # Step 9: Check Withdrawal Vault implementation initial state
            assert withdrawal_vault_impl_before != WITHDRAWAL_VAULT_IMPL, "Withdrawal Vault implementation should be different before upgrade"

            # Step 10: Withdrawal Vault finalizeUpgrade_v2 check is done post-execution
            assert contracts.withdrawal_vault.getContractVersion() == 1, "Withdrawal Vault version should be 1 before upgrade"

            # Step 11: Check Accounting Oracle implementation initial state
            assert accounting_oracle_impl_before != ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be different before upgrade"

            # Steps 12-14: Check AO consensus version management
            initial_ao_consensus_version = contracts.accounting_oracle.getConsensusVersion()
            assert initial_ao_consensus_version < AO_CONSENSUS_VERSION, f"AO consensus version should be less than {AO_CONSENSUS_VERSION}"
            assert not contracts.accounting_oracle.hasRole(contracts.accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE(),
                                                           contracts.agent), "Agent should not have MANAGE_CONSENSUS_VERSION_ROLE on AO before upgrade"

            # Step 17: Check AO version before finalizeUpgrade_v3
            assert contracts.accounting_oracle.getContractVersion() == 2, "AO contract version should be 2 before finalizeUpgrade_v3"

            # Step 15: Check Staking Router implementation initial state
            assert staking_router_impl_before != STAKING_ROUTER_IMPL, "Staking Router implementation should be different before upgrade"

            # Steps 16-17: Check SR roles initial state
            try:
                report_validator_exiting_status_role = contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE()
                report_validator_exit_triggered_role = contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE()
            except Exception as e:
                assert "Unknown typed error: 0x" in str(e), f"Unexpected error: {e}"
                report_validator_exiting_status_role = ZERO_ADDRESS
                report_validator_exit_triggered_role = ZERO_ADDRESS

            assert report_validator_exiting_status_role == ZERO_ADDRESS, "REPORT_VALIDATOR_EXITING_STATUS_ROLE should not exist before upgrade"
            assert report_validator_exit_triggered_role == ZERO_ADDRESS, "REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE should not exist before upgrade"

            # Step 18: Check APP_MANAGER_ROLE initial state
            app_manager_role = web3.keccak(text="APP_MANAGER_ROLE")
            assert contracts.acl.getPermissionManager(ARAGON_KERNEL,
                                                      app_manager_role) == AGENT, "AGENT should be the permission manager for APP_MANAGER_ROLE"
            assert contracts.node_operators_registry.kernel() == ARAGON_KERNEL, "Node Operators Registry must use the correct kernel"
            assert not contracts.acl.hasPermission(VOTING, ARAGON_KERNEL,
                                                   app_manager_role), "VOTING should not have APP_MANAGER_ROLE before the upgrade"
            assert not contracts.acl.hasPermission(AGENT, ARAGON_KERNEL,
                                                   app_manager_role), "AGENT should not have APP_MANAGER_ROLE before the upgrade"

            # Steps 19-23: Check NOR and sDVT initial state
            assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel,
                                                   app_manager_role), "Agent should not have APP_MANAGER_ROLE before upgrade"
            assert contracts.node_operators_registry.getContractVersion() == 3, "Node Operators Registry version should be 3 before upgrade"
            assert contracts.simple_dvt.getContractVersion() == 3, "Simple DVT version should be 3 before upgrade"

            # Step 24: Check CONFIG_MANAGER_ROLE initial state
            config_manager_role = contracts.oracle_daemon_config.CONFIG_MANAGER_ROLE()
            assert not contracts.oracle_daemon_config.hasRole(config_manager_role,
                                                              contracts.agent), "Agent should not have CONFIG_MANAGER_ROLE on Oracle Daemon Config before upgrade"

            # Steps 25-27: Check Oracle Daemon Config variables to be removed
            try:
                contracts.oracle_daemon_config.get('NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP')
                contracts.oracle_daemon_config.get('VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS')
                contracts.oracle_daemon_config.get('VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS')
            except Exception as e:
                assert False, f"Expected variables to exist before removal: {e}"

            # Step 28: Check that EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS doesn't exist yet
            try:
                contracts.oracle_daemon_config.get('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS')
                assert False, "EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS should not exist before vote"
            except Exception:
                pass  # Expected to fail

            # Step 29: Check CSM implementation initial state
            assert csm_impl_before != CSM_IMPL_V2_ADDRESS, "CSM implementation should be different before vote"

            # Step 30: Check CSM finalizeUpgradeV2 initial state
            with reverts():
                # The function should not exist yet
                contracts.csm.getInitializedVersion()

            # CSM Step 32: Check CSAccounting implementation (pre-vote state)
            assert cs_accounting_impl_before != CS_ACCOUNTING_IMPL_V2_ADDRESS, "CSAccounting implementation should be different before vote"

            # CSM Step 33: Check CSAccounting finalizeUpgradeV2 was not called (pre-vote state)
            with reverts():
                # The function should not exist yet
                contracts.cs_accounting.getInitializedVersion()

            # CSM Step 34: Check CSFeeOracle implementation (pre-vote state)
            assert cs_fee_oracle_impl_before != CS_FEE_ORACLE_IMPL_V2_ADDRESS, "CSFeeOracle implementation should be different before vote"

            # CSM Step 35: Check CSFeeOracle finalizeUpgradeV2 was not called (pre-vote state)
            assert contracts.cs_fee_oracle.getContractVersion() < CS_FEE_ORACLE_V2_VERSION, f"CSFeeOracle version should be less than {CS_FEE_ORACLE_V2_VERSION} before vote"
            assert contracts.cs_fee_oracle.getConsensusVersion() < 3, "CSFeeOracle consensus version should be less than 3 before vote"

            # CSM Step 36: Check CSFeeDistributor implementation (pre-vote state)
            assert cs_fee_distributor_impl_before != CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS, "CSFeeDistributor implementation should be different before vote"

            # CSM Step 37: Check CSFeeDistributor finalizeUpgradeV2 was not called (pre-vote state)
            with reverts():
                # The function should not exist yet
                contracts.cs_fee_distributor.getInitializedVersion()

            # CSM Steps 38-40: CSAccounting roles (pre-vote state)
            assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), contracts.csm.address), "CSM should have SET_BOND_CURVE_ROLE on CSAccounting before vote"
            assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), contracts.csm.address), "CSM should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"
            assert contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"), CSM_COMMITTEE_MS), "CSM committee should have RESET_BOND_CURVE_ROLE on CSAccounting before vote"

            # CSM Steps 41-42: CSM roles (pre-vote state)
            assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), cs_permissionless_gate.address), "Permissionless gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"
            assert not contracts.csm.hasRole(web3.keccak(text="CREATE_NODE_OPERATOR_ROLE"), cs_vetted_gate.address), "Vetted gate should not have CREATE_NODE_OPERATOR_ROLE on CSM before vote"

            # CSM Step 43: CSAccounting bond curve role for vetted gate (pre-vote state)
            assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(), cs_vetted_gate.address), "Vetted gate should not have SET_BOND_CURVE_ROLE on CSAccounting before vote"

            # CSM Steps 44-45: Verifier roles (pre-vote state)
            assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), CS_VERIFIER_ADDRESS_OLD), "Old verifier should have VERIFIER_ROLE on CSM before vote"
            assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(), cs_verifier_v2.address), "New verifier should not have VERIFIER_ROLE on CSM before vote"

            # CSM Steps 46-51: GateSeal roles (pre-vote state)
            assert contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSM before vote"
            assert contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSAccounting before vote"
            assert contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on CSFeeOracle before vote"

            assert not contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSM before vote"
            assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSAccounting before vote"
            assert not contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should not have PAUSE_ROLE on CSFeeOracle before vote"

            # CSM Step 52: Staking Router CSM module state before vote (pre-vote state)
            csm_module_before = contracts.staking_router.getStakingModule(CS_MODULE_ID)
            csm_share_before = csm_module_before['stakeShareLimit']
            csm_priority_exit_threshold_before = csm_module_before['priorityExitShareThreshold']
            assert csm_share_before != CS_MODULE_NEW_TARGET_SHARE_BP, f"CSM share should not be {CS_MODULE_NEW_TARGET_SHARE_BP} before vote, current: {csm_share_before}"
            assert csm_priority_exit_threshold_before != CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP, f"CSM priority exit threshold should not be {CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP} before vote, current: {csm_priority_exit_threshold_before}"

            # Gate Seals: Check initial states before vote
            assert contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), OLD_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on WithdrawalQueue before vote"
            assert contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.PAUSE_ROLE(), OLD_GATE_SEAL_ADDRESS), "Old GateSeal should have PAUSE_ROLE on VEBO before vote"
            assert not contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(), NEW_WQ_GATE_SEAL), "New WQ GateSeal should not have PAUSE_ROLE on WithdrawalQueue before vote"
            assert not contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.PAUSE_ROLE(), NEW_TW_GATE_SEAL), "New TW GateSeal should not have PAUSE_ROLE on VEBO before vote"
            assert not triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.PAUSE_ROLE(), NEW_TW_GATE_SEAL), "New TW GateSeal should not have PAUSE_ROLE on TWG before vote"

            # ResealManager: Check initial states before vote
            assert not triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.PAUSE_ROLE(), RESEAL_MANAGER), "ResealManager should not have PAUSE_ROLE on TWG before vote"
            assert not triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.RESUME_ROLE(), RESEAL_MANAGER), "ResealManager should not have RESUME_ROLE on TWG before vote"
            # Rename Nethermind NO
            nethermind_no_data_before = no_registry.getNodeOperator(NETHERMIND_NO_ID, True)

            assert nethermind_no_data_before["rewardAddress"] == NETHERMIND_NO_STAKING_REWARDS_ADDRESS_OLD
            assert nethermind_no_data_before["name"] == NETHERMIND_NO_NAME_OLD

            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)
                # Wait for time window (13:00-19:00 UTC) to satisfy time constraints
                wait_for_time_window(13, 19)

                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                assert count_vote_items_by_events(dg_tx, AGENT) == EXPECTED_DG_EVENTS_FROM_AGENT
                assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

                # === DG EXECUTION EVENTS VALIDATION ===
                # 0. Lido Locator upgrade events
                validate_proxy_upgrade_event(dg_events[0], LIDO_LOCATOR_IMPL, emitted_by=contracts.lido_locator)

                # 1. VEBO upgrade events
                validate_proxy_upgrade_event(dg_events[1], VALIDATORS_EXIT_BUS_ORACLE_IMPL, emitted_by=contracts.validators_exit_bus_oracle)

                # 2. VEBO finalize upgrade events
                validate_contract_version_set_event(dg_events[2], version=2, emitted_by=contracts.validators_exit_bus_oracle)
                assert 'ExitRequestsLimitSet' in dg_events[2], "ExitRequestsLimitSet event not found"
                assert dg_events[2]['ExitRequestsLimitSet'][0]['maxExitRequestsLimit'] == MAX_EXIT_REQUESTS_LIMIT, "Wrong maxExitRequestsLimit"
                assert dg_events[2]['ExitRequestsLimitSet'][0]['exitsPerFrame'] == EXITS_PER_FRAME, "Wrong exitsPerFrame"
                assert dg_events[2]['ExitRequestsLimitSet'][0]['frameDurationInSec'] == FRAME_DURATION_IN_SEC, "Wrong frameDurationInSec"

                # 3. Grant VEBO MANAGE_CONSENSUS_VERSION_ROLE to Agent
                validate_role_grant_event(
                    dg_events[3],
                    role_hash=web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex(),
                    account=contracts.agent.address,
                    emitted_by=contracts.validators_exit_bus_oracle
                )

                # 4. Set VEBO consensus version to 4
                validate_consensus_version_set_event(
                    dg_events[4],
                    new_version=4,
                    prev_version=3,
                    emitted_by=contracts.validators_exit_bus_oracle
                )

                # 5. Revoke VEBO MANAGE_CONSENSUS_VERSION_ROLE from Agent
                validate_role_revoke_event(
                    dg_events[5],
                    role_hash=web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex(),
                    account=contracts.agent.address,
                    emitted_by=contracts.validators_exit_bus_oracle
                )

                # 6. Grant VEBO SUBMIT_REPORT_HASH_ROLE to EasyTrack executor
                validate_role_grant_event(
                    dg_events[6],
                    role_hash=web3.keccak(text="SUBMIT_REPORT_HASH_ROLE").hex(),
                    account=EASYTRACK_EVMSCRIPT_EXECUTOR,
                    emitted_by=contracts.validators_exit_bus_oracle
                )

                # 7. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to CS Ejector
                validate_role_grant_event(
                    dg_events[7],
                    role_hash=web3.keccak(text="ADD_FULL_WITHDRAWAL_REQUEST_ROLE").hex(),
                    account=CS_EJECTOR_ADDRESS,
                    emitted_by=triggerable_withdrawals_gateway
                )

                # 8. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to VEBO
                validate_role_grant_event(
                    dg_events[8],
                    role_hash=web3.keccak(text="ADD_FULL_WITHDRAWAL_REQUEST_ROLE").hex(),
                    account=contracts.validators_exit_bus_oracle.address,
                    emitted_by=triggerable_withdrawals_gateway
                )

                # 9. Connect TWG to Dual Governance tiebreaker
                assert 'SealableWithdrawalBlockerAdded' in dg_events[
                    9], "SealableWithdrawalBlockerAdded event not found"
                assert dg_events[9]['SealableWithdrawalBlockerAdded'][0]['sealable'] == TRIGGERABLE_WITHDRAWALS_GATEWAY, "Wrong sealableWithdrawalBlocker"

                # 10. Update WithdrawalVault implementation
                validate_proxy_upgrade_event(dg_events[10], WITHDRAWAL_VAULT_IMPL, emitted_by=contracts.withdrawal_vault)

                # 11. Call finalizeUpgrade_v2 on WithdrawalVault
                validate_contract_version_set_event(dg_events[11], version=2, emitted_by=contracts.withdrawal_vault)

                # 12. Update AO implementation
                validate_proxy_upgrade_event(dg_events[12], ACCOUNTING_ORACLE_IMPL, emitted_by=contracts.accounting_oracle)

                # 13. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
                validate_role_grant_event(
                    dg_events[13],
                    role_hash=web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex(),
                    account=contracts.agent.address,
                    emitted_by=contracts.accounting_oracle
                )

                # 14. Bump AO consensus version to 4
                validate_consensus_version_set_event(
                    dg_events[14],
                    new_version=4,
                    prev_version=3,
                    emitted_by=contracts.accounting_oracle
                )

                # 15. Revoke AO MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
                validate_role_revoke_event(
                    dg_events[15],
                    role_hash=web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex(),
                    account=contracts.agent.address,
                    emitted_by=contracts.accounting_oracle
                )

                # 16. Call finalizeUpgrade_v3() on AO
                validate_contract_version_set_event(dg_events[16], version=3, emitted_by=contracts.accounting_oracle)

                # 17. Update SR implementation
                validate_proxy_upgrade_event(dg_events[17], STAKING_ROUTER_IMPL, emitted_by=contracts.staking_router)

                # 18. Call finalizeUpgrade_v3() on SR
                validate_contract_version_set_event(dg_events[18], version=3, emitted_by=contracts.staking_router)

                # 19. Grant SR REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitVerifier
                validate_role_grant_event(
                    dg_events[19],
                    role_hash=web3.keccak(text="REPORT_VALIDATOR_EXITING_STATUS_ROLE").hex(),
                    account=VALIDATOR_EXIT_VERIFIER,
                    emitted_by=contracts.staking_router
                )

                # 20. Grant SR REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG
                validate_role_grant_event(
                    dg_events[20],
                    role_hash=web3.keccak(text="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE").hex(),
                    account=triggerable_withdrawals_gateway.address,
                    emitted_by=contracts.staking_router
                )

                # 21. Grant APP_MANAGER_ROLE on Kernel to Voting
                assert 'SetPermission' in dg_events[21]
                assert dg_events[21]['SetPermission'][0]['allowed'] is True

                # 22. Set new implementation for NOR
                assert 'SetApp' in dg_events[22]

                # 23. Finalize upgrade for NOR
                validate_contract_version_set_event(dg_events[23], version=4, emitted_by=contracts.node_operators_registry)
                assert 'ExitDeadlineThresholdChanged' in dg_events[23]
                assert dg_events[23]['ExitDeadlineThresholdChanged'][0]['threshold'] == NOR_EXIT_DEADLINE_IN_SEC

                # 24. Set new implementation for sDVT
                assert 'SetApp' in dg_events[24]

                # 25. Finalize upgrade for sDVT
                validate_contract_version_set_event(dg_events[25], version=4, emitted_by=contracts.simple_dvt)
                assert 'ExitDeadlineThresholdChanged' in dg_events[25]
                assert dg_events[25]['ExitDeadlineThresholdChanged'][0]['threshold'] == NOR_EXIT_DEADLINE_IN_SEC

                # 26. Revoke APP_MANAGER_ROLE on Kernel from Voting
                assert 'SetPermission' in dg_events[26]
                assert dg_events[26]['SetPermission'][0]['allowed'] is False

                # 27. Grant CONFIG_MANAGER_ROLE on OracleDaemonConfig to Agent
                validate_role_grant_event(
                    dg_events[27],
                    role_hash=contracts.oracle_daemon_config.CONFIG_MANAGER_ROLE().hex(),
                    account=contracts.agent.address,
                    emitted_by=contracts.oracle_daemon_config
                )

                # 28. Unset NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP
                assert 'ConfigValueUnset' in dg_events[28]
                assert 'NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP' in \
                       dg_events[28]['ConfigValueUnset'][0]['key']

                # 29. Unset VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS
                assert 'ConfigValueUnset' in dg_events[29]
                assert 'VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS' in dg_events[29]['ConfigValueUnset'][0]['key']

                # 30. Unset VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS
                assert 'ConfigValueUnset' in dg_events[30]
                assert 'VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS' in dg_events[30]['ConfigValueUnset'][0]['key']

                # 31. Set EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS
                assert 'ConfigValueSet' in dg_events[31]
                assert 'EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS' in dg_events[31]['ConfigValueSet'][0]['key']
                assert convert.to_int(dg_events[31]['ConfigValueSet'][0]['value']) == EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS

                # 32. Revoke CONFIG_MANAGER_ROLE from the AGENT
                validate_role_revoke_event(
                    dg_events[32],
                    role_hash=contracts.oracle_daemon_config.CONFIG_MANAGER_ROLE().hex(),
                    account=contracts.agent.address,
                    emitted_by=contracts.oracle_daemon_config
                )

                # 33. CSM implementation upgrade
                validate_proxy_upgrade_event(dg_events[33], CSM_IMPL_V2_ADDRESS, emitted_by=contracts.csm)

                # 34. CSM finalize upgrade validation
                assert 'Initialized' in dg_events[34]
                assert dg_events[34]['Initialized'][0]['version'] == CSM_V2_VERSION

                # 35. CSAccounting implementation upgrade
                validate_proxy_upgrade_event(dg_events[35], CS_ACCOUNTING_IMPL_V2_ADDRESS, emitted_by=contracts.cs_accounting)

                # 36. CSAccounting finalize upgrade with bond curves
                assert 'BondCurveAdded' in dg_events[36]
                assert len(dg_events[36]['BondCurveAdded']) == len(CS_CURVES)
                assert 'Initialized' in dg_events[36]
                assert dg_events[36]['Initialized'][0]['version'] == CS_ACCOUNTING_V2_VERSION

                # 37. CSFeeOracle implementation upgrade
                validate_proxy_upgrade_event(dg_events[37], CS_FEE_ORACLE_IMPL_V2_ADDRESS, emitted_by=contracts.cs_fee_oracle)

                # 38. CSFeeOracle finalize upgrade with consensus version
                validate_consensus_version_set_event(dg_events[38], new_version=3, prev_version=2, emitted_by=contracts.cs_fee_oracle)
                validate_contract_version_set_event(dg_events[38], version=CS_FEE_ORACLE_V2_VERSION, emitted_by=contracts.cs_fee_oracle)

                # 39. CSFeeDistributor implementation upgrade
                validate_proxy_upgrade_event(dg_events[39], CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS, emitted_by=contracts.cs_fee_distributor)

                # 40. CSFeeDistributor finalize upgrade
                assert 'RebateRecipientSet' in dg_events[40]
                assert 'Initialized' in dg_events[40]
                assert dg_events[40]['Initialized'][0]['version'] == CS_FEE_DISTRIBUTOR_V2_VERSION

                # 41. Revoke SET_BOND_CURVE_ROLE from CSM on CSAccounting
                validate_role_revoke_event(
                    dg_events[41],
                    role_hash=contracts.cs_accounting.SET_BOND_CURVE_ROLE().hex(),
                    account=contracts.csm.address,
                    emitted_by=contracts.cs_accounting
                )

                # 42. Revoke RESET_BOND_CURVE_ROLE from CSM on CSAccounting
                validate_role_revoke_event(
                    dg_events[42],
                    role_hash=web3.keccak(text="RESET_BOND_CURVE_ROLE").hex(),
                    account=contracts.csm.address,
                    emitted_by=contracts.cs_accounting
                )

                # 43. Revoke RESET_BOND_CURVE_ROLE from CSM committee on CSAccounting
                validate_role_revoke_event(
                    dg_events[43],
                    role_hash=web3.keccak(text="RESET_BOND_CURVE_ROLE").hex(),
                    account=CSM_COMMITTEE_MS,
                    emitted_by=contracts.cs_accounting
                )

                # 44. Grant CREATE_NODE_OPERATOR_ROLE to permissionless gate on CSM
                validate_role_grant_event(
                    dg_events[44],
                    role_hash=contracts.csm.CREATE_NODE_OPERATOR_ROLE().hex(),
                    account=CS_PERMISSIONLESS_GATE_ADDRESS,
                    emitted_by=contracts.csm
                )

                # 45. Grant CREATE_NODE_OPERATOR_ROLE to vetted gate on CSM
                validate_role_grant_event(
                    dg_events[45],
                    role_hash=contracts.csm.CREATE_NODE_OPERATOR_ROLE().hex(),
                    account=CS_VETTED_GATE_ADDRESS,
                    emitted_by=contracts.csm
                )

                # 46. Grant SET_BOND_CURVE_ROLE to vetted gate on CSAccounting
                validate_role_grant_event(
                    dg_events[46],
                    role_hash=contracts.cs_accounting.SET_BOND_CURVE_ROLE().hex(),
                    account=CS_VETTED_GATE_ADDRESS,
                    emitted_by=contracts.cs_accounting
                )

                # 47. Revoke VERIFIER_ROLE from old verifier on CSM
                validate_role_revoke_event(
                    dg_events[47],
                    role_hash=contracts.csm.VERIFIER_ROLE().hex(),
                    account=CS_VERIFIER_ADDRESS_OLD,
                    emitted_by=contracts.csm
                )

                # 48. Grant VERIFIER_ROLE to new verifier on CSM
                validate_role_grant_event(
                    dg_events[48],
                    role_hash=contracts.csm.VERIFIER_ROLE().hex(),
                    account=CS_VERIFIER_V2_ADDRESS,
                    emitted_by=contracts.csm
                )

                # 49. Revoke PAUSE_ROLE from old GateSeal on CSM
                validate_role_revoke_event(
                    dg_events[49],
                    role_hash=contracts.csm.PAUSE_ROLE().hex(),
                    account=CS_GATE_SEAL_ADDRESS,
                    emitted_by=contracts.csm
                )

                # 50. Revoke PAUSE_ROLE from old GateSeal on CSAccounting
                validate_role_revoke_event(
                    dg_events[50],
                    role_hash=contracts.cs_accounting.PAUSE_ROLE().hex(),
                    account=CS_GATE_SEAL_ADDRESS,
                    emitted_by=contracts.cs_accounting
                )

                # 51. Revoke PAUSE_ROLE from old GateSeal on CSFeeOracle
                validate_role_revoke_event(
                    dg_events[51],
                    role_hash=contracts.cs_fee_oracle.PAUSE_ROLE().hex(),
                    account=CS_GATE_SEAL_ADDRESS,
                    emitted_by=contracts.cs_fee_oracle
                )

                # 52. Grant PAUSE_ROLE to new GateSeal on CSM
                validate_role_grant_event(
                    dg_events[52],
                    role_hash=contracts.csm.PAUSE_ROLE().hex(),
                    account=CS_GATE_SEAL_V2_ADDRESS,
                    emitted_by=contracts.csm
                )

                # 53. Grant PAUSE_ROLE to new GateSeal on CSAccounting
                validate_role_grant_event(
                    dg_events[53],
                    role_hash=contracts.cs_accounting.PAUSE_ROLE().hex(),
                    account=CS_GATE_SEAL_V2_ADDRESS,
                    emitted_by=contracts.cs_accounting
                )

                # 54. Grant PAUSE_ROLE to new GateSeal on CSFeeOracle
                validate_role_grant_event(
                    dg_events[54],
                    role_hash=contracts.cs_fee_oracle.PAUSE_ROLE().hex(),
                    account=CS_GATE_SEAL_V2_ADDRESS,
                    emitted_by=contracts.cs_fee_oracle
                )

                # 55. Grant MANAGE_BOND_CURVES_ROLE to agent on CSAccounting
                validate_role_grant_event(
                    dg_events[55],
                    role_hash=contracts.cs_accounting.MANAGE_BOND_CURVES_ROLE().hex(),
                    account=contracts.agent.address,
                    emitted_by=contracts.cs_accounting
                )

                # 56. Add ICS bond curve
                ics_curve_id = len(CS_CURVES)
                validate_bond_curve_added_event(dg_events[56], curve_id=ics_curve_id, emitted_by=contracts.cs_accounting)

                # 57. Revoke MANAGE_BOND_CURVES_ROLE from agent on CSAccounting
                validate_role_revoke_event(
                    dg_events[57],
                    role_hash=contracts.cs_accounting.MANAGE_BOND_CURVES_ROLE().hex(),
                    account=contracts.agent.address,
                    emitted_by=contracts.cs_accounting
                )

                # 58. Increase CSM share in Staking Router
                validate_staking_module_update_event(
                    dg_events[58],
                    module_id=CS_MODULE_ID,
                    share_limit=CS_MODULE_NEW_TARGET_SHARE_BP,
                    priority_share_threshold=CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
                    module_fee_points_bp=CS_MODULE_MODULE_FEE_BP,
                    treasury_fee_points_bp=CS_MODULE_TREASURY_FEE_BP,
                    max_deposits_per_block=CS_MODULE_MAX_DEPOSITS_PER_BLOCK,
                    min_deposit_block_distance=CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
                    emitted_by=contracts.staking_router
                )

                # 59-65. Gate Seals and ResealManager role updates
                # 59. Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
                validate_role_revoke_event(
                    dg_events[59],
                    role_hash=contracts.withdrawal_queue.PAUSE_ROLE().hex(),
                    account=OLD_GATE_SEAL_ADDRESS,
                    emitted_by=contracts.withdrawal_queue
                )

                # 60. Revoke PAUSE_ROLE on ValidatorsExitBusOracle from the old GateSeal
                validate_role_revoke_event(
                    dg_events[60],
                    role_hash=contracts.validators_exit_bus_oracle.PAUSE_ROLE().hex(),
                    account=OLD_GATE_SEAL_ADDRESS,
                    emitted_by=contracts.validators_exit_bus_oracle
                )

                # 61. Grant PAUSE_ROLE on WithdrawalQueue to the new WithdrawalQueue GateSeal
                validate_role_grant_event(
                    dg_events[61],
                    role_hash=contracts.withdrawal_queue.PAUSE_ROLE().hex(),
                    account=NEW_WQ_GATE_SEAL,
                    emitted_by=contracts.withdrawal_queue
                )

                # 62. Grant PAUSE_ROLE on ValidatorsExitBusOracle to the new Triggerable Withdrawals GateSeal
                validate_role_grant_event(
                    dg_events[62],
                    role_hash=contracts.validators_exit_bus_oracle.PAUSE_ROLE().hex(),
                    account=NEW_TW_GATE_SEAL,
                    emitted_by=contracts.validators_exit_bus_oracle
                )

                # 63. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to the new Triggerable Withdrawals GateSeal
                validate_role_grant_event(
                    dg_events[63],
                    role_hash=triggerable_withdrawals_gateway.PAUSE_ROLE().hex(),
                    account=NEW_TW_GATE_SEAL,
                    emitted_by=triggerable_withdrawals_gateway
                )

                # 64. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to ResealManager
                validate_role_grant_event(
                    dg_events[64],
                    role_hash=triggerable_withdrawals_gateway.PAUSE_ROLE().hex(),
                    account=RESEAL_MANAGER,
                    emitted_by=triggerable_withdrawals_gateway
                )

                # 65. Grant RESUME_ROLE on TriggerableWithdrawalsGateway to ResealManager
                validate_role_grant_event(
                    dg_events[65],
                    role_hash=triggerable_withdrawals_gateway.RESUME_ROLE().hex(),
                    account=RESEAL_MANAGER,
                    emitted_by=triggerable_withdrawals_gateway
                )

                # Validate Nethermind NO name change
                validate_node_operator_name_set_event(
                    dg_events[66],
                    NodeOperatorNameSetItem(nodeOperatorId=NETHERMIND_NO_ID, name=NETHERMIND_NO_NAME_NEW),
                    emitted_by=no_registry,
                    is_dg_event=True,
                )

                # Validate Nethermind NO rewards address change
                validate_node_operator_reward_address_set_event(
                    dg_events[67],
                    NodeOperatorRewardAddressSetItem(
                        nodeOperatorId=NETHERMIND_NO_ID, reward_address=NETHERMIND_NO_STAKING_REWARDS_ADDRESS_NEW
                    ),
                    emitted_by=no_registry,
                    is_dg_event=True,
                )
                # Guardian remove event
                validate_remove_guardian_event(
                    dg_events[68],
                    OLD_KILN_ADDRESS,
                    emitted_by=contracts.deposit_security_module.address,
                )
                # Guardian add event
                validate_add_guardian_event(
                    dg_events[69],
                    NEW_KILN_ADDRESS,
                    emitted_by=contracts.deposit_security_module.address,
                )

                # 70. Time constraints event validation
                assert 'TimeWithinDayTimeChecked' in dg_events[70], "TimeWithinDayTimeChecked event not found"
                assert dg_events[70]['TimeWithinDayTimeChecked'][0]['startDayTime'] == 3600 * 13, "Wrong startDayTime for time constraints (expected 13:00 UTC)"
                assert dg_events[70]['TimeWithinDayTimeChecked'][0]['endDayTime'] == 3600 * 19, "Wrong endDayTime for time constraints (expected 19:00 UTC)"
                assert convert.to_address(dg_events[70]['TimeWithinDayTimeChecked'][0]['_emitted_by']) == convert.to_address(DUAL_GOVERNANCE_TIME_CONSTRAINTS), "Wrong event emitter for time constraints"

        # Step 1: Validate Lido Locator implementation was updated
        assert get_ossifiable_proxy_impl(
            contracts.lido_locator) == LIDO_LOCATOR_IMPL, "Locator implementation should be updated to the new value"

        # Step 2-3: Validate VEBO implementation was updated and configured
        assert get_ossifiable_proxy_impl(
            contracts.validators_exit_bus_oracle) == VALIDATORS_EXIT_BUS_ORACLE_IMPL, "VEBO implementation should be updated"
        assert contracts.validators_exit_bus_oracle.getMaxValidatorsPerReport() == 600, "VEBO max validators per report should be set to 600"

        # Validate exit request limit parameters from finalizeUpgrade_v2 call
        exit_request_limits = contracts.validators_exit_bus_oracle.getExitRequestLimitFullInfo()
        assert exit_request_limits[0] == MAX_EXIT_REQUESTS_LIMIT, "maxExitRequestsLimit should be 11200"
        assert exit_request_limits[1] == EXITS_PER_FRAME, "exitsPerFrame should be 1"
        assert exit_request_limits[2] == FRAME_DURATION_IN_SEC, "frameDurationInSec should be 48 in seconds"

        # Steps 4-6: Validate VEBO consensus version management
        assert not contracts.validators_exit_bus_oracle.hasRole(
            contracts.validators_exit_bus_oracle.MANAGE_CONSENSUS_VERSION_ROLE(),
            contracts.agent), "Agent should not have MANAGE_CONSENSUS_VERSION_ROLE on VEBO"
        assert contracts.validators_exit_bus_oracle.getConsensusVersion() == VEBO_CONSENSUS_VERSION, f"VEBO consensus version should be set to {VEBO_CONSENSUS_VERSION}"

        # Step 7: Validate EasyTrack VEB SUBMIT_REPORT_HASH_ROLE
        assert contracts.validators_exit_bus_oracle.hasRole(submit_report_hash_role, EASYTRACK_EVMSCRIPT_EXECUTOR), "EasyTrack executor should have SUBMIT_REPORT_HASH_ROLE on VEBO"

        # Steps 8-9: Validate TWG roles
        assert triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, cs_ejector), "CS Ejector should have ADD_FULL_WITHDRAWAL_REQUEST_ROLE on TWG"
        assert triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle), "VEBO should have ADD_FULL_WITHDRAWAL_REQUEST_ROLE on TWG"

        # Step 10: Validate DualGovernance tiebreaker connection
        final_tiebreaker_details = contracts.dual_governance.getTiebreakerDetails()
        final_tiebreakers = final_tiebreaker_details[3]  # sealableWithdrawalBlockers
        assert TRIGGERABLE_WITHDRAWALS_GATEWAY in final_tiebreakers, "TWG should be in tiebreaker list after upgrade"

        # Steps 11-12: Validate Withdrawal Vault upgrade
        assert get_wv_contract_proxy_impl(contracts.withdrawal_vault) == WITHDRAWAL_VAULT_IMPL, "Withdrawal Vault implementation should be updated"
        assert contracts.withdrawal_vault.getContractVersion() == 2, "Withdrawal Vault version should be 2 after finalizeUpgrade_v2"

        # Steps 13-16: Validate Accounting Oracle upgrade
        assert get_ossifiable_proxy_impl(
            contracts.accounting_oracle) == ACCOUNTING_ORACLE_IMPL, "Accounting Oracle implementation should be updated"
        assert not contracts.accounting_oracle.hasRole(contracts.accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE(), contracts.agent), "Agent should not have MANAGE_CONSENSUS_VERSION_ROLE on AO"
        assert contracts.accounting_oracle.getConsensusVersion() == AO_CONSENSUS_VERSION, f"AO consensus version should be set to {AO_CONSENSUS_VERSION}"

        # Step 17: Validate AO finalizeUpgrade_v3
        assert contracts.accounting_oracle.getContractVersion() == 3, "AO contract version should be 3 after finalizeUpgrade_v3"

        # Steps 18-21: Validate Staking Router upgrade
        assert get_ossifiable_proxy_impl(contracts.staking_router) == STAKING_ROUTER_IMPL, "Staking Router implementation should be updated"
        assert contracts.staking_router.getContractVersion() == 3, "Staking Router version should be 3 after finalizeUpgrade_v3"
        assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE(), VALIDATOR_EXIT_VERIFIER), "ValidatorExitVerifier should have REPORT_VALIDATOR_EXITING_STATUS_ROLE on SR"
        assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE(), triggerable_withdrawals_gateway), "TWG should have REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE on SR"

        # Steps 22-27: Validate NOR and sDVT updates
        assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel,app_manager_role), "Agent should not have APP_MANAGER_ROLE after vote"
        assert contracts.node_operators_registry.getContractVersion() == 4, "Node Operators Registry version should be updated to 4"
        assert contracts.simple_dvt.getContractVersion() == 4, "Simple DVT version should be updated to 4"
        assert contracts.node_operators_registry.exitDeadlineThreshold(0) == NOR_EXIT_DEADLINE_IN_SEC, "NOR exit deadline threshold should be set correctly after finalizeUpgrade_v4"
        assert contracts.simple_dvt.exitDeadlineThreshold(0) == NOR_EXIT_DEADLINE_IN_SEC, "sDVT exit deadline threshold should be set correctly after finalizeUpgrade_v4"

        # Steps 28-33: Validate Oracle Daemon Config changes
        assert not contracts.oracle_daemon_config.hasRole(config_manager_role, contracts.agent), "Agent should not have CONFIG_MANAGER_ROLE on Oracle Daemon Config"
        for var_name in ['NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP', 'VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS',
                         'VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS']:
            try:
                contracts.oracle_daemon_config.get(var_name)
            except VirtualMachineError:
                pass  # Expected to fail - variable should be removed
            else:
                raise AssertionError(f"Variable {var_name} should have been removed")
        assert convert.to_uint(contracts.oracle_daemon_config.get(
            'EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS')) == EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS, f"EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS should be set to {EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS}"

        # Step 34: Validate CSM implementation upgrade
        check_proxy_implementation(contracts.csm.address, CSM_IMPL_V2_ADDRESS)

        # Step 35: Validate CSM finalizeUpgradeV2 was called
        assert contracts.csm.getInitializedVersion() == CSM_V2_VERSION, f"CSM version should be {CSM_V2_VERSION} after vote"

        # Step 36: Validate CSAccounting implementation upgrade
        check_proxy_implementation(contracts.cs_accounting.address, CS_ACCOUNTING_IMPL_V2_ADDRESS)

        # Step 37: Validate CSAccounting finalizeUpgradeV2 was called with bond curves
        assert contracts.cs_accounting.getInitializedVersion() == CS_ACCOUNTING_V2_VERSION, f"CSAccounting version should be {CS_ACCOUNTING_V2_VERSION} after vote"
        # FIXME: check bond curves

        # Step 38: Validate CSFeeOracle implementation upgrade
        check_proxy_implementation(contracts.cs_fee_oracle.address, CS_FEE_ORACLE_IMPL_V2_ADDRESS)

        # Step 39: Validate CSFeeOracle finalizeUpgradeV2 was called with consensus version 3
        assert contracts.cs_fee_oracle.getContractVersion() == CS_FEE_ORACLE_V2_VERSION, f"CSFeeOracle version should be {CS_FEE_ORACLE_V2_VERSION} after vote"
        assert contracts.cs_fee_oracle.getConsensusVersion() == CSM_CONSENSUS_VERSION, "CSFeeOracle consensus version should be 3 after vote"

        # Step 40: Validate CSFeeDistributor implementation upgrade
        check_proxy_implementation(contracts.cs_fee_distributor.address, CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS)

        # Step 41: Validate CSFeeDistributor finalizeUpgradeV2 was called
        assert contracts.cs_fee_distributor.getInitializedVersion() == CS_FEE_DISTRIBUTOR_V2_VERSION, f"CSFeeDistributor version should be {CS_FEE_DISTRIBUTOR_V2_VERSION} after vote"
        assert contracts.cs_fee_distributor.rebateRecipient() == contracts.agent.address, "Rebate recipient should be the agent after vote"

        # Step 42: Validate SET_BOND_CURVE_ROLE was revoked from CSM on CSAccounting
        assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(),
                                                   contracts.csm.address), "CSM should not have SET_BOND_CURVE_ROLE on CSAccounting after vote"

        # Step 43: Validate RESET_BOND_CURVE_ROLE was revoked from CSM on CSAccounting
        assert not contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"),
                                                   contracts.csm.address), "CSM should not have RESET_BOND_CURVE_ROLE on CSAccounting after vote"

        # Step 44: Validate RESET_BOND_CURVE_ROLE was revoked from CSM committee on CSAccounting
        assert not contracts.cs_accounting.hasRole(web3.keccak(text="RESET_BOND_CURVE_ROLE"),
                                                   CSM_COMMITTEE_MS), "CSM committee should not have RESET_BOND_CURVE_ROLE on CSAccounting after vote"

        # Step 45: Validate CREATE_NODE_OPERATOR_ROLE was granted to permissionless gate on CSM
        assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(),
                                     cs_permissionless_gate.address), "Permissionless gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"

        # Step 46: Validate CREATE_NODE_OPERATOR_ROLE was granted to vetted gate on CSM
        assert contracts.csm.hasRole(contracts.csm.CREATE_NODE_OPERATOR_ROLE(),
                                     cs_vetted_gate.address), "Vetted gate should have CREATE_NODE_OPERATOR_ROLE on CSM after vote"

        # Step 47: Validate SET_BOND_CURVE_ROLE was granted to vetted gate on CSAccounting
        assert contracts.cs_accounting.hasRole(contracts.cs_accounting.SET_BOND_CURVE_ROLE(),
                                               cs_vetted_gate.address), "Vetted gate should have SET_BOND_CURVE_ROLE on CSAccounting after vote"

        # Step 48: Validate VERIFIER_ROLE was revoked from old verifier on CSM
        assert not contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(),
                                         CS_VERIFIER_ADDRESS_OLD), "Old verifier should not have VERIFIER_ROLE on CSM after vote"

        # Step 49: Validate VERIFIER_ROLE was granted to new verifier on CSM
        assert contracts.csm.hasRole(contracts.csm.VERIFIER_ROLE(),
                                     cs_verifier_v2.address), "New verifier should have VERIFIER_ROLE on CSM after vote"

        # Step 50: Validate PAUSE_ROLE was revoked from old GateSeal on CSM
        assert not contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(),
                                         CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSM after vote"

        # Step 51: Validate PAUSE_ROLE was revoked from old GateSeal on CSAccounting
        assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(),
                                                   CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSAccounting after vote"

        # Step 52: Validate PAUSE_ROLE was revoked from old GateSeal on CSFeeOracle
        assert not contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(),
                                                   CS_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on CSFeeOracle after vote"

        # Step 53: Validate PAUSE_ROLE was granted to new GateSeal on CSM
        assert contracts.csm.hasRole(contracts.csm.PAUSE_ROLE(),
                                     CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSM after vote"

        # Step 54: Validate PAUSE_ROLE was granted to new GateSeal on CSAccounting
        assert contracts.cs_accounting.hasRole(contracts.cs_accounting.PAUSE_ROLE(),
                                               CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSAccounting after vote"

        # Step 55: Validate PAUSE_ROLE was granted to new GateSeal on CSFeeOracle
        assert contracts.cs_fee_oracle.hasRole(contracts.cs_fee_oracle.PAUSE_ROLE(),
                                               CS_GATE_SEAL_V2_ADDRESS), "New GateSeal should have PAUSE_ROLE on CSFeeOracle after vote"

        # Step 50-52: Check add ICS Bond Curve to CSAccounting
        assert not contracts.cs_accounting.hasRole(contracts.cs_accounting.MANAGE_BOND_CURVES_ROLE(),
                                                   contracts.agent), "Agent should not have MANAGE_BOND_CURVES_ROLE on CSAccounting after vote"
        assert contracts.cs_accounting.getCurvesCount() == len(
            CS_CURVES) + 1, "CSAccounting should have legacy bond curves and ICS Bond Curve after vote"
        # FIXME: Check curves?

        # Step 53: Increase CSM share in Staking Router
        csm_module_after = contracts.staking_router.getStakingModule(CS_MODULE_ID)
        csm_share_after = csm_module_after['stakeShareLimit']
        assert csm_share_after == CS_MODULE_NEW_TARGET_SHARE_BP, f"CSM share should be {CS_MODULE_NEW_TARGET_SHARE_BP} after vote, but got {csm_share_after}"

        csm_priority_exit_threshold_after = csm_module_after['priorityExitShareThreshold']
        assert csm_priority_exit_threshold_after == CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP, f"CSM priority exit threshold should be {CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP} after vote, but got {csm_priority_exit_threshold_after}"

        # Steps 58-62: Validate Gate Seals updates
        assert not contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(),
                                                      OLD_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on WithdrawalQueue after vote"
        assert not contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.PAUSE_ROLE(),
                                                                OLD_GATE_SEAL_ADDRESS), "Old GateSeal should not have PAUSE_ROLE on VEBO after vote"
        assert contracts.withdrawal_queue.hasRole(contracts.withdrawal_queue.PAUSE_ROLE(),
                                                  NEW_WQ_GATE_SEAL), "New WQ GateSeal should have PAUSE_ROLE on WithdrawalQueue after vote"
        assert contracts.validators_exit_bus_oracle.hasRole(contracts.validators_exit_bus_oracle.PAUSE_ROLE(),
                                                            NEW_TW_GATE_SEAL), "New TW GateSeal should have PAUSE_ROLE on VEBO after vote"
        assert triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.PAUSE_ROLE(),
                                                       NEW_TW_GATE_SEAL), "New TW GateSeal should have PAUSE_ROLE on TWG after vote"

        # Steps 63-64: Validate ResealManager roles
        assert triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.PAUSE_ROLE(),
                                                       RESEAL_MANAGER), "ResealManager should have PAUSE_ROLE on TWG after vote"
        assert triggerable_withdrawals_gateway.hasRole(triggerable_withdrawals_gateway.RESUME_ROLE(),
                                                       RESEAL_MANAGER), "ResealManager should have RESUME_ROLE on TWG after vote"

        # 67-68. Rename Node Operator ID 25 from Nethermind to Twinstake
        no = contracts.node_operators_registry.getNodeOperator(NETHERMIND_NO_ID, True)

        assert no[1] == NETHERMIND_NO_NAME_NEW
        assert no[2] == NETHERMIND_NEW_REWARD_ADDRESS

        assert contracts.deposit_security_module.isGuardian(OLD_KILN_ADDRESS) is False, "Old Kiln address should be removed from guardians"
        assert contracts.deposit_security_module.isGuardian(NEW_KILN_ADDRESS) is True, "New Kiln address should be added to guardians"
