"""
Vote 03/07/2025 [HOODI]

--- Locator
1. Update locator implementation
--- VEB
2. Update VEBO implementation
3. Call finalizeUpgrade_v2(maxValidatorsPerReport, maxExitRequestsLimit, exitsPerFrame, frameDurationInSec) on VEBO
4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
5. Bump VEBO consensus version to `4`
6. Revoke VEBO role MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
--- Triggerable Withdrawals Gateway (TWG)
7. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the CS Ejector
8. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEB
--- EasyTrack VEB
9. Grant SUBMIT_REPORT_HASH_ROLE on Validator Exit Bus Oracle to the EasyTrack EVM Script Executor
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
19. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitVerifier
20. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG
--- NOR
21. Grant APP_MANAGER_ROLE role to the AGENT on Kernel
22. Update `NodeOperatorsRegistry` implementation
23. Call finalizeUpgrade_v4 on NOR
--- sDVT
24. Update `SimpleDVT` implementation
25. Call finalizeUpgrade_v4 on sDVT
26. Revoke APP_MANAGER_ROLE role from the AGENT on Kernel
--- Oracle configs ---
27. Grant CONFIG_MANAGER_ROLE role to the AGENT
28. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig
29. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
30. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
31. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig
--- CSM ---
32. Upgrade CSM implementation on proxy
33. Call `finalizeUpgradeV2()` on CSM contract
34. Upgrade CSAccounting implementation on proxy
35. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract
36. Upgrade CSFeeOracle implementation on proxy
37. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract
38. Upgrade CSFeeDistributor implementation on proxy
39. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract
40. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract
41. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract
42. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee
43. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate
44. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate
45. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate
46. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract
47. Grant role VERIFIER_ROLE to the new instance of the Verifier contract
48. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance
49. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance
50. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance
51. Grant CSM role PAUSE_ROLE for the new GateSeal instance
52. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance
53. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance
54. Grant MANAGE_BOND_CURVES_ROLE to the AGENT
55. Add Identified Community Stakers Gate Bond Curve
56. Revoke MANAGE_BOND_CURVES_ROLE from the AGENT
57. Increase CSM share in Staking Router from 15% to 20%
--- Gate Seals ---
58. Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
59. Revoke PAUSE_ROLE on ValidatorsExitBusOracle from the old GateSeal
60. Grant PAUSE_ROLE on WithdrawalQueue to the new WithdrawalQueue GateSeal
61. Grant PAUSE_ROLE on ValidatorsExitBusOracle to the new Triggerable Withdrawals GateSeal
62. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to the new Triggerable Withdrawals GateSeal
--- ResealManager ---
63. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to ResealManager
64. Grant RESUME_ROLE on TriggerableWithdrawalsGateway to ResealManager
--- EasyTrack ---
65. Add `SubmitValidatorsExitRequestHashes` (SDVT) EVM script factory to Easy Track
66. Add `SubmitValidatorsExitRequestHashes` (Curated Module) EVM script factory to Easy Track
67. Add CSSetVettedGateTree factory to EasyTrack with permissions
"""
import time

from typing import TYPE_CHECKING, Any, Dict
from typing import Tuple, Optional, Sequence
from brownie import interface, web3, convert, ZERO_ADDRESS  # type: ignore
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
from utils.dual_governance import submit_proposals
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
)
from utils.voting import confirm_vote_script, create_vote
from utils.config import get_deployer_account, get_priority_fee, get_is_live

DESCRIPTION = "Triggerable withdrawals and CSM v2 upgrade voting (HOODI)"

# New core contracts implementations
# TODO: Change to the correct addresses after deployment
LIDO_LOCATOR_IMPL = "0x5067457698Fd6Fa1C6964e416b3f42713513B3dD"
ACCOUNTING_ORACLE_IMPL = "0xe8D2A1E88c91DCd5433208d4152Cc4F399a7e91d"
VALIDATORS_EXIT_BUS_ORACLE_IMPL = "0x86A2EE8FAf9A840F7a2c64CA3d51209F9A02081D"
WITHDRAWAL_VAULT_IMPL = "0xf953b3A269d80e3eB0F2947630Da976B896A8C5b"
STAKING_ROUTER_IMPL = "0xAA292E8611aDF267e563f334Ee42320aC96D0463"
NODE_OPERATORS_REGISTRY_IMPL = "0x5c74c94173F05dA1720953407cbb920F3DF9f887"

