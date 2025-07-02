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
--- WV
9. Update WithdrawalVault implementation
10. Call finalizeUpgrade_v2() on WithdrawalVault
--- AO
11. Update Accounting Oracle implementation
12. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
13. Bump AO consensus version to `4`
14. Revoke AO MANAGE_CONSENSUS_VERSION_ROLE from the AGENT
--- SR
15. Update SR implementation
16. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitVerifier
17. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG
--- NOR
18. Grant APP_MANAGER_ROLE role to the AGENT on Kernel
19. Update `NodeOperatorsRegistry` implementation
20. Call finalizeUpgrade_v4 on NOR
--- sDVT
21. Update `SimpleDVT` implementation
22. Call finalizeUpgrade_v4 on sDVT
23. Revoke APP_MANAGER_ROLE role from the AGENT on Kernel
--- Oracle configs ---
24. Grant CONFIG_MANAGER_ROLE role to the AGENT
25. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig
26. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
27. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
28. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig
--- CSM ---
29. Upgrade CSM implementation on proxy
30. Call `finalizeUpgradeV2()` on CSM contract
31. Upgrade CSAccounting implementation on proxy
32. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract
33. Upgrade CSFeeOracle implementation on proxy
34. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract
35. Upgrade CSFeeDistributor implementation on proxy
36. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract
37. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract
38. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract
39. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee
40. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate
41. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate
42. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate
43. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract
44. Grant role VERIFIER_ROLE to the new instance of the Verifier contract
45. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance
46. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance
47. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance
48. Grant CSM role PAUSE_ROLE for the new GateSeal instance
49. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance
50. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance
51. Grant MANAGE_BOND_CURVES_ROLE to the AGENT
52. Add Identified Community Stakers Gate Bond Curve
53. Revoke MANAGE_BOND_CURVES_ROLE from the AGENT
54. Increase CSM share in Staking Router from 15% to 20%
55. Add CSSetVettedGateTree factory to EasyTrack with permissions
"""
import time

from typing import TYPE_CHECKING, Any, Dict
from typing import Tuple, Optional, Sequence
from brownie import interface, web3, convert, ZERO_ADDRESS  # type: ignore
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
from utils.vote_item_builder import VoteAction, build_executable_vote_items
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

EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS = 7200

NOR_EXIT_DEADLINE_IN_SEC = 30 * 60

# CSM
CS_MODULE_NEW_TARGET_SHARE_BP = 2000  # 20%
CS_MODULE_NEW_PRIORITY_EXIT_THRESHOLD_BP = 3000  # 30%

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
    ([1, 2.4 * 10**18], [2, 1.3 * 10**18]),  # Default Curve
    ([1, 1.5 * 10**18], [2, 1.3 * 10**18]),  # Legacy EA Curve
]
CS_ICS_GATE_BOND_CURVE = ([1, 1.5 * 10**18], [2, 1.3 * 10**18])  # Identified Community Stakers Gate Bond Curve


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
    voting_items = [
        # --- locator
        (
            "1. Update locator implementation",
            VoteAction.agent(*encode_proxy_upgrade_to(contracts.lido_locator, LIDO_LOCATOR_IMPL))
        ),
        # --- VEB
        (
            "2. Update VEBO implementation",
            VoteAction.agent(*encode_proxy_upgrade_to(contracts.validators_exit_bus_oracle, VALIDATORS_EXIT_BUS_ORACLE_IMPL))
        ),
        (
            "3. Call finalizeUpgrade_v2 on VEBO",
            VoteAction.agent(
                contracts.validators_exit_bus_oracle.address,
                contracts.validators_exit_bus_oracle.finalizeUpgrade_v2.encode_input(600, 13000, 1, 48),
            )
        ),
        (
            "4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.validators_exit_bus_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                grant_to=contracts.agent,
            ))
        ),
        (
            "5. Bump VEBO consensus version to `4`",
            VoteAction.agent(*encode_oracle_upgrade_consensus(contracts.validators_exit_bus_oracle, VEBO_CONSENSUS_VERSION))
        ),
        (
            "6. Revoke VEBO role MANAGE_CONSENSUS_VERSION_ROLE from the AGENT",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.validators_exit_bus_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                revoke_from=contracts.agent,
            ))
        ),
        # --- Triggerable Withdrawals Gateway (TWG)
        (
            "7. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the CS Ejector",
            VoteAction.admin(*encode_oz_grant_role(
                contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                grant_to=CS_EJECTOR_ADDRESS,
            ))
        ),
        (
            "8. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEB",
            VoteAction.admin(*encode_oz_grant_role(
                contract=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
                role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                grant_to=contracts.validators_exit_bus_oracle,
            ))
        ),
        # --- WV
        (
            "9. Update WithdrawalVault implementation",
            VoteAction.agent(*encode_wv_proxy_upgrade_to(contracts.withdrawal_vault, WITHDRAWAL_VAULT_IMPL))
        ),
        (
            "10. Call finalizeUpgrade_v2 on WithdrawalVault",
            VoteAction.agent(
                contracts.withdrawal_vault.address,
                contracts.withdrawal_vault.finalizeUpgrade_v2.encode_input(),
            )
        ),
        # --- AO
        (
            "11. Update Accounting Oracle implementation",
            VoteAction.agent(*encode_proxy_upgrade_to(contracts.accounting_oracle, ACCOUNTING_ORACLE_IMPL))
        ),
        (
            "12. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.accounting_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                grant_to=contracts.agent,
            ))
        ),
        (
            "13. Bump AO consensus version to `4`",
            VoteAction.agent(*encode_oracle_upgrade_consensus(contracts.accounting_oracle, AO_CONSENSUS_VERSION))
        ),
        (
            "14. Revoke AO MANAGE_CONSENSUS_VERSION_ROLE from the AGENT",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.accounting_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                revoke_from=contracts.agent,
            ))
        ),
        # --- SR
        (
            "15. Update SR implementation",
            VoteAction.agent(*encode_staking_router_proxy_update(STAKING_ROUTER_IMPL))
        ),
        (
            "16. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitDelayVerifier",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.staking_router,
                role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                grant_to=VALIDATOR_EXIT_VERIFIER,
            ))
        ),
        (
            "17. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.staking_router,
                role_name="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE",
                grant_to=interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY),
            ))
        ),
        # --- NOR and sDVT
        (
            "18. Grant APP_MANAGER_ROLE role to the AGENT",
            VoteAction.agent(
                contracts.acl.address,
                contracts.acl.grantPermission.encode_input(
                    AGENT,
                    ARAGON_KERNEL,
                    convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE"))
                )
            )
        ),
        (
            "19. Update `NodeOperatorsRegistry` implementation",
            VoteAction.agent(
                contracts.kernel.address,
                contracts.kernel.setApp.encode_input(
                    contracts.kernel.APP_BASES_NAMESPACE(),
                    NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
                    NODE_OPERATORS_REGISTRY_IMPL
                )
            )
        ),
        (
            "20. Call finalizeUpgrade_v4 on NOR",
            VoteAction.agent(
                interface.NodeOperatorsRegistry(contracts.node_operators_registry).address,
                interface.NodeOperatorsRegistry(contracts.node_operators_registry).finalizeUpgrade_v4.encode_input(
                    NOR_EXIT_DEADLINE_IN_SEC
                )
            )
        ),
        (
            "21. Update `SDVT` implementation",
            VoteAction.agent(
                contracts.kernel.address,
                contracts.kernel.setApp.encode_input(
                    contracts.kernel.APP_BASES_NAMESPACE(),
                    SIMPLE_DVT_ARAGON_APP_ID,
                    NODE_OPERATORS_REGISTRY_IMPL
                )
            )
        ),
        (
            "22. Call finalizeUpgrade_v4 on SDVT",
            VoteAction.agent(
                interface.NodeOperatorsRegistry(contracts.simple_dvt).address,
                interface.NodeOperatorsRegistry(contracts.simple_dvt).finalizeUpgrade_v4.encode_input(
                    NOR_EXIT_DEADLINE_IN_SEC
                )
            )
        ),
        (
            "23. Revoke APP_MANAGER_ROLE role from the AGENT",
            VoteAction.agent(
                contracts.acl.address,
                contracts.acl.revokePermission.encode_input(
                    AGENT,
                    ARAGON_KERNEL,
                    convert.to_uint(web3.keccak(text="APP_MANAGER_ROLE"))
                )
            )
        ),
        # --- Oracle configs ---
        (
            "24. Grant CONFIG_MANAGER_ROLE role to the AGENT",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.oracle_daemon_config,
                role_name="CONFIG_MANAGER_ROLE",
                grant_to=contracts.agent,
            ))
        ),
        (
            "25. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig",
            VoteAction.agent(
                contracts.oracle_daemon_config.address,
                contracts.oracle_daemon_config.unset.encode_input('NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP'),
            )
        ),
        (
            "26. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            VoteAction.agent(
                contracts.oracle_daemon_config.address,
                contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS'),
            )
        ),
        (
            "27. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            VoteAction.agent(
                contracts.oracle_daemon_config.address,
                contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS'),
            )
        ),
        (
            "28. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig",
            VoteAction.agent(
                contracts.oracle_daemon_config.address,
                contracts.oracle_daemon_config.set.encode_input('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS', EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS),
            )
        ),
        # --- CSM
        (
            "29. Upgrade CSM implementation on proxy",
            VoteAction.agent(*encode_proxy_upgrade_to(
                contracts.csm,
                CSM_IMPL_V2_ADDRESS,
            ))
        ),
        (
            "30. Call `finalizeUpgradeV2()` on CSM contract",
            VoteAction.agent(
                contracts.csm.address,
                contracts.csm.finalizeUpgradeV2.encode_input(),
            )
        ),
        (
            "31. Upgrade CSAccounting implementation on proxy",
            VoteAction.agent(*encode_proxy_upgrade_to(
                contracts.cs_accounting,
                CS_ACCOUNTING_IMPL_V2_ADDRESS,
            ))
        ),
        (
            "32. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract",
            VoteAction.agent(
                contracts.cs_accounting.address,
                contracts.cs_accounting.finalizeUpgradeV2.encode_input(CS_CURVES),
            )
        ),
        (
            "33. Upgrade CSFeeOracle implementation on proxy",
            VoteAction.agent(*encode_proxy_upgrade_to(
                contracts.cs_fee_oracle,
                CS_FEE_ORACLE_IMPL_V2_ADDRESS,
            ))
        ),
        (
            "34. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract",
            VoteAction.agent(
                contracts.cs_fee_oracle.address,
                contracts.cs_fee_oracle.finalizeUpgradeV2.encode_input(CSM_CONSENSUS_VERSION),
            )
        ),
        (
            "35. Upgrade CSFeeDistributor implementation on proxy",
            VoteAction.agent(*encode_proxy_upgrade_to(
                contracts.cs_fee_distributor,
                CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
            ))
        ),
        (
            "36. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract",
            VoteAction.agent(
                contracts.cs_fee_distributor.address,
                contracts.cs_fee_distributor.finalizeUpgradeV2.encode_input(contracts.agent),
            )
        ),
        (
            "37. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="SET_BOND_CURVE_ROLE",
                revoke_from=contracts.csm,
            ))
        ),
        (
            "38. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="RESET_BOND_CURVE_ROLE",
                revoke_from=contracts.csm,
            ))
        ),
        (
            "39. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="RESET_BOND_CURVE_ROLE",
                revoke_from=CSM_COMMITTEE_MS,
            ))
        ),
        (
            "40. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.csm,
                role_name="CREATE_NODE_OPERATOR_ROLE",
                grant_to=CS_PERMISSIONLESS_GATE_ADDRESS,
            ))
        ),
        (
            "41. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.csm,
                role_name="CREATE_NODE_OPERATOR_ROLE",
                grant_to=CS_VETTED_GATE_ADDRESS,
            ))
        ),
        (
            "42. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.cs_accounting,
                role_name="SET_BOND_CURVE_ROLE",
                grant_to=CS_VETTED_GATE_ADDRESS,
            ))
        ),
        (
            "43. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.csm,
                role_name="VERIFIER_ROLE",
                revoke_from=contracts.cs_verifier,
            ))
        ),
        (
            "44. Grant role VERIFIER_ROLE to the new instance of the Verifier contract",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.csm,
                role_name="VERIFIER_ROLE",
                grant_to=CS_VERIFIER_V2_ADDRESS,
            ))
        ),
        (
            "45. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.csm,
                role_name="PAUSE_ROLE",
                revoke_from=CS_GATE_SEAL_ADDRESS,
            ))
        ),
        (
            "46. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="PAUSE_ROLE",
                revoke_from=CS_GATE_SEAL_ADDRESS,
            ))
        ),
        (
            "47. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.cs_fee_oracle,
                role_name="PAUSE_ROLE",
                revoke_from=CS_GATE_SEAL_ADDRESS,
            ))
        ),
        (
            "48. Grant CSM role PAUSE_ROLE for the new GateSeal instance",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.csm,
                role_name="PAUSE_ROLE",
                grant_to=CS_GATE_SEAL_V2_ADDRESS,
            ))
        ),
        (
            "49. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.cs_accounting,
                role_name="PAUSE_ROLE",
                grant_to=CS_GATE_SEAL_V2_ADDRESS,
            ))
        ),
        (
            "50. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.cs_fee_oracle,
                role_name="PAUSE_ROLE",
                grant_to=CS_GATE_SEAL_V2_ADDRESS,
            ))
        ),
        (
            "51. Grant MANAGE_BOND_CURVES_ROLE to the AGENT",
            VoteAction.agent(*encode_oz_grant_role(
                contract=contracts.cs_accounting,
                role_name="MANAGE_BOND_CURVES_ROLE",
                grant_to=contracts.agent,
            ))
        ),
        (
            "52. Add Identified Community Stakers Gate Bond Curve",
            VoteAction.agent(
                contracts.cs_accounting.address,
                contracts.cs_accounting.addBondCurve.encode_input(CS_ICS_GATE_BOND_CURVE),
            )
        ),
        (
            "53. Revoke MANAGE_BOND_CURVES_ROLE from the AGENT",
            VoteAction.agent(*encode_oz_revoke_role(
                contract=contracts.cs_accounting,
                role_name="MANAGE_BOND_CURVES_ROLE",
                revoke_from=contracts.agent,
            ))
        ),
        (
            "54. Increase CSM share in Staking Router from 15% to 20%",
            VoteAction.agent(*encode_staking_router_update_csm_module_share())
        ),
        (
            "55. Add CSSetVettedGateTree factory to EasyTrack with permissions",
            VoteAction.voting(*add_evmscript_factory(
                factory=CS_SET_VETTED_GATE_TREE_FACTORY,
                permissions=(create_permissions(interface.CSVettedGate(CS_VETTED_GATE_ADDRESS), "setTreeParams")),
            ))
        )
    ]

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

    vote_items = build_executable_vote_items(voting_items)

    assert confirm_vote_script(vote_items, silent, desc_ipfs)

    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
