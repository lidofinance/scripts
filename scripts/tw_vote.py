from itertools import count
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from utils.config import (
    CS_ACCOUNTING_IMPL_V2_ADDRESS,
    CS_CURVES,
    CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
    CS_FEE_ORACLE_IMPL_V2_ADDRESS,
    CS_GATE_SEAL_ADDRESS,
    CS_GATE_SEAL_V2_ADDRESS,
    CSM_COMMITTEE_MS,
    CSM_IMPL_V2_ADDRESS,
    NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
    NODE_OPERATORS_REGISTRY_IMPL,
    SIMPLE_DVT_ARAGON_APP_ID,
    STAKING_ROUTER_IMPL,
    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    WITHDRAWAL_VAULT_IMPL,
    contracts,
    get_deployer_account,
    get_priority_fee,
)
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import get_deployer_account, get_priority_fee
from utils.agent import agent_forward
from utils.kernel import update_app_implementation

try:
    from brownie import interface
except ImportError as e:
    print(f"ImportError: {e}")
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")
    if TYPE_CHECKING:
        interface: Any = ...


TW_DESCRIPTION = "Proposal to use TW in Lido protocol"

## Oracle consensus versions
AO_CONSENSUS_VERSION = 4
VEBO_CONSENSUS_VERSION = 4

EXIT_DAILY_LIMIT = 20
TW_DAILY_LIMIT = 10

EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS = 7200

NOR_EXIT_DEADLINE_IN_SEC = 30 * 60

DEVNET_01_ADDRESS = '0x308eaCED5a0c5C4e717b29eD49300158ddeE8D54'

NOR_VERSION = ["2", "0", "0"]
SDVT_VERSION = ["2", "0", "0"]

def _add_implementation_to_repo(repo, version, address, content_uri):
    return (repo.address, repo.newVersion.encode_input(version, address, content_uri))

def add_implementation_to_nor_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.nor_app_repo, version, address, content_uri)

def add_implementation_to_sdvt_app_repo(version, address, content_uri):
    return _add_implementation_to_repo(contracts.simple_dvt_app_repo, version, address, content_uri)

def encode_staking_router_proxy_update(implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(contracts.staking_router)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)

def get_repo_uri(repo_address: str) -> str:
    print("repo_address", repo_address)
    contract = interface.Repo(repo_address).getLatest()
    print("contract", contract)
    return contract["contentURI"]

def encode_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)

def encode_wv_proxy_upgrade_to(proxy: Any, implementation: str) -> Tuple[str, str]:
    proxy = interface.WithdrawalContractProxy(proxy)
    if (proxy.proxy_getAdmin() != contracts.voting.address):
        raise Exception('withdrawal_contract is not in a valid state')

    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b'')


def encode_oracle_upgrade_consensus(proxy: Any, consensus_version: int) -> Tuple[str, str]:
    oracle = interface.BaseOracle(proxy)
    return oracle.address, oracle.setConsensusVersion.encode_input(consensus_version)