TRIGGERABLE_WITHDRAWALS_GATEWAY = "0xA4899D35897033b927acFCf422bc745916139776"
VALIDATOR_EXIT_VERIFIER = "0x720472c8ce72c2A2D711333e064ABD3E6BbEAdd3"

# Oracle consensus versions
AO_CONSENSUS_VERSION = 4
VEBO_CONSENSUS_VERSION = 4
CSM_CONSENSUS_VERSION = 3

# Fixed constants from Holesky version
EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS = 7 * 7200  # 7 * 7200 in Holesky
NOR_EXIT_DEADLINE_IN_SEC = 172800  # 172800 in Holesky (48 hours)

# VEB parameters from Holesky
MAX_VALIDATORS_PER_REPORT = 600
MAX_EXIT_REQUESTS_LIMIT = 13000
EXITS_PER_FRAME = 1
FRAME_DURATION_IN_SEC = 48

# CSM
CS_MODULE_NEW_TARGET_SHARE_BP = 2000  # 20%
CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 2500  # 25%

# TODO: Change to the correct addresses after deployment
CS_ACCOUNTING_IMPL_V2_ADDRESS = "0x84eA74d481Ee0A5332c457a4d796187F6Ba67fEB"
CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS = "0x1291Be112d480055DaFd8a610b7d1e203891C274"
CS_FEE_ORACLE_IMPL_V2_ADDRESS = "0x7969c5eD335650692Bc04293B07F5BF2e7A673C0"
CSM_IMPL_V2_ADDRESS = "0xCD8a1C3ba11CF5ECfa6267617243239504a98d90"

CS_GATE_SEAL_V2_ADDRESS = "0x1568928F73E4F5e2f748dA36bc56eCcc2fb66457"
CS_SET_VETTED_GATE_TREE_FACTORY = ZERO_ADDRESS
CS_EJECTOR_ADDRESS = "0xcbEAF3BDe82155F56486Fb5a1072cb8baAf547cc"
CS_PERMISSIONLESS_GATE_ADDRESS = "0x9E545E3C0baAB3E08CdfD552C960A1050f373042"
CS_VETTED_GATE_ADDRESS = "0x9467A509DA43CB50EB332187602534991Be1fEa4"
CS_VERIFIER_V2_ADDRESS = "0xB0D4afd8879eD9F52b28595d31B441D079B2Ca07"

CS_CURVES = [
    ([1, 2 * 10**18], [2, 1.9 * 10**18], [3, 1.8 * 10**18], [4, 1.7 * 10**18], [5, 1.6 * 10**18], [6, 1.5 * 10**18]),  # Default Curve
    ([1, 1.5 * 10**18], [2, 1.9 * 10**18], [3, 1.8 * 10**18], [4, 1.7 * 10**18], [5, 1.6 * 10**18], [6, 1.5 * 10**18]),  # Legacy EA Curve
]
CS_ICS_GATE_BOND_CURVE = ([1, 1.5 * 10**18], [2, 1.3 * 10**18])  # Identified Community Stakers Gate Bond Curve

# Add missing constants
OLD_GATE_SEAL_ADDRESS = "0xAE6eCd77DCC656c5533c4209454Fd56fB46e1778"  # TODO: Update for HOODI
NEW_WQ_GATE_SEAL = "0xE900BC859EB750562E1009e912B63743BC877662"  # TODO: Update for HOODI
NEW_TW_GATE_SEAL = "0xaEEF47C61f2A9CCe4C4D0363911C5d49e2cFb6f1"  # TODO: Update for HOODI
RESEAL_MANAGER = "0x9dE2273f9f1e81145171CcA927EFeE7aCC64c9fb"  # TODO: Update for HOODI

# Add EasyTrack constants
EASYTRACK_EVMSCRIPT_EXECUTOR = "0x2819B65021E13CEEB9AC33E77DB32c7e64e7520D"  # TODO: Update for HOODI
EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x4aB23f409F8F6EdeF321C735e941E4670804a1B4"  # TODO: Update for HOODI
EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x7A1c5af4625dc1160a7c67d00335B6Ad492bE53f"  # TODO: Update for HOODI


def encode_staking_router_proxy_update(implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(contracts.staking_router)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_wv_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.WithdrawalContractProxy(proxy)

    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b'')


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
        )
    )


