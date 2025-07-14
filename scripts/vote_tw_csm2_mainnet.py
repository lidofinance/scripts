"""
Vote 2025_<MM>_<DD> [MAINNET]

--- Locator
1. Update locator implementation
--- VEB
2. Update VEBO implementation
3. Call finalizeUpgrade_v2(maxValidatorsPerReport, maxExitRequestsLimit, exitsPerFrame, frameDurationInSec) on VEBO
4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
5. Bump VEBO consensus version to `4`
6. Revoke VEBO role MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
7. Grant SUBMIT_REPORT_HASH_ROLE on Validator Exit Bus Oracle to the EasyTrack EVM Script Executor
--- Triggerable Withdrawals Gateway (TWG)
8. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the CS Ejector
9. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEB
10. Connect TRIGGERABLE_WITHDRAWALS_GATEWAY to Dual Governance tiebreaker
--- WV
11. Update WithdrawalVault implementation
12. Call finalizeUpgrade_v2() on WithdrawalVault
--- AO
13. Update Accounting Oracle implementation
14. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
15. Bump AO consensus version to `4`
16. Revoke AO MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
17. Call finalizeUpgrade_v3() on AO
--- SR
18. Update SR implementation
19. Call finalizeUpgrade_v3() on SR
20. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitVerifier
21. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG
--- Curated Staking Module
22. Grant APP_MANAGER_ROLE role to the AGENT on Kernel
23. Update `NodeOperatorsRegistry` implementation
24. Call finalizeUpgrade_v4 on Curated Staking Module
--- sDVT
25. Update `SimpleDVT` implementation
26. Call finalizeUpgrade_v4 on sDVT
27. Revoke APP_MANAGER_ROLE role from the AGENT on Kernel
--- Oracle configs ---
28. Grant CONFIG_MANAGER_ROLE role to the AGENT
29. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig
30. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
31. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
32. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig
33. Revoke CONFIG_MANAGER_ROLE role from the AGENT
--- CSM ---
34. Upgrade CSM implementation on proxy
35. Call `finalizeUpgradeV2()` on CSM contract
36. Upgrade CSAccounting implementation on proxy
37. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract
38. Upgrade CSFeeOracle implementation on proxy
39. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract
40. Upgrade CSFeeDistributor implementation on proxy
41. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract
42. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract
43. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract
44. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee
45. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate
46. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate
47. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate
48. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract
49. Grant role VERIFIER_ROLE to the new instance of the Verifier contract
50. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance
51. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance
52. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance
53. Grant CSM role PAUSE_ROLE for the new GateSeal instance
54. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance
55. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance
56. Grant MANAGE_BOND_CURVES_ROLE to the AGENT
57. Add Identified Community Stakers Gate Bond Curve
58. Revoke MANAGE_BOND_CURVES_ROLE from the AGENT
59. Increase CSM share in Staking Router from 15% to 16%
--- Gate Seals ---
60. Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
61. Revoke PAUSE_ROLE on ValidatorsExitBusOracle from the old GateSeal
62. Grant PAUSE_ROLE on WithdrawalQueue to the new WithdrawalQueue GateSeal
63. Grant PAUSE_ROLE on ValidatorsExitBusOracle to the new Triggerable Withdrawals GateSeal
64. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to the new Triggerable Withdrawals GateSeal
--- ResealManager ---
65. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to ResealManager
66. Grant RESUME_ROLE on TriggerableWithdrawalsGateway to ResealManager
--- EasyTrack ---
67. Add CSSetVettedGateTree factory to EasyTrack with permissions
68. Add `SubmitValidatorsExitRequestHashes` (SDVT) EVM script factory to Easy Track
69. Add `SubmitValidatorsExitRequestHashes` (Curated Module) EVM script factory to Easy Track

# TODO (after vote) Vote #{vote number} passed & executed on ${date+time}, block ${blockNumber}.
"""