def create_tw_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[Any]]:
    """
        Triggerable withdrawals voting baking and sending.

        Contains next steps:
            --- VEB
            1. Update VEBO implementation
            2. Call finalizeUpgrade_v2 on VEBO
            3. Grant VEBO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            4. Bump VEBO consensus version to `4`
            5. Revoke VEBO MANAGE_CONSENSUS_VERSION_ROLE from AGENT
            6. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to CSEjector
            7. Grant VEB SUBMIT_REPORT_HASH_ROLE to the AGENT/VOTING (TBD)
            8. Grant VEB EXIT_REPORT_LIMIT_ROLE role to AGENT
            9. Call setExitRequestLimit on VEB
            10. Revoke VEB EXIT_REPORT_LIMIT_ROLE from AGENT
            --- WV
            11. Update WithdrawalVault implementation
            12. Call finalizeUpgrade_v2 on WithdrawalVault
            13. Grant WithdrawalVault ADD_WITHDRAWAL_REQUEST_ROLE to the VEB
            --- AO
            14. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            15. Bump AO consensus version to `4`
            16. Revoke MANAGE_CONSENSUS_VERSION_ROLE from AGENT
            --- SR
            17. Update SR implementation
            18. Grant SR REPORT_EXITED_VALIDATORS_STATUS_ROLE to ValidatorExitVerifier
            19. Grant SR REPORT_EXITED_VALIDATORS_ROLE to VEB
            --- NOR
            20. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo
            21. Update `NodeOperatorsRegistry` implementation
            22. Call finalizeUpgrade_v4 on NOR
            --- sDVT
            23. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo
            24. Update `SimpleDVT` implementation
            25. Call finalizeUpgrade_v4 on sDVT
            --- Oracle configs ---
            30. Grant CONFIG_MANAGER_ROLE role to the AGENT
            31. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig
            32. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            33. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            34. Add EXIT_EVENTS_LOOKBACK_WINDOW_SLOTS variable to OracleDaemonConfig
            35. Revoke CONFIG_MANAGER_ROLE from AGENT
            --- Temp ---
            40. Add ADD_WITHDRAWAL_REQUEST_ROLE WV for Consolidation to the TEMP-DEVNET-01 (write contract)
            41. Add ADD_CONSOLIDATION_REQUEST_ROLE WV for Triggerable Withdrawal to the TEMP-DEVNET-01 (write contract)
            42. Add PAUSE_ROLE for WV to the TEMP-DEVNET-01
            43. Add DIRECT_EXIT_ROLE VEB for direct exits to the TEMP-DEVNET-01
            44. Add PAUSE_ROLE for VEB to the TEMP-DEVNET-01
            45. Add SUBMIT_REPORT_HASH_ROLE for VEB to the TEMP-DEVNET-01
            --- CSM ---
            46. Upgrade CSM implementation on proxy
            47. Call `finalizeUpgradeV2()` on CSM contract
            48. Upgrade CSAccounting implementation on proxy
            49. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract
            50. Upgrade CSFeeOracle implementation on proxy
            51. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract
            52. Upgrade CSFeeDistributor implementation on proxy
            53. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract
            54. Revoke SET_BOND_CURVE_ROLE on CSAccounting from CSM
            55. Revoke RESET_BOND_CURVE_ROLE on CSAccounting from CSM
            56. Revoke RESET_BOND_CURVE_ROLE on CSAccounting from CSM committee
            57. Grant CREATE_NODE_OPERATOR_ROLE on CSM to the permissionless gate
            58. Grant CREATE_NODE_OPERATOR_ROLE on CSM to the vetted gate
            59. Grant SET_BOND_CURVE_ROLE on CSAccounting to the vetted gate
            60. Revoke VERIFIER_ROLE on CSM from the previous instance of CSVerifier
            61. Grant VERIFIER_ROLE on CSM to the new instance of CSVerifier
            62. Revoke PAUSE_ROLE on CSM from the previous GateSeal instance
            63. Revoke PAUSE_ROLE on CSAccounting from the previous GateSeal instance
            64. Revoke PAUSE_ROLE on CSFeeOracle from the previous GateSeal instance
            65. Grant PAUSE_ROLE on CSM to the new GateSeal instance
            66. Grant PAUSE_ROLE on CSAccounting to the new GateSeal instance
            67. Grant PAUSE_ROLE on CSAccounting to the new GateSeal instance
            68. Revoke REQUEST_BURN_SHARES_ROLE on Burner from CSAccounting
            69. Grant REQUEST_BURN_MY_STETH_ROLE on Burnder to CSAccounting
    """

    item_idx = count(1)

    nor_repo = contracts.nor_app_repo.address
    simple_dvt_repo = contracts.simple_dvt_app_repo.address

    nor_uri = get_repo_uri(nor_repo)
    simple_dvt_uri = get_repo_uri(simple_dvt_repo)

    vote_descriptions, call_script_items = zip(
        (
            f"{next(item_idx)}. Update VEBO implementation",
            agent_forward([
                encode_proxy_upgrade_to(contracts.validators_exit_bus_oracle, VALIDATORS_EXIT_BUS_ORACLE_IMPL)
            ])
        ),
        (
            f"{next(item_idx)}. Call finalizeUpgrade_v2 on VEBO",
            (
                contracts.validators_exit_bus_oracle.address,
                contracts.validators_exit_bus_oracle.finalizeUpgrade_v2.encode_input(),
            )
        ),
        (
            f"{next(item_idx)}. Grant VEBO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Bump VEBO consensus version to `{VEBO_CONSENSUS_VERSION}`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.validators_exit_bus_oracle, VEBO_CONSENSUS_VERSION)
            ])
        ),
        (
            f"{next(item_idx)}. Revoke VEBO MANAGE_CONSENSUS_VERSION_ROLE from AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant TWG ADD_FULL_WITHDRAWAL_REQUEST_ROLE to CSEjector",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.triggerable_withdrawals_gateway,
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.cs_ejector,
                )
            ])
        ),
        # (
        #     f"{next(item_idx)}. Grant VEB SUBMIT_REPORT_HASH_ROLE to the AGENT (TBD",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.validators_exit_bus_oracle,
        #             role_name="MANAGE_CONSENSUS_VERSION_ROLE",
        #             revoke_from=contracts.agent,
        #         )
        #     ])
        # ),
        (
            f"{next(item_idx)}. Grant VEB EXIT_REPORT_LIMIT_ROLE role to AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="EXIT_REPORT_LIMIT_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Call setExitRequestLimit on VEB",
            agent_forward([
                (
                    contracts.validators_exit_bus_oracle.address,
                    contracts.validators_exit_bus_oracle.setExitRequestLimit.encode_input(EXIT_DAILY_LIMIT, TW_DAILY_LIMIT),
                ),
            ])
        ),
        (
            f"{next(item_idx)}. Revoke VEB EXIT_REPORT_LIMIT_ROLE from AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="EXIT_REPORT_LIMIT_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Update WithdrawalVault implementation",
            encode_wv_proxy_upgrade_to(contracts.withdrawal_vault, WITHDRAWAL_VAULT_IMPL)
        ),
        (
            f"{next(item_idx)}. Call finalizeUpgrade_v2 on WithdrawalVault",
            (
                contracts.withdrawal_vault.address,
                contracts.withdrawal_vault.finalizeUpgrade_v2.encode_input(
                    contracts.agent,
                ),
            )
        ),
        (
            f"{next(item_idx)}. Grant WithdrawalVault ADD_WITHDRAWAL_REQUEST_ROLE to the VEB",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="ADD_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.validators_exit_bus_oracle,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Bump AO consensus version to `{AO_CONSENSUS_VERSION}`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.accounting_oracle, AO_CONSENSUS_VERSION)
            ])
        ),
        (
            f"{next(item_idx)}. Revoke MANAGE_CONSENSUS_VERSION_ROLE from AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Update SR implementation",
            agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)]),
        ),
        (
            f"{next(item_idx)}. Grant SR REPORT_EXITED_VALIDATORS_STATUS_ROLE to ValidatorExitVerifier",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_EXITED_VALIDATORS_STATUS_ROLE",
                    grant_to=contracts.validator_exit_verifier,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant SR REPORT_EXITED_VALIDATORS_ROLE to VEB",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_EXITED_VALIDATORS_ROLE",
                    grant_to=contracts.validators_exit_bus_oracle,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo",
            add_implementation_to_nor_app_repo(NOR_VERSION, NODE_OPERATORS_REGISTRY_IMPL, nor_uri),
        ),
        (
            f"{next(item_idx)}. Update `NodeOperatorsRegistry` implementation",
            update_app_implementation(NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        ),
        (
            f"{next(item_idx)}. Call finalizeUpgrade_v4 on NOR",
            (
                interface.NodeOperatorsRegistry(contracts.node_operators_registry).address,
                interface.NodeOperatorsRegistry(contracts.node_operators_registry).finalizeUpgrade_v4.encode_input(
                    NOR_EXIT_DEADLINE_IN_SEC
                )
            )
        ),
        # TODO: Implement after devnet-01
        # (
        #     f"{next(item_idx)}. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo",
        #     add_implementation_to_sdvt_app_repo(SDVT_VERSION, NODE_OPERATORS_REGISTRY_IMPL, simple_dvt_uri),
        # ),
        # (
        #     f"{next(item_idx)}. Update `SimpleDVT` implementation",
        #     update_app_implementation(SIMPLE_DVT_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        # ),
        # (
        #     f"{next(item_idx)}. Call finalizeUpgrade_v4 on sDVT",
        # (
        #     contracts.sDVT.address,
        #     contracts.withdrawal_vault.finalizeUpgrade_v4.encode_input(
        #         NOR_EXIT_DEADLINE_IN_SEC,
        #     ),
        # )
        # ),
        (
            f"{next(item_idx)}. Grant CONFIG_MANAGER_ROLE role to the AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input('NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP'),
                ),
            ])
        ),
        (
            f"{next(item_idx)}. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS'),
                ),
            ])
        ),
        (
            f"{next(item_idx)}. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS'),
                ),
            ])
        ),
        (
            f"{next(item_idx)}. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.set.encode_input('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS', EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS),
                ),
            ])
        ),
        (
            f"{next(item_idx)}. Revoke CONFIG_MANAGER_ROLE from AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Add ADD_WITHDRAWAL_REQUEST_ROLE WV for Consolidation to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="ADD_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Add ADD_WITHDRAWAL_REQUEST_ROLE WV for Consolidation to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="ADD_CONSOLIDATION_REQUEST_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Add PAUSE_ROLE for WV to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="PAUSE_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Add DIRECT_EXIT_ROLE for WV to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="DIRECT_EXIT_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Add PAUSE_ROLE for VEB to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="PAUSE_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Add SUBMIT_REPORT_HASH_ROLE for VEB to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="SUBMIT_REPORT_HASH_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),

        # CSM related calls

        (
            f"{next(item_idx)}. Upgrade CSM implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(
                    contracts.csm,
                    CSM_IMPL_V2_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Call `finalizeUpgradeV2()` on CSM contract",
            (
                contracts.csm.address,
                contracts.csm.finalizeUpgradeV2.encode_input(),
            ),
        ),
        (
            f"{next(item_idx)}. Upgrade CSAccounting implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(
                    contracts.cs_accounting,
                    CS_ACCOUNTING_IMPL_V2_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract",
            (
                contracts.cs_accounting.address,
                contracts.cs_accounting.finalizeUpgradeV2.encode_input(CS_CURVES),
            ),
        ),
        (
            f"{next(item_idx)}. Upgrade CSFeeOracle implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(
                    contracts.cs_fee_oracle,
                    CS_FEE_ORACLE_IMPL_V2_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract",
            (
                contracts.cs_fee_oracle.address,
                contracts.cs_fee_oracle.finalizeUpgradeV2.encode_input(3),
            ),
        ),
        (
            f"{next(item_idx)}. Upgrade CSFeeDistributor implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(
                    contracts.cs_fee_distributor,
                    CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract",
            (
                contracts.cs_fee_distributor.address,
                contracts.cs_fee_distributor.finalizeUpgradeV2.encode_input(contracts.agent),
            ),
        ),
        (
            f"{next(item_idx)}. Revoke SET_BOND_CURVE_ROLE on CSAccounting from CSM",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    revoke_from=contracts.csm,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Revoke RESET_BOND_CURVE_ROLE on CSAccounting from CSM",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=contracts.csm,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Revoke RESET_BOND_CURVE_ROLE on CSAccounting from CSM committee",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=CSM_COMMITTEE_MS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant CREATE_NODE_OPERATOR_ROLE on CSM to the permissionless gate",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=contracts.cs_permissionless_gate,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant CREATE_NODE_OPERATOR_ROLE on CSM to the vetted gate",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=contracts.cs_vetted_gate,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant SET_BOND_CURVE_ROLE on CSAccounting to the vetted gate",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    grant_to=contracts.cs_vetted_gate,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Revoke VERIFIER_ROLE on CSM from the previous instance of CSVerifier",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.csm,
                    role_name="VERIFIER_ROLE",
                    revoke_from=contracts.cs_verifier,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant VERIFIER_ROLE on CSM to the new instance of CSVerifier",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="VERIFIER_ROLE",
                    grant_to=contracts.cs_verifier_v2,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Revoke PAUSE_ROLE on CSM from the previous GateSeal instance",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.csm,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Revoke PAUSE_ROLE on CSAccounting from the previous GateSeal instance",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Revoke PAUSE_ROLE on CSFeeOracle from the previous GateSeal instance",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_fee_oracle,
                    role_name="PAUSE_ROLE",
                    revoke_from=CS_GATE_SEAL_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant PAUSE_ROLE on CSM to the new GateSeal instance",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant PAUSE_ROLE on CSAccounting to the new GateSeal instance",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.cs_accounting,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant PAUSE_ROLE on CSAccounting to the new GateSeal instance",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.cs_fee_oracle,
                    role_name="PAUSE_ROLE",
                    grant_to=CS_GATE_SEAL_V2_ADDRESS,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Revoke REQUEST_BURN_SHARES_ROLE on Burner from CSAccounting",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.burner,
                    role_name="REQUEST_BURN_SHARES_ROLE",
                    revoke_from=contracts.cs_accounting,
                )
            ])
        ),
        (
            f"{next(item_idx)}. Grant REQUEST_BURN_MY_STETH_ROLE on Burnder to CSAccounting",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.burner,
                    role_name="REQUEST_BURN_MY_STETH_ROLE",
                    grant_to=contracts.cs_accounting,
                )
            ])
        ),
    )

    vote_items = bake_vote_items(list(vote_descriptions), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(TW_DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(TW_DESCRIPTION)

    assert confirm_vote_script(vote_items, silent, desc_ipfs), 'Vote not confirmed.'

    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)


def main():
    print('Start baking vote.')
    print("DEPLOYER ACCOUNT:", get_deployer_account())
    tx_params = {
        "from": get_deployer_account(),
        "priority_fee": get_priority_fee(),
    }

    vote_id, _ = create_tw_vote(tx_params=tx_params, silent=True)

    if vote_id:
        print(f'Vote [{vote_id}] created.')
