from typing import Dict, Tuple, Optional

from utils.config import (
    contracts, VALIDATORS_EXIT_BUS_ORACLE_IMPL, WITHDRAWAL_VAULT_IMPL, STAKING_ROUTER_IMPL,
    NODE_OPERATORS_REGISTRY_IMPL, NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, SIMPLE_DVT_ARAGON_APP_ID,
    CS_DEFAULT_BOND_CURVE, CS_VETTED_BOND_CURVE, CSM_COMMITTEE_MS, CS_GATE_SEAL_ADDRESS, CS_GATE_SEAL_V2_ADDRESS,
    CSM_IMPL_V2_ADDRESS, CS_ACCOUNTING_IMPL_V2_ADDRESS, CS_FEE_ORACLE_IMPL_V2_ADDRESS,
    CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS
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


TW_DESCRIPTION = "Proposal to use TW in Lido protocol"

## Oracle consensus versions
AO_CONSENSUS_VERSION = 4
VEBO_CONSENSUS_VERSION = 4

EXIT_DAILY_LIMIT = 20
TW_DAILY_LIMIT = 10

EXIT_EVENTS_LOOKBACK_WINDOW_SLOTS = 7200

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

def encode_proxy_upgrade_to(proxy: any, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)

def encode_wv_proxy_upgrade_to(proxy: any, implementation: str) -> Tuple[str, str]:
    proxy = interface.WithdrawalContractProxy(proxy)
    if (proxy.proxy_getAdmin() != contracts.voting.address):
        raise Exception('withdrawal_contract is not in a valid state')

    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b'')


def encode_oracle_upgrade_consensus(proxy: any, consensus_version: int) -> Tuple[str, str]:
    oracle = interface.BaseOracle(proxy)
    return oracle.address, oracle.setConsensusVersion.encode_input(consensus_version)