import time

from typing import TYPE_CHECKING, Any, Dict
from typing import Tuple, Optional, Sequence
from brownie import interface, web3, convert, ZERO_ADDRESS
from brownie.convert.main import to_uint  # type: ignore
from utils.agent import agent_forward
from utils.config import (
    CSM_COMMITTEE_MS,
    CS_MODULE_ID,
    CS_MODULE_MODULE_FEE_BP,
    CS_MODULE_TREASURY_FEE_BP,
    CS_MODULE_MAX_DEPOSITS_PER_BLOCK,
    CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
    CS_MODULE_TARGET_SHARE_BP,
    CS_GATE_SEAL_ADDRESS,
    NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
    SIMPLE_DVT_ARAGON_APP_ID,
    ARAGON_KERNEL,
    AGENT,
    contracts,
)
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
)
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.dual_governance import submit_proposals
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.config import get_deployer_account, get_priority_fee, get_is_live

# ============================== Addresses ===================================
# New core contracts implementations
LIDO_LOCATOR_IMPL = "0x2C298963FB763f74765829722a1ebe0784f4F5Cf"
ACCOUNTING_ORACLE_IMPL = "0xE9906E543274cebcd335d2C560094089e9547e8d"
VALIDATORS_EXIT_BUS_ORACLE_IMPL = "0x905A211eD6830Cfc95643f0bE2ff64E7f3bf9b94"
WITHDRAWAL_VAULT_IMPL = "0x7D2BAa6094E1C4B60Da4cbAF4A77C3f4694fD53D"
STAKING_ROUTER_IMPL = "0x226f9265CBC37231882b7409658C18bB7738173A"
NODE_OPERATORS_REGISTRY_IMPL = "0x6828b023e737f96B168aCd0b5c6351971a4F81aE"

TRIGGERABLE_WITHDRAWALS_GATEWAY = "0xDC00116a0D3E064427dA2600449cfD2566B3037B"
VALIDATOR_EXIT_VERIFIER = "0xbDb567672c867DB533119C2dcD4FB9d8b44EC82f"

# Oracle consensus versions
AO_CONSENSUS_VERSION = 4
VEBO_CONSENSUS_VERSION = 4
CSM_CONSENSUS_VERSION = 3

# Fixed constants from Holesky version
EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS = 14 * 7200  # 14 days in slots (assuming 12 seconds per slot)
NOR_EXIT_DEADLINE_IN_SEC = 172800  # 172800

# VEB parameters from Holesky
MAX_VALIDATORS_PER_REPORT = 600
MAX_EXIT_REQUESTS_LIMIT = 11200
EXITS_PER_FRAME = 1
FRAME_DURATION_IN_SEC = 48

# CSM
CS_MODULE_NEW_TARGET_SHARE_BP = 3500  # 3.5%
CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 3750  # 3.75%

CS_ACCOUNTING_IMPL_V2_ADDRESS = "0x6f09d2426c7405C5546413e6059F884D2D03f449"
CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS = "0x5DCF7cF7c6645E9E822a379dF046a8b0390251A1"
CS_FEE_ORACLE_IMPL_V2_ADDRESS = "0xe0B234f99E413E27D9Bc31aBba9A49A3e570Da97"
CSM_IMPL_V2_ADDRESS = "0x1eB6d4da13ca9566c17F526aE0715325d7a07665"

CS_GATE_SEAL_V2_ADDRESS = "0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3"
CS_EJECTOR_ADDRESS = "0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C"
CS_PERMISSIONLESS_GATE_ADDRESS = "0xcF33a38111d0B1246A3F38a838fb41D626B454f0"
CS_VETTED_GATE_ADDRESS = "0xB314D4A76C457c93150d308787939063F4Cc67E0"
CS_VERIFIER_V2_ADDRESS = "0xdC5FE1782B6943f318E05230d688713a560063DC"