def to_percent(bp: int) -> float:
    """
    Convert basis points to percentage.
    """
    return bp / 10000 * 100


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[Any]]:
    vote_desc_items, call_script_items = zip(
        # --- locator
        (
            "1. Update locator implementation",
            agent_forward([encode_proxy_upgrade_to(contracts.lido_locator, LIDO_LOCATOR_IMPL)])
        ),
        # --- VEB
        (
            "2. Update VEBO implementation",
            agent_forward([encode_proxy_upgrade_to(contracts.validators_exit_bus_oracle, VALIDATORS_EXIT_BUS_ORACLE_IMPL)])
        ),
        (
            "3. Call finalizeUpgrade_v2 on VEBO",
            agent_forward([
                (
                    contracts.validators_exit_bus_oracle.address,
                    contracts.validators_exit_bus_oracle.finalizeUpgrade_v2.encode_input(
                        MAX_VALIDATORS_PER_REPORT, MAX_EXIT_REQUESTS_LIMIT, EXITS_PER_FRAME, FRAME_DURATION_IN_SEC
                    ),
                )
            ])
        ),
        (
            "4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            "5. Bump VEBO consensus version to `4`",
            agent_forward([encode_oracle_upgrade_consensus(contracts.validators_exit_bus_oracle, VEBO_CONSENSUS_VERSION)])
        ),
        (
            "6. Revoke VEBO role MANAGE_CONSENSUS_VERSION_ROLE from the AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        # --- Triggerable Withdrawals Gateway (TWG)
        (
            "7. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the CS Ejector",
            agent_forward([
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=CS_EJECTOR_ADDRESS,
                )
            ])
        ),
        (
            "8. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEB",
            agent_forward([
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.validators_exit_bus_oracle,
                )
            ])
        ),
        # --- EasyTrack VEB
        (
            "9. Grant SUBMIT_REPORT_HASH_ROLE on Validator Exit Bus Oracle to the EasyTrack EVM Script Executor",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="SUBMIT_REPORT_HASH_ROLE",
                    grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
                )
            ])
        ),
        (
            "10. Connect TRIGGERABLE_WITHDRAWALS_GATEWAY to Dual Governance tiebreaker",
            (
                contracts.dual_governance.address,
                contracts.dual_governance.addTiebreakerSealableWithdrawalBlocker.encode_input(
                    TRIGGERABLE_WITHDRAWALS_GATEWAY
                ),
            )
        ),
        # --- WV
        (
            "11. Update WithdrawalVault implementation",
            agent_forward([encode_wv_proxy_upgrade_to(contracts.withdrawal_vault, WITHDRAWAL_VAULT_IMPL)])
        ),
        (
            "12. Call finalizeUpgrade_v2 on WithdrawalVault",
            agent_forward([
                (
                    contracts.withdrawal_vault.address,
                    contracts.withdrawal_vault.finalizeUpgrade_v2.encode_input(),
                )
            ])
        ),
        # --- AO
        (
            "13. Update Accounting Oracle implementation",
            agent_forward([encode_proxy_upgrade_to(contracts.accounting_oracle, ACCOUNTING_ORACLE_IMPL)])
        ),
        (
            "14. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            "15. Bump AO consensus version to `4`",
            agent_forward([encode_oracle_upgrade_consensus(contracts.accounting_oracle, AO_CONSENSUS_VERSION)])
        ),
        (
            "16. Revoke AO MANAGE_CONSENSUS_VERSION_ROLE from the AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            "17. Call finalizeUpgrade_v3() on AO",
            agent_forward([
                (
                    contracts.accounting_oracle.address,
                    contracts.accounting_oracle.finalizeUpgrade_v3.encode_input(),
                )
            ])
        ),
        # --- SR
        (
            "18. Update SR implementation",
            agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)])
        ),
        (
            "19. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitDelayVerifier",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                    grant_to=VALIDATOR_EXIT_VERIFIER,
                )
            ])
        ),
        (
            "20. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE",
                    grant_to=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                )
            ])
        ),
        # --- NOR and sDVT
        (
            "21. Grant APP_MANAGER_ROLE role to the AGENT",
            agent_forward([
                (
                    contracts.acl.address,
                    contracts.acl.grantPermission.encode_input(
                        AGENT,
                        ARAGON_KERNEL,
                        convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE"))
                    )
                )
            ])
        ),
        (
            "22. Update `NodeOperatorsRegistry` implementation",
            agent_forward([
                (
                    contracts.kernel.address,
                    contracts.kernel.setApp.encode_input(
                        contracts.kernel.APP_BASES_NAMESPACE(),
                        NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
                        NODE_OPERATORS_REGISTRY_IMPL
                    )
                )
            ])
        ),
        (
            "23. Call finalizeUpgrade_v4 on NOR",
            agent_forward([
                (
                    interface.NodeOperatorsRegistry(contracts.node_operators_registry).address,
                    interface.NodeOperatorsRegistry(contracts.node_operators_registry).finalizeUpgrade_v4.encode_input(
                        NOR_EXIT_DEADLINE_IN_SEC
                    )
                )
            ])
        ),
        (
            "24. Update `SDVT` implementation",
            agent_forward([
                (
                    contracts.kernel.address,
                    contracts.kernel.setApp.encode_input(
                        contracts.kernel.APP_BASES_NAMESPACE(),
                        SIMPLE_DVT_ARAGON_APP_ID,
                        NODE_OPERATORS_REGISTRY_IMPL
                    )
                )
            ])
        ),
        (
            "25. Call finalizeUpgrade_v4 on SDVT",
            agent_forward([
                (
                    interface.NodeOperatorsRegistry(contracts.simple_dvt).address,
                    interface.NodeOperatorsRegistry(contracts.simple_dvt).finalizeUpgrade_v4.encode_input(
                        NOR_EXIT_DEADLINE_IN_SEC
                    )
                )
            ])
        ),
        (
            "26. Revoke APP_MANAGER_ROLE role from the AGENT",
            agent_forward([
                (
                    contracts.acl.address,
                    contracts.acl.revokePermission.encode_input(
                        AGENT,
                        ARAGON_KERNEL,
                        convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE"))
                    )
                )
            ])
        ),
        # --- Oracle configs
        (
            "27. Grant CONFIG_MANAGER_ROLE role to the AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            "28. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input('NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP'),
                )
            ])
        ),
        (
            "29. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS'),
                )
            ])
        ),
        (
            "30. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS'),
                )
            ])
        ),
        (
            "31. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.set.encode_input('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS', EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS),
                )
            ])
        ),
        # --- CSM
        (
            "32. Upgrade CSM implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(
                    contracts.csm,
                    CSM_IMPL_V2_ADDRESS,
                )
            ])
        ),
        (
            "33. Call `finalizeUpgradeV2()` on CSM contract",
            agent_forward([
                (
                    contracts.csm.address,
                    contracts.csm.finalizeUpgradeV2.encode_input(),
                )
            ])
        ),
        (
            "34. Upgrade CSAccounting implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(
                    contracts.cs_accounting,
                    CS_ACCOUNTING_IMPL_V2_ADDRESS,
                )
            ])
        ),
        (
            "35. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract",
            agent_forward([
                (
                    contracts.cs_accounting.address,
                    contracts.cs_accounting.finalizeUpgradeV2.encode_input(CS_CURVES),
                )
            ])
        ),
        (
            "36. Upgrade CSFeeOracle implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(
                    contracts.cs_fee_oracle,
                    CS_FEE_ORACLE_IMPL_V2_ADDRESS,
                )
            ])
        ),
        (
            "37. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract",
            agent_forward([
                (
                    contracts.cs_fee_oracle.address,
                    contracts.cs_fee_oracle.finalizeUpgradeV2.encode_input(CSM_CONSENSUS_VERSION),
                )
            ])
        ),
        (
            "38. Upgrade CSFeeDistributor implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(
                    contracts.cs_fee_distributor,
                    CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
                )
            ])
        ),
        (
            "39. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract",
            agent_forward([
                (
                    contracts.cs_fee_distributor.address,
                    contracts.cs_fee_distributor.finalizeUpgradeV2.encode_input(contracts.agent),
                )
            ])
        ),
        (
            "40. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    revoke_from=contracts.csm,
                )
            ])
        ),
        (
            "41. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=contracts.csm,
                )
            ])
        ),
        (
            "42. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=CSM_COMMITTEE_MS,
                )
            ])
        ),
        (
            "43. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=CS_PERMISSIONLESS_GATE_ADDRESS,
                )
            ])
        ),
        (
            "44. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=CS_VETTED_GATE_ADDRESS,
                )
            ])
        ),
        (
            "45. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    grant_to=CS_VETTED_GATE_ADDRESS,
                )
            ])
        ),
        (
            "46. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.csm,
                    role_name="VERIFIER_ROLE",
                    revoke_from=contracts.cs_verifier,
                )
            ])
        ),
        (
            "47. Grant role VERIFIER_ROLE to the new instance of the Verifier contract",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="VERIFIER_ROLE",
                    grant_to=CS_VERIFIER_V2_ADDRESS,
                )
            ])
        ),
        (
            "48. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.csm,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ])
        ),
        (
            "49. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ])
        ),
        (
            "50. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_fee_oracle,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ])
        ),
        (
            "51. Grant CSM role PAUSE_ROLE for the new GateSeal instance",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ])
        ),
        (
            "52. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.cs_accounting,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ])
        ),
        (
            "53. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.cs_fee_oracle,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ])
        ),
        (
            "54. Grant MANAGE_BOND_CURVES_ROLE to the AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.cs_accounting,
                    role_name="MANAGE_BOND_CURVES_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            "55. Add Identified Community Stakers Gate Bond Curve",
            agent_forward([
                (
                    contracts.cs_accounting.address,
                    contracts.cs_accounting.addBondCurve.encode_input(CS_ICS_GATE_BOND_CURVE),
                )
            ])
        ),
        (
            "56. Revoke MANAGE_BOND_CURVES_ROLE from the AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="MANAGE_BOND_CURVES_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            "57. Increase CSM share in Staking Router from 15% to 20%",
            agent_forward([encode_staking_router_update_csm_module_share()])
        ),
        # --- Gate Seals
        (
            "58. Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.withdrawal_queue,
                    role_name="PAUSE_ROLE",
                    revoke_from=OLD_GATE_SEAL_ADDRESS,
                )
            ])
        ),
        (
            "59. Revoke PAUSE_ROLE on ValidatorsExitBusOracle from the old GateSeal",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="PAUSE_ROLE",
                    revoke_from=OLD_GATE_SEAL_ADDRESS,
                )
            ])
        ),
        (
            "60. Grant PAUSE_ROLE on WithdrawalQueue to the new WithdrawalQueue GateSeal",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_queue,
                    role_name="PAUSE_ROLE",
                    grant_to=NEW_WQ_GATE_SEAL,
                )
            ])
        ),
        (
            "61. Grant PAUSE_ROLE on ValidatorsExitBusOracle to the new Triggerable Withdrawals GateSeal",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="PAUSE_ROLE",
                    grant_to=NEW_TW_GATE_SEAL,
                )
            ])
        ),
        (
            "62. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to the new Triggerable Withdrawals GateSeal",
            agent_forward([
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="PAUSE_ROLE",
                    grant_to=NEW_TW_GATE_SEAL,
                )
            ])
        ),
        (
            "63. Grant PAUSE_ROLE on TriggerableWithdrawalsGateway to ResealManager",
            agent_forward([
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="PAUSE_ROLE",
                    grant_to=RESEAL_MANAGER,
                )
            ])
        ),
        (
            "64. Grant RESUME_ROLE on TriggerableWithdrawalsGateway to ResealManager",
            agent_forward([
                encode_oz_grant_role(
                    contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                    role_name="RESUME_ROLE",
                    grant_to=RESEAL_MANAGER,
                )
            ])
        ),
    )

    dg_bypass_item = {
        "65. Add CSSetVettedGateTree factory to EasyTrack with permissions": add_evmscript_factory(
                factory=CS_SET_VETTED_GATE_TREE_FACTORY,
                permissions=(create_permissions(interface.CSVettedGate(CS_VETTED_GATE_ADDRESS), "setTreeParams")),
            ),
        "66. Add `SubmitValidatorsExitRequestHashes` (SDVT) EVM script factory to Easy Track": add_evmscript_factory(
                factory=EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                permissions=(create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")),
            ),
        "67. Add `SubmitValidatorsExitRequestHashes` (Curated Module) EVM script factory to Easy Track": add_evmscript_factory(
                factory=EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                permissions=(create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")),
            )
    }

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

    dg_desc = "\n".join(vote_desc_items)
    dg_vote = submit_proposals(call_script_items, dg_desc)
    vote_items = {dg_desc: dg_vote, **dg_bypass_item}

    assert confirm_vote_script(vote_items, silent, desc_ipfs)

    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