def create_tw_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[any]]:
    """
        Triggerable withdrawals voting baking and sending.

        Contains next steps:
            --- VEB
            1. Update VEBO implementation
            2. Call finalizeUpgrade_v2 on VEBO
            3. Grant VEBO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            4. Bump VEBO consensus version to `4`
            5. Revoke VEBO MANAGE_CONSENSUS_VERSION_ROLE from AGENT
            6. Grant VEB DIRECT_EXIT_ROLE to CS Ejector
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
            18. Grant REPORT_EXITED_VALIDATORS_STATUS_ROLE to ValidatorExitVerifier
            --- NOR
            19. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo
            20. Update `NodeOperatorsRegistry` implementation
            21. Call finalizeUpgrade_v4 on NOR
            --- sDVT
            22. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo
            23. Update `SimpleDVT` implementation
            24. Call finalizeUpgrade_v4 on sDVT
            --- Oracle configs ---
            25. Grant CONFIG_MANAGER_ROLE role to the AGENT
            26. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig
            27. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            28. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            29. Add EXIT_EVENTS_LOOKBACK_WINDOW_SLOTS variable to OracleDaemonConfig
            30. Revoke CONFIG_MANAGER_ROLE from AGENT
            --- Temp ---
            40. Add ADD_WITHDRAWAL_REQUEST_ROLE WV for Consolidation to the TEMP-DEVNET-01 (write contract)
            41. Add ADD_CONSOLIDATION_REQUEST_ROLE WV for Triggerable Withdrawal to the TEMP-DEVNET-01 (write contract)
            42. Add PAUSE_ROLE for WV to the TEMP-DEVNET-01
            43. Add DIRECT_EXIT_ROLE VEB for direct exits to the TEMP-DEVNET-01
            44. Add PAUSE_ROLE for VEB to the TEMP-DEVNET-01
            45. Add SUBMIT_REPORT_HASH_ROLE for VEB to the TEMP-DEVNET-01
            --- CSM ---
            46. Upgrade CSM implementation on proxy
            47. Upgrade CSAccounting implementation on proxy
            48. Upgrade CSFeeOracle implementation on proxy
            49. Upgrade CSFeeDistributor implementation on proxy
            50. Call `finalizeUpgradeV2(exitPenalties)` on CSM contract
            51. Call `finalizeUpgradeV2(defaultBondCurve,vettedBondCurve)` on CSAccounting contract
            52. Call `finalizeUpgradeV2(consensusVersion,strikesContract)` on CSFeeOracle contract
            53. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract
            54. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract
            55. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract
            56. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee
            57. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate
            58. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate
            59. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate
            60. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract
            61. Grant role VERIFIER_ROLE to the new instance of the Verifier contract
            62. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance
            63. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance
            64. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance
            65. Grant CSM role PAUSE_ROLE for the new GateSeal instance
            66. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance
            67. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance
            68. Revoke Burner role REQUEST_BURN_SHARES_ROLE from the CSAccounting contract
            69. Grant Burner role REQUEST_BURN_MY_STETH_ROLE to the CSAccounting contract

    """

    nor_repo = contracts.nor_app_repo.address
    simple_dvt_repo = contracts.simple_dvt_app_repo.address

    nor_uri = get_repo_uri(nor_repo)
    simple_dvt_uri = get_repo_uri(simple_dvt_repo)

    vote_descriptions, call_script_items = zip(
        (
            "1. Update VEBO implementation",
            agent_forward([
                encode_proxy_upgrade_to(contracts.validators_exit_bus_oracle, VALIDATORS_EXIT_BUS_ORACLE_IMPL)
            ])
        ),
        (
            "2. Call finalizeUpgrade_v2 on VEBO",
            (
                contracts.validators_exit_bus_oracle.address,
                contracts.validators_exit_bus_oracle.finalizeUpgrade_v2.encode_input(),
            )
        ),
        (
            "3. Grant VEBO MANAGE_CONSENSUS_VERSION_ROLE to the ${AGENT}",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            f"4. Bump VEBO consensus version to `{VEBO_CONSENSUS_VERSION}`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.validators_exit_bus_oracle, VEBO_CONSENSUS_VERSION)
            ])
        ),
        (
            "5. Revoke VEBO MANAGE_CONSENSUS_VERSION_ROLE from ${AGENT}",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            "6. Grant VEB DIRECT_EXIT_ROLE to CS Ejector",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="DIRECT_EXIT_ROLE",
                    grant_to=contracts.cs_ejector,
                )
            ])
        ),
        # (
        #     "7. Grant VEB SUBMIT_REPORT_HASH_ROLE to the AGENT (TBD",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.validators_exit_bus_oracle,
        #             role_name="MANAGE_CONSENSUS_VERSION_ROLE",
        #             revoke_from=contracts.agent,
        #         )
        #     ])
        # ),
        (
            "8. Grant VEB EXIT_REPORT_LIMIT_ROLE role to AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="EXIT_REPORT_LIMIT_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            "9. Call setExitRequestLimit on VEB",
            agent_forward([
                (
                    contracts.validators_exit_bus_oracle.address,
                    contracts.validators_exit_bus_oracle.setExitRequestLimit.encode_input(EXIT_DAILY_LIMIT, TW_DAILY_LIMIT),
                ),
            ])
        ),
        (
            "10. Revoke VEB EXIT_REPORT_LIMIT_ROLE from AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="EXIT_REPORT_LIMIT_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            "11. Update WithdrawalVault implementation",
            encode_wv_proxy_upgrade_to(contracts.withdrawal_vault, WITHDRAWAL_VAULT_IMPL)
        ),
        (
            "12. Call finalizeUpgrade_v2 on WithdrawalVault",
            (
                contracts.withdrawal_vault.address,
                contracts.withdrawal_vault.finalizeUpgrade_v2.encode_input(
                    contracts.agent,
                ),
            )
        ),
        (
            "13. Grant WithdrawalVault ADD_WITHDRAWAL_REQUEST_ROLE to the VEB",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="ADD_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.validators_exit_bus_oracle,
                )
            ])
        ),
        (
            "14. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the ${AGENT}",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            f"15. Bump AO consensus version to `{AO_CONSENSUS_VERSION}`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.accounting_oracle, AO_CONSENSUS_VERSION)
            ])
        ),
        (
            "16. Revoke MANAGE_CONSENSUS_VERSION_ROLE from AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            "17. Update SR implementation",
            agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)]),
        ),
        (
            "18. Grant REPORT_EXITED_VALIDATORS_STATUS_ROLE to ValidatorExitVerifier",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.staking_router,
                    role_name="REPORT_EXITED_VALIDATORS_STATUS_ROLE",
                    grant_to=contracts.validator_exit_verifier,
                )
            ])
        ),
        (
            "19. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo",
            add_implementation_to_nor_app_repo(NOR_VERSION, NODE_OPERATORS_REGISTRY_IMPL, nor_uri),
        ),
        (
            "20. Update `NodeOperatorsRegistry` implementation",
            update_app_implementation(NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        ),
        (
            "21. Call finalizeUpgrade_v4 on NOR",
            (
                interface.NodeOperatorsRegistry(contracts.node_operators_registry).address,
                interface.NodeOperatorsRegistry(contracts.node_operators_registry).finalizeUpgrade_v4.encode_input(
                    NOR_EXIT_DEADLINE_IN_SEC
                )
            )
        ),
        # TODO: Implement after devnet-01
        # (
        #     "22. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo",
        #     add_implementation_to_sdvt_app_repo(SDVT_VERSION, NODE_OPERATORS_REGISTRY_IMPL, simple_dvt_uri),
        # ),
        # (
        #     "23. Update `SimpleDVT` implementation",
        #     update_app_implementation(SIMPLE_DVT_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        # ),
        # (
        #     "24. Call finalizeUpgrade_v4 on sDVT",
        # (
        #     contracts.sDVT.address,
        #     contracts.withdrawal_vault.finalizeUpgrade_v4.encode_input(
        #         NOR_EXIT_DEADLINE_IN_SEC,
        #     ),
        # )
        # ),
        (
            "25. Grant CONFIG_MANAGER_ROLE role to the AGENT",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            "26. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input('NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP'),
                ),
            ])
        ),
        (
            "27. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS'),
                ),
            ])
        ),
        (
            "28. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS'),
                ),
            ])
        ),
        (
            "29. Add EXIT_EVENTS_LOOKBACK_WINDOW_SLOTS variable to OracleDaemonConfig",
            agent_forward([
                (
                    contracts.oracle_daemon_config.address,
                    contracts.oracle_daemon_config.set.encode_input('EXIT_EVENTS_LOOKBACK_WINDOW_SLOTS', EXIT_EVENTS_LOOKBACK_WINDOW_SLOTS),
                ),
            ])
        ),
        (
            "30. Revoke CONFIG_MANAGER_ROLE from AGENT",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.oracle_daemon_config,
                    role_name="CONFIG_MANAGER_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            "40. Add ADD_WITHDRAWAL_REQUEST_ROLE WV for Consolidation to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="ADD_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            "41. Add ADD_WITHDRAWAL_REQUEST_ROLE WV for Consolidation to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="ADD_CONSOLIDATION_REQUEST_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            "42. Add PAUSE_ROLE for WV to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="PAUSE_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            "43. Add DIRECT_EXIT_ROLE for WV to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="DIRECT_EXIT_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            "44. Add PAUSE_ROLE for VEB to the TEMP-DEVNET-01",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="PAUSE_ROLE",
                    grant_to=DEVNET_01_ADDRESS,
                )
            ])
        ),
        (
            "45. Add SUBMIT_REPORT_HASH_ROLE for VEB to the TEMP-DEVNET-01",
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
            "46. Upgrade CSM implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(contracts.csm, CSM_IMPL_V2_ADDRESS)
            ])
        ),
        (
            "47. Upgrade CSAccounting implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(contracts.cs_accounting, CS_ACCOUNTING_IMPL_V2_ADDRESS)
            ])
        ),
        (
            "48. Upgrade CSFeeOracle implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(contracts.cs_fee_oracle, CS_FEE_ORACLE_IMPL_V2_ADDRESS)
            ])
        ),
        (
            "49. Upgrade CSFeeDistributor implementation on proxy",
            agent_forward([
                encode_proxy_upgrade_to(contracts.cs_fee_distributor, CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS)
            ])
        ),
        (
            "50. Call `finalizeUpgradeV2(exitPenalties)` on CSM contract",
            (
                contracts.csm.address,
                contracts.csm.finalizeUpgradeV2.encode_input(
                    contracts.exit_penalties,
                ),
            ),
        ),
        (
            "51. Call `finalizeUpgradeV2(defaultBondCurve,vettedBondCurve)` on CSAccounting contract",
            (
                contracts.cs_accounting.address,
                contracts.cs_accounting.finalizeUpgradeV2.encode_input(
                    CS_DEFAULT_BOND_CURVE,
                    CS_VETTED_BOND_CURVE,
                ),
            ),
        ),
        (
            "52. Call `finalizeUpgradeV2(consensusVersion,strikesContract)` on CSFeeOracle contract",
            (
                contracts.cs_fee_oracle.address,
                contracts.cs_fee_oracle.finalizeUpgradeV2.encode_input(
                    3,
                    contracts.cs_strikes,
                ),
            ),
        ),
        (
            "53. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract",
            (
                contracts.cs_fee_distributor.address,
                contracts.cs_fee_distributor.finalizeUpgradeV2.encode_input(
                    contracts.agent,
                ),
            ),
        ),
        (
            "54. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    revoke_from=contracts.csm,
                )
            ])
        ),
        (
            "55. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=contracts.csm,
                )
            ])
        ),
        (
            "56. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.cs_accounting,
                    role_name="RESET_BOND_CURVE_ROLE",
                    revoke_from=CSM_COMMITTEE_MS,
                )
            ])
        ),
        (
            "57. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=contracts.cs_permissionless_gate,
                )
            ])
        ),
        (
            "58. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="CREATE_NODE_OPERATOR_ROLE",
                    grant_to=contracts.cs_vetted_gate,
                )
                ])
        ),
        (
            "59. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.cs_accounting,
                    role_name="SET_BOND_CURVE_ROLE",
                    grant_to=contracts.cs_vetted_gate,
                )
            ])
        ),
        (
            "60. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.csm,
                    role_name="VERIFIER_ROLE",
                    revoke_from=contracts.cs_verifier,
                )
            ])
        ),
        (
            "61. Grant role VERIFIER_ROLE to the new instance of the Verifier contract",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.csm,
                    role_name="VERIFIER_ROLE",
                    grant_to=contracts.cs_verifier_v2,
                )
            ])
        ),
        # (
        #     "62. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.csm,
        #             role_name="PAUSE_ROLE",
        #             revoke_from=CS_GATE_SEAL_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     "63. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.cs_accounting,
        #             role_name="PAUSE_ROLE",
        #             revoke_from=CS_GATE_SEAL_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     "64. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.cs_fee_oracle,
        #             role_name="PAUSE_ROLE",
        #             revoke_from=CS_GATE_SEAL_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     "65. Grant CSM role PAUSE_ROLE for the new GateSeal instance",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.csm,
        #             role_name="PAUSE_ROLE",
        #             grant_to=CS_GATE_SEAL_V2_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     "66. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.cs_accounting,
        #             role_name="PAUSE_ROLE",
        #             grant_to=CS_GATE_SEAL_V2_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     "67. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.cs_fee_oracle,
        #             role_name="PAUSE_ROLE",
        #             grant_to=CS_GATE_SEAL_V2_ADDRESS,
        #         )
        #     ])
        # ),
        (
            "68. Revoke Burner role REQUEST_BURN_SHARES_ROLE from the CSAccounting contract",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.burner,
                    role_name="REQUEST_BURN_SHARES_ROLE",
                    revoke_from=contracts.cs_accounting,
                )
            ])
        ),
        (
            "69. Grant Burner role REQUEST_BURN_MY_STETH_ROLE to the CSAccounting contract",
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

    tx_params = {
        "from": get_deployer_account(),
        "priority_fee": get_priority_fee(),
    }

    vote_id, _ = create_tw_vote(tx_params=tx_params, silent=True)

    if vote_id:
        print(f'Vote [{vote_id}] created.')