CS_CURVES = [
    ([1, 2.4 * 10**18], [2, 1.3 * 10**18]),  # Default Curve
    ([1, 1.5 * 10**18], [2, 1.3 * 10**18]),  # Legacy EA Curve
]
CS_ICS_GATE_BOND_CURVE = ([1, 1.5 * 10**18], [2, 1.3 * 10**18])  # Identified Community Stakers Gate Bond Curve

# Add missing constants
OLD_GATE_SEAL_ADDRESS = "0xf9C9fDB4A5D2AA1D836D5370AB9b28BC1847e178"
NEW_WQ_GATE_SEAL = "0x8A854C4E750CDf24f138f34A9061b2f556066912"
NEW_TW_GATE_SEAL = "0xA6BC802fAa064414AA62117B4a53D27fFfF741F1"
RESEAL_MANAGER = "0x7914b5a1539b97Bd0bbd155757F25FD79A522d24"

# Add EasyTrack constants
EASYTRACK_EVMSCRIPT_EXECUTOR = "0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E"
EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0xAa3D6A8B52447F272c1E8FAaA06EA06658bd95E2"
EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x397206ecdbdcb1A55A75e60Fc4D054feC72E5f63"
EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY = "0xa890fc73e1b771Ee6073e2402E631c312FF92Cd9"  # TODO: replace with the real one

# ============================= Description ==================================
IPFS_DESCRIPTION = "Triggerable withdrawals and CSM v2 upgrade voting"


def encode_staking_router_proxy_update(implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(contracts.staking_router)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_wv_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.WithdrawalContractProxy(proxy)

    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b"")


def encode_oracle_upgrade_consensus(proxy: Any, consensus_version: int) -> Tuple[str, str]:
    oracle = interface.BaseOracle(proxy)
    return oracle.address, oracle.setConsensusVersion.encode_input(consensus_version)


def encode_staking_router_update_csm_module_share() -> Tuple[str, str]:
    """Encode call to update CSM share limit"""
    return (
        contracts.staking_router.address,
        contracts.staking_router.updateStakingModule.encode_input(
            CS_MODULE_ID,
            CS_MODULE_NEW_TARGET_SHARE_BP,
            CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP,
            CS_MODULE_MODULE_FEE_BP,
            CS_MODULE_TREASURY_FEE_BP,
            CS_MODULE_MAX_DEPOSITS_PER_BLOCK,
            CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
        ),
    )


def to_percent(bp: int) -> float:
    """
    Convert basis points to percentage.
    """
    return bp / 10000 * 100


def get_vote_items():
    dg_items = [
        # --- locator
        # "1. Update locator implementation",
        agent_forward([encode_proxy_upgrade_to(contracts.lido_locator, LIDO_LOCATOR_IMPL)]),
        # --- VEB
        # "2. Update VEBO implementation",
        agent_forward([encode_proxy_upgrade_to(contracts.validators_exit_bus_oracle, VALIDATORS_EXIT_BUS_ORACLE_IMPL)]),
        # "3. Call finalizeUpgrade_v2 on VEBO",
        agent_forward(
            [
                (
                    contracts.validators_exit_bus_oracle.address,
                    contracts.validators_exit_bus_oracle.finalizeUpgrade_v2.encode_input(
                        MAX_VALIDATORS_PER_REPORT, MAX_EXIT_REQUESTS_LIMIT, EXITS_PER_FRAME, FRAME_DURATION_IN_SEC
                    ),
                )
            ]
        ),
        # "4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ]
        ),
        # "5. Bump VEBO consensus version to `4`",
        agent_forward([encode_oracle_upgrade_consensus(contracts.validators_exit_bus_oracle, VEBO_CONSENSUS_VERSION)]),
        # "6. Revoke VEBO role MANAGE_CONSENSUS_VERSION_ROLE from the AGENT",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
                )
            ]
        ),
        # "7. Grant SUBMIT_REPORT_HASH_ROLE on Validator Exit Bus Oracle to the EasyTrack EVM Script Executor",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="SUBMIT_REPORT_HASH_ROLE",
                    grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
                )
            ]
        ),
        # --- Triggerable Withdrawals Gateway (TWG)
        # "8. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the CS Ejector",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=CS_EJECTOR_ADDRESS,
                )
            ]
        ),
        # "9. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEB",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.validators_exit_bus_oracle,
                )
            ]
        ),
        # "10. Connect TRIGGERABLE_WITHDRAWALS_GATEWAY to Dual Governance tiebreaker",
        (
            contracts.dual_governance.address,
            contracts.dual_governance.addTiebreakerSealableWithdrawalBlocker.encode_input(
                TRIGGERABLE_WITHDRAWALS_GATEWAY
            ),
        ),
        # --- WV
        # "11. Update WithdrawalVault implementation",
        agent_forward([encode_wv_proxy_upgrade_to(contracts.withdrawal_vault, WITHDRAWAL_VAULT_IMPL)]),
        # "12. Call finalizeUpgrade_v2 on WithdrawalVault",
        agent_forward(
            [
                (
                    contracts.withdrawal_vault.address,
                    contracts.withdrawal_vault.finalizeUpgrade_v2.encode_input(),
                )
            ]
        ),
        # --- AO
        # "13. Update Accounting Oracle implementation",
        agent_forward([encode_proxy_upgrade_to(contracts.accounting_oracle, ACCOUNTING_ORACLE_IMPL)]),
        # "14. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ]
        ),
        # "15. Bump AO consensus version to `4`",
        agent_forward([encode_oracle_upgrade_consensus(contracts.accounting_oracle, AO_CONSENSUS_VERSION)]),
        # "16. Revoke AO MANAGE_CONSENSUS_VERSION_ROLE from the AGENT",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
                )
            ]
        ),
        # "17. Call finalizeUpgrade_v3() on AO",
        agent_forward(
            [
                (
                    contracts.accounting_oracle.address,
                    contracts.accounting_oracle.finalizeUpgrade_v3.encode_input(),
                )
            ]
        ),
        # --- SR
        # "18. Update SR implementation",
        agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)]),
        # "19. Call finalizeUpgrade_v3() on SR",
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.finalizeUpgrade_v3.encode_input(),
                )
            ]
        ),
        # "20. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitDelayVerifier",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                    grant_to=VALIDATOR_EXIT_VERIFIER,
                )
            ]
        ),
        # "21. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE",
                    grant_to=interface.TriggerableWithdrawalsGateway(
                        TRIGGERABLE_WITHDRAWALS_GATEWAY
                    ),  # FIXME: simply use the address
                )
            ]
        ),
        # --- Curated Staking Module and sDVT
        # "22. Grant APP_MANAGER_ROLE role to the AGENT",
        agent_forward(
            [
                (
                    contracts.acl.address,
                    contracts.acl.grantPermission.encode_input(
                        AGENT,
                        ARAGON_KERNEL,
                        convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE")),  # FIXME: no need for to_uint I guess
                    ),
                )
            ]
        ),
        # "23. Update `NodeOperatorsRegistry` implementation",
        agent_forward(
            [
                (
                    contracts.kernel.address,
                    contracts.kernel.setApp.encode_input(
                        contracts.kernel.APP_BASES_NAMESPACE(),
                        NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
                        NODE_OPERATORS_REGISTRY_IMPL,
                    ),
                )
            ]
        ),
        # "24. Call finalizeUpgrade_v4 on Curated Staking Module",
        agent_forward(
            [
                (
                    interface.NodeOperatorsRegistry(contracts.node_operators_registry).address,
                    interface.NodeOperatorsRegistry(contracts.node_operators_registry).finalizeUpgrade_v4.encode_input(
                        NOR_EXIT_DEADLINE_IN_SEC
                    ),
                )
            ]
        ),
        # "25. Update `SDVT` implementation",
        agent_forward(
            [
                (
                    contracts.kernel.address,
                    contracts.kernel.setApp.encode_input(
                        contracts.kernel.APP_BASES_NAMESPACE(),
                        SIMPLE_DVT_ARAGON_APP_ID,
                        NODE_OPERATORS_REGISTRY_IMPL,
                    ),
                )
            ]
        ),
        # "26. Call finalizeUpgrade_v4 on SDVT",
        agent_forward(
            [
                (
                    interface.NodeOperatorsRegistry(contracts.simple_dvt).address,
                    interface.NodeOperatorsRegistry(contracts.simple_dvt).finalizeUpgrade_v4.encode_input(
                        NOR_EXIT_DEADLINE_IN_SEC
                    ),
                )
            ]
        ),
        # "27. Revoke APP_MANAGER_ROLE role from the AGENT",
        agent_forward(
            [
                (
                    contracts.acl.address,
                    contracts.acl.revokePermission.encode_input(
                        AGENT,
                        ARAGON_KERNEL,
                        convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE")),  # FIXME: remove to_uint
                    ),
                )
            ]
        ),
        # --- Oracle configs
        # "28. Grant CONFIG_MANAGER_ROLE role to the AGENT",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    grant_to=contracts.agent,  # FIXME: misleading usage of contract
                )
            ]
        ),
        # "29. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig",
        agent_forward(
            [
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input("NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP"),
                )
            ]
        ),
        # "30. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
        agent_forward(
            [
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input("VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS"),
                )
            ]
        ),
        # "31. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
        agent_forward(
            [
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input("VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS"),
                )
            ]
        ),
        # "32. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig",
        agent_forward(
            [
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.set.encode_input(
                        "EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS", EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS
                    ),
                )
            ]
        ),
        # "33. Revoke CONFIG_MANAGER_ROLE role from the AGENT",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    revoke_from=contracts.agent,  # FIXME: typing says its str
                )
            ]
        ),
        # --- CSM
        # "34. Upgrade CSM implementation on proxy",
        agent_forward(
            [
                encode_proxy_upgrade_to(
                    contracts.csm,
                    CSM_IMPL_V2_ADDRESS,
                )
            ]
        ),
        # "35. Call `finalizeUpgradeV2()` on CSM contract",
        agent_forward(
            [
                (
                    contracts.csm.address,
                    contracts.csm.finalizeUpgradeV2.encode_input(),
                )
            ]
        ),
        # "36. Upgrade CSAccounting implementation on proxy",
        agent_forward(
            [
                encode_proxy_upgrade_to(
                    contracts.cs_accounting,
                    CS_ACCOUNTING_IMPL_V2_ADDRESS,
                )
            ]
        ),
        # "37. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract",
        agent_forward(
            [
                (
                    contracts.cs_accounting.address,
                    contracts.cs_accounting.finalizeUpgradeV2.encode_input(CS_CURVES),
                )
            ]
        ),
        # "38. Upgrade CSFeeOracle implementation on proxy",
        agent_forward(
            [
                encode_proxy_upgrade_to(
                    contracts.cs_fee_oracle,
                    CS_FEE_ORACLE_IMPL_V2_ADDRESS,
                )
            ]
        ),
        # "39. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract",
        agent_forward(
            [
                (
                    contracts.cs_fee_oracle.address,
                    contracts.cs_fee_oracle.finalizeUpgradeV2.encode_input(CSM_CONSENSUS_VERSION),
                )
            ]
        ),
        # "40. Upgrade CSFeeDistributor implementation on proxy",
        agent_forward(
            [
                encode_proxy_upgrade_to(
                    contracts.cs_fee_distributor,
                    CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
                )
            ]
        ),
        # "41. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract",
        agent_forward(
            [
                (
                    contracts.cs_fee_distributor.address,
                    contracts.cs_fee_distributor.finalizeUpgradeV2.encode_input(contracts.agent),
                )
            ]
        ),
        # "42. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    revoke_from=contracts.csm,
                )
            ]
        ),
        # "43. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=contracts.csm,
                )
            ]
        ),
        # "44. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=CSM_COMMITTEE_MS,
                )
            ]
        ),
        # "45. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=CS_PERMISSIONLESS_GATE_ADDRESS,
                )
            ]
        ),
        # "46. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=CS_VETTED_GATE_ADDRESS,
                )
            ]
        ),
        # "47. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    grant_to=CS_VETTED_GATE_ADDRESS,
                )
            ]
        ),
        # "48. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.csm,
                    role_name="VERIFIER_ROLE",
                    revoke_from=contracts.cs_verifier,
                )
            ]
        ),
        # "49. Grant role VERIFIER_ROLE to the new instance of the Verifier contract",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="VERIFIER_ROLE",
                    grant_to=CS_VERIFIER_V2_ADDRESS,
                )
            ]
        ),
        # "50. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.csm,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "51. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "52. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.cs_fee_oracle,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "53. Grant CSM role PAUSE_ROLE for the new GateSeal instance",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ]
        ),
        # "54. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.cs_accounting,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ]
        ),
        # "55. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.cs_fee_oracle,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ]
        ),
        # "56. Grant MANAGE_BOND_CURVES_ROLE to the AGENT",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.cs_accounting,
                    role_name="MANAGE_BOND_CURVES_ROLE",
                    grant_to=contracts.agent,
                )
            ]
        ),
        # "57. Add Identified Community Stakers Gate Bond Curve",
        agent_forward(
            [
                (
                    contracts.cs_accounting.address,
                    contracts.cs_accounting.addBondCurve.encode_input(CS_ICS_GATE_BOND_CURVE),
                )
            ]
        ),
        # "58. Revoke MANAGE_BOND_CURVES_ROLE from the AGENT",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="MANAGE_BOND_CURVES_ROLE",
                    revoke_from=contracts.agent,
                )
            ]
        ),
        # "59. Increase CSM share in Staking Router from 15% to 16%",
        agent_forward([encode_staking_router_update_csm_module_share()]),
        # --- Gate Seals
        # "60. Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.withdrawal_queue,
                    role_name="PAUSE_ROLE",
                    revoke_from=OLD_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "61. Revoke PAUSE_ROLE on ValidatorsExitBusOracle from the old GateSeal",
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="PAUSE_ROLE",
                    revoke_from=OLD_GATE_SEAL_ADDRESS,
                )
            ]
        ),
        # "62. Grant PAUSE_ROLE on WithdrawalQueue to the new WithdrawalQueue GateSeal",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.withdrawal_queue,
                    role_name="PAUSE_ROLE",
                    grant_to=NEW_WQ_GATE_SEAL,
                )
            ]
        ),
        # "63. Grant PAUSE_ROLE on ValidatorsExitBusOracle to the new Triggerable Withdrawals GateSeal",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="PAUSE_ROLE",
                    grant_to=NEW_TW_GATE_SEAL,
                )
            ]
        ),
        # "64. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to the new Triggerable Withdrawals GateSeal",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="PAUSE_ROLE",
                    grant_to=NEW_TW_GATE_SEAL,
                )
            ]
        ),
        # "65. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to ResealManager",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="PAUSE_ROLE",
                    grant_to=RESEAL_MANAGER,
                )
            ]
        ),
        # "66. Grant RESUME_ROLE on TriggerableWithdrawalsGateway to ResealManager",
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="RESUME_ROLE",
                    grant_to=RESEAL_MANAGER,
                )
            ]
        ),
    ]
    dg_call_script = submit_proposals(
        [
            (
                dg_items,
                "Upgrade to CSM v2 and Triggerable Withdrawals",
            )
        ]
    )

    vote_desc_items, call_script_items = zip(
        ("""
--- Locator
1. Update locator implementation
--- VEB
2. Update VEBO implementation
3. Call finalizeUpgrade_v2(maxValidatorsPerReport, maxExitRequestsLimit, exitsPerFrame, frameDurationInSec) on VEBO
4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
5. Bump VEBO consensus version to `4`
6. Revoke VEBO role MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
7. Grant SUBMIT_REPORT_HASH_ROLE on Validator Exit Bus Oracle to the EasyTrack EVM Script Executor
--- Triggerable Withdrawals Gateway (TWG)
8. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the CS Ejector
9. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEB
10. Connect TRIGGERABLE_WITHDRAWALS_GATEWAY to Dual Governance tiebreaker
--- WV
11. Update WithdrawalVault implementation
12. Call finalizeUpgrade_v2() on WithdrawalVault
--- AO
13. Update Accounting Oracle implementation
14. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
15. Bump AO consensus version to `4`
16. Revoke AO MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
17. Call finalizeUpgrade_v3() on AO
--- SR
18. Update SR implementation
19. Call finalizeUpgrade_v3() on SR
20. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitVerifier
21. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG
--- Curated Staking Module
22. Grant APP_MANAGER_ROLE role to the AGENT on Kernel
23. Update `NodeOperatorsRegistry` implementation
24. Call finalizeUpgrade_v4 on Curated Staking Module
--- sDVT
25. Update `SimpleDVT` implementation
26. Call finalizeUpgrade_v4 on sDVT
27. Revoke APP_MANAGER_ROLE role from the AGENT on Kernel
--- Oracle configs ---
28. Grant CONFIG_MANAGER_ROLE role to the AGENT
29. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig
30. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
31. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
32. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig
33. Revoke CONFIG_MANAGER_ROLE role from the AGENT
--- CSM ---
34. Upgrade CSM implementation on proxy
35. Call `finalizeUpgradeV2()` on CSM contract
36. Upgrade CSAccounting implementation on proxy
37. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract
38. Upgrade CSFeeOracle implementation on proxy
39. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract
40. Upgrade CSFeeDistributor implementation on proxy
41. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract
42. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract
43. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract
44. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee
45. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate
46. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate
47. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate
48. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract
49. Grant role VERIFIER_ROLE to the new instance of the Verifier contract
50. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance
51. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance
52. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance
53. Grant CSM role PAUSE_ROLE for the new GateSeal instance
54. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance
55. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance
56. Grant MANAGE_BOND_CURVES_ROLE to the AGENT
57. Add Identified Community Stakers Gate Bond Curve
58. Revoke MANAGE_BOND_CURVES_ROLE from the AGENT
59. Increase CSM share in Staking Router from 15% to 16%
--- Gate Seals ---
60. Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
61. Revoke PAUSE_ROLE on ValidatorsExitBusOracle from the old GateSeal
62. Grant PAUSE_ROLE on WithdrawalQueue to the new WithdrawalQueue GateSeal
63. Grant PAUSE_ROLE on ValidatorsExitBusOracle to the new Triggerable Withdrawals GateSeal
64. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to the new Triggerable Withdrawals GateSeal
--- ResealManager ---
65. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to ResealManager
66. Grant RESUME_ROLE on TriggerableWithdrawalsGateway to ResealManager""", dg_call_script[0]),
        (
            "67. Add CSSetVettedGateTree factory to EasyTrack with permissions",
            add_evmscript_factory(
                factory=EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY,
                permissions=(create_permissions(interface.CSVettedGate(CS_VETTED_GATE_ADDRESS), "setTreeParams")),
            ),
        ),
        (
            "68. Add `SubmitValidatorsExitRequestHashes` (SDVT) EVM script factory to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                permissions=(create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")),
            ),
        ),
        (
            "69. Add `SubmitValidatorsExitRequestHashes` (Curated Module) EVM script factory to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                permissions=(create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")),
            ),
        ),
    )

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    assert confirm_vote_script(vote_items, silent, desc_ipfs)

    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
