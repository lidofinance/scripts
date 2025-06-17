from itertools import count
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple
from typing import Tuple, Optional, Sequence
from brownie import accounts, web3, convert,ZERO_ADDRESS
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
    ACCOUNTING_ORACLE_IMPL,
    SIMPLE_DVT_ARAGON_APP_ID,
    STAKING_ROUTER_IMPL,
    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    WITHDRAWAL_VAULT_IMPL,
    LIDO_LOCATOR_IMPL,
    VOTING,
    ARAGON_KERNEL,
    AGENT,
    contracts,
    get_deployer_account,
    get_priority_fee,
)
from utils.evm_script import encode_call_script
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.agent import dual_governance_agent_forward
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import get_deployer_account, get_priority_fee
from utils.agent import dual_governance_submit_proposal, dual_governance_agent_forward
from utils.kernel import update_app_implementation
from utils.agent import agent_forward
from tests.conftest import Helpers

try:
    from brownie import interface
except ImportError as e:
    print(f"ImportError: {e}")
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")
    if TYPE_CHECKING:
        interface: Any = ...


TW_DESCRIPTION = "Proposal to use TW in Lido protocol"

# TWG
TWG_MAX_EXIT_REQUESTS_LIMIT = 13000
TWG_EXIT_REQUESTS_PER_FRAME = 1
TWG_FRAME_DURATION = 48  # in hours

## Oracle consensus versions
AO_CONSENSUS_VERSION = 4
VEBO_CONSENSUS_VERSION = 4

EXIT_DAILY_LIMIT = 20
TW_DAILY_LIMIT = 10

EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS = 7200

NOR_EXIT_DEADLINE_IN_SEC = 30 * 60

NOR_VERSION = ["6", "0", "0"]
SDVT_VERSION = ["6", "0", "0"]

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
    print("proxy", proxy.address)
    print("proxy_getAdmin", proxy.proxy_getAdmin())
    print("contracts.voting.address", contracts.voting.address)
    # if (proxy.proxy_getAdmin() != contracts.voting.address):
    #     raise Exception('withdrawal_contract is not in a valid state')

    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b'')

def submit_proposal(call_script: Sequence[Tuple[str, str]], description: Optional[str] = "") -> Tuple[str, str]:
    proposal_calldata = []

    for call in call_script:
        (address, calldata) = call
        proposal_calldata.append((address, 0, calldata))
    print("Dual governance address:", contracts.dual_governance.address)
    return (
        contracts.dual_governance.address,
        contracts.dual_governance.submitProposal.encode_input(
            proposal_calldata, description
        ),
    )
#  vote_input = [
#         (
#             mev_boost_allowed_list.address,
#             mev_boost_allowed_list.add_relay.encode_input(*mev_boost_relay),
#         )
#     ]
# call_script_items = [submit_proposal(agent_forward(vote_input))]
# vote_desc_items = ["Add MEV-Boost relay"]
# def agent_forward(call_script: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
#     agent = contracts.agent
#     return (agent, agent.forward.encode_input(encode_call_script(call_script)))

def encode_oracle_upgrade_consensus(proxy: Any, consensus_version: int) -> Tuple[str, str]:
    oracle = interface.BaseOracle(proxy)
    return oracle.address, oracle.setConsensusVersion.encode_input(consensus_version)

def create_tw_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[Any]]:
    """
        Triggerable withdrawals voting baking and sending.

        Contains next steps:
            --- Locator
            1. Update locator implementation
            --- VEB
            2. Update VEBO implementation
            3. Call finalizeUpgrade_v2(maxValidatorsPerReport, maxExitRequestsLimit, exitsPerFrame, frameDurationInSec) on VEBO
            4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            5. Bump VEBO consensus version to `4`
            6. Grant VEB role SUBMIT_REPORT_HASH_ROLE to the ET (TBD)
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
            --- SR
            14. Update SR implementation
            15. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitVerifier
            16. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG
            --- NOR
            17. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo
            18. Update `NodeOperatorsRegistry` implementation
            19. Call finalizeUpgrade_v4 on NOR
            --- sDVT
            20. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo
            21. Update `SimpleDVT` implementation
            22. Call finalizeUpgrade_v4 on sDVT
            --- Oracle configs ---
            23. Grant CONFIG_MANAGER_ROLE role to the AGENT
            24. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig
            25. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            26. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            27. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig
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
    """

    item_idx = count(1)

    nor_repo = contracts.nor_app_repo.address
    simple_dvt_repo = contracts.simple_dvt_app_repo.address

    nor_uri = get_repo_uri(nor_repo)
    simple_dvt_uri = get_repo_uri(simple_dvt_repo)
    print(f"LIDO_LOCATOR_IMPL repo URI: {LIDO_LOCATOR_IMPL}")
    print(f"VALIDATORS_EXIT_BUS_ORACLE_IMPL: {VALIDATORS_EXIT_BUS_ORACLE_IMPL}")

    # DAOKernel Permissions Transition
    APP_MANAGER_ROLE = web3.keccak(text="APP_MANAGER_ROLE")
    print(f"APP_MANAGER_ROLE: {contracts.acl.getPermissionManager(ARAGON_KERNEL, APP_MANAGER_ROLE)}")
    # assert contracts.acl.hasPermission(AGENT, ARAGON_KERNEL, APP_MANAGER_ROLE)
    # assert not contracts.acl.hasPermission(AGENT, ARAGON_KERNEL, APP_MANAGER_ROLE)
    print("Permission manager", contracts.acl.getPermissionManager(ARAGON_KERNEL, APP_MANAGER_ROLE))
    assert contracts.acl.getPermissionManager(ARAGON_KERNEL, APP_MANAGER_ROLE) == AGENT
    assert contracts.node_operators_registry.kernel() == ARAGON_KERNEL
    assert not contracts.acl.hasPermission(VOTING, ARAGON_KERNEL, APP_MANAGER_ROLE)
    assert not contracts.acl.hasPermission(AGENT, ARAGON_KERNEL, APP_MANAGER_ROLE)
    # assert contracts.acl.getPermissionManager(ARAGON_KERNEL, APP_MANAGER_ROLE) == VOTING

    vote_descriptions, call_script_items = zip(
        # --- locator
        (
            f"1. Update locator implementation",
            encode_proxy_upgrade_to(contracts.lido_locator, LIDO_LOCATOR_IMPL)
        ),
        # --- VEB
        (
            f"2. Update VEBO implementation",
            encode_proxy_upgrade_to(contracts.validators_exit_bus_oracle, VALIDATORS_EXIT_BUS_ORACLE_IMPL)
        ),
        (
            f"3. Call finalizeUpgrade_v2 on VEBO",
            (
                contracts.validators_exit_bus_oracle.address,
                contracts.validators_exit_bus_oracle.finalizeUpgrade_v2.encode_input(600, 13000, 1, 48),
            )
        ),
        (
            f"4. Grant VEBO role MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
            encode_oz_grant_role(
                contract=contracts.validators_exit_bus_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                grant_to=contracts.agent,
            )
        ),
        (
            f"5. Bump VEBO consensus version to `{VEBO_CONSENSUS_VERSION}`",
            encode_oracle_upgrade_consensus(contracts.validators_exit_bus_oracle, VEBO_CONSENSUS_VERSION)
        ),
        # (
        #     f"6. Grant VEB role SUBMIT_REPORT_HASH_ROLE to the ET",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.validators_exit_bus_oracle,
        #             role_name="SUBMIT_REPORT_HASH_ROLE",
        #             grant_to=contracts.agent,
        #         )
        #     ])
        # ),
        # # --- Triggerable Withdrawals Gateway (TWG)
        (
            f"7. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the CS Ejector",
            encode_oz_grant_role(
                contract=contracts.triggerable_withdrawals_gateway,
                role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                grant_to=contracts.cs_ejector,
            )
        ),
        (
            f"8. Grant TWG role ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEB",
            encode_oz_grant_role(
                contract=contracts.triggerable_withdrawals_gateway,
                role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                grant_to=contracts.validators_exit_bus_oracle,
            )
        ),
        # --- WV
        (
            f"9. Update WithdrawalVault implementation",
            encode_wv_proxy_upgrade_to(contracts.withdrawal_vault, WITHDRAWAL_VAULT_IMPL)
        ),
        (
            f"10. Call finalizeUpgrade_v2 on WithdrawalVault",
            (
                contracts.withdrawal_vault.address,
                contracts.withdrawal_vault.finalizeUpgrade_v2.encode_input(),
            )
        ),
        # --- AO
        (
            f"11. Update Accounting Oracle implementation",
            encode_proxy_upgrade_to(contracts.accounting_oracle, ACCOUNTING_ORACLE_IMPL),
        ),
        (
            f"12. Grant AO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT",
            encode_oz_grant_role(
                contract=contracts.accounting_oracle,
                role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                grant_to=contracts.agent,
            )
        ),
        (
            f"13. Bump AO consensus version to `{AO_CONSENSUS_VERSION}`",
            encode_oracle_upgrade_consensus(contracts.accounting_oracle, AO_CONSENSUS_VERSION)
        ),
        # --- SR
        (
            f"14. Update SR implementation",
            encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)
        ),
        (
            f"15. Grant SR role REPORT_VALIDATOR_EXITING_STATUS_ROLE to ValidatorExitDelayVerifier",
            encode_oz_grant_role(
                contract=contracts.staking_router,
                role_name="REPORT_VALIDATOR_EXITING_STATUS_ROLE",
                grant_to=contracts.validator_exit_verifier,
            )
        ),
        (
            f"16. Grant SR role REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE to TWG",
            encode_oz_grant_role(
                contract=contracts.staking_router,
                role_name="REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE",
                grant_to=contracts.triggerable_withdrawals_gateway,
            )
        ),
        # # --- NOR and sDVT
        (
            f"18. Grant APP_MANAGER_ROLE role to the AGENT",
            (
                contracts.acl.address,
                contracts.acl.grantPermission.encode_input(
                    AGENT,
                    ARAGON_KERNEL,
                    convert.to_uint(APP_MANAGER_ROLE)
                )
            )
        ),
        (
            f"18. Update `NodeOperatorsRegistry` implementation",
            (
                contracts.kernel.address,
                contracts.kernel.setApp.encode_input(
                    contracts.kernel.APP_BASES_NAMESPACE(),
                    NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
                    NODE_OPERATORS_REGISTRY_IMPL
                )
            )
        ),
        (
            f"19. Call finalizeUpgrade_v4 on NOR",
            (
                interface.NodeOperatorsRegistry(contracts.node_operators_registry).address,
                interface.NodeOperatorsRegistry(contracts.node_operators_registry).finalizeUpgrade_v4.encode_input(
                    NOR_EXIT_DEADLINE_IN_SEC
                )
            )
        ),
         (
            f"18. Update `SDVT` implementation",
            (
                contracts.kernel.address,
                contracts.kernel.setApp.encode_input(
                    contracts.kernel.APP_BASES_NAMESPACE(),
                    SIMPLE_DVT_ARAGON_APP_ID,
                    NODE_OPERATORS_REGISTRY_IMPL
                )
            )
        ),
        (
            f"19. Call finalizeUpgrade_v4 on SDVT",
            (
                interface.NodeOperatorsRegistry(contracts.simple_dvt).address,
                interface.NodeOperatorsRegistry(contracts.simple_dvt).finalizeUpgrade_v4.encode_input(
                    NOR_EXIT_DEADLINE_IN_SEC
                )
            )
        ),
         (
            f"18. Revoke APP_MANAGER_ROLE role from the AGENT",
            (
                contracts.acl.address,
                contracts.acl.revokePermission.encode_input(
                    AGENT,
                    ARAGON_KERNEL,
                    convert.to_uint(APP_MANAGER_ROLE)
                )
            )
        ),
        # --- Oracle configs ---
        (
            f"23. Grant CONFIG_MANAGER_ROLE role to the AGENT",
            encode_oz_grant_role(
                contract=contracts.oracle_daemon_config,
                role_name="CONFIG_MANAGER_ROLE",
                grant_to=contracts.agent,
            )
        ),
        (
            f"24. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig",
            (
                contracts.oracle_daemon_config.address,
                contracts.oracle_daemon_config.unset.encode_input('NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP'),
            ),
        ),
        (
            f"25. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            (
                contracts.oracle_daemon_config.address,
                contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS'),
            ),
        ),
        (
            f"26. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig",
            (
                contracts.oracle_daemon_config.address,
                contracts.oracle_daemon_config.unset.encode_input('VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS'),
            ),
        ),
        (
            f"27. Add EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS variable to OracleDaemonConfig",
            (
                contracts.oracle_daemon_config.address,
                contracts.oracle_daemon_config.set.encode_input('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS', EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS),
            ),
        ),
        # --- CSM
        # (
        #     f"28. Upgrade CSM implementation on proxy",
        #     agent_forward([
        #         encode_proxy_upgrade_to(
        #             contracts.csm,
        #             CSM_IMPL_V2_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     f"29. Call `finalizeUpgradeV2()` on CSM contract",
        #     (
        #         contracts.csm.address,
        #         contracts.csm.finalizeUpgradeV2.encode_input(),
        #     ),
        # ),
        # (
        #     f"30. Upgrade CSAccounting implementation on proxy",
        #     agent_forward([
        #         encode_proxy_upgrade_to(
        #             contracts.cs_accounting,
        #             CS_ACCOUNTING_IMPL_V2_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     f"31. Call `finalizeUpgradeV2(bondCurves)` on CSAccounting contract",
        #     (
        #         contracts.cs_accounting.address,
        #         contracts.cs_accounting.finalizeUpgradeV2.encode_input(CS_CURVES),
        #     ),
        # ),
        # (
        #     f"32. Upgrade CSFeeOracle implementation on proxy",
        #     agent_forward([
        #         encode_proxy_upgrade_to(
        #             contracts.cs_fee_oracle,
        #             CS_FEE_ORACLE_IMPL_V2_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     f"33. Call `finalizeUpgradeV2(consensusVersion)` on CSFeeOracle contract",
        #     (
        #         contracts.cs_fee_oracle.address,
        #         contracts.cs_fee_oracle.finalizeUpgradeV2.encode_input(3),
        #     ),
        # ),
        # (
        #     f"34. Upgrade CSFeeDistributor implementation on proxy",
        #     agent_forward([
        #         encode_proxy_upgrade_to(
        #             contracts.cs_fee_distributor,
        #             CS_FEE_DISTRIBUTOR_IMPL_V2_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     f"35. Call `finalizeUpgradeV2(admin)` on CSFeeDistributor contract",
        #     (
        #         contracts.cs_fee_distributor.address,
        #         contracts.cs_fee_distributor.finalizeUpgradeV2.encode_input(contracts.agent),
        #     ),
        # ),
        # (
        #     f"36. Revoke CSAccounting role SET_BOND_CURVE_ROLE from the CSM contract",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.cs_accounting,
        #             role_name="SET_BOND_CURVE_ROLE",
        #             revoke_from=contracts.csm,
        #         )
        #     ])
        # ),
        # (
        #     f"37. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM contract",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.cs_accounting,
        #             role_name="RESET_BOND_CURVE_ROLE",
        #             revoke_from=contracts.csm,
        #         )
        #     ])
        # ),
        # (
        #     f"38. Revoke CSAccounting role RESET_BOND_CURVE_ROLE from the CSM committee",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.cs_accounting,
        #             role_name="RESET_BOND_CURVE_ROLE",
        #             revoke_from=CSM_COMMITTEE_MS,
        #         )
        #     ])
        # ),
        # (
        #     f"39. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the permissionless gate",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.csm,
        #             role_name="CREATE_NODE_OPERATOR_ROLE",
        #             grant_to=contracts.cs_permissionless_gate,
        #         )
        #     ])
        # ),
        # (
        #     f"40. Grant CSM role CREATE_NODE_OPERATOR_ROLE for the vetted gate",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.csm,
        #             role_name="CREATE_NODE_OPERATOR_ROLE",
        #             grant_to=contracts.cs_vetted_gate,
        #         )
        #     ])
        # ),
        # (
        #     f"41. Grant CSAccounting role SET_BOND_CURVE_ROLE for the vetted gate",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.cs_accounting,
        #             role_name="SET_BOND_CURVE_ROLE",
        #             grant_to=contracts.cs_vetted_gate,
        #         )
        #     ])
        # ),
        # (
        #     f"42. Revoke role VERIFIER_ROLE from the previous instance of the Verifier contract",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.csm,
        #             role_name="VERIFIER_ROLE",
        #             revoke_from=contracts.cs_verifier,
        #         )
        #     ])
        # ),
        # (
        #     f"43. Grant role VERIFIER_ROLE to the new instance of the Verifier contract",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.csm,
        #             role_name="VERIFIER_ROLE",
        #             grant_to=contracts.cs_verifier_v2,
        #         )
        #     ])
        # ),
        # (
        #     f"44. Revoke CSM role PAUSE_ROLE from the previous GateSeal instance",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.csm,
        #             role_name="PAUSE_ROLE",
        #             revoke_from=CS_GATE_SEAL_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     f"45. Revoke CSAccounting role PAUSE_ROLE from the previous GateSeal instance",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.cs_accounting,
        #             role_name="PAUSE_ROLE",
        #             revoke_from=CS_GATE_SEAL_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     f"46. Revoke CSFeeOracle role PAUSE_ROLE from the previous GateSeal instance",
        #     agent_forward([
        #         encode_oz_revoke_role(
        #             contract=contracts.cs_fee_oracle,
        #             role_name="PAUSE_ROLE",
        #             revoke_from=CS_GATE_SEAL_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     f"47. Grant CSM role PAUSE_ROLE for the new GateSeal instance",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.csm,
        #             role_name="PAUSE_ROLE",
        #             grant_to=CS_GATE_SEAL_V2_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     f"48. Grant CSAccounting role PAUSE_ROLE for the new GateSeal instance",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.cs_accounting,
        #             role_name="PAUSE_ROLE",
        #             grant_to=CS_GATE_SEAL_V2_ADDRESS,
        #         )
        #     ])
        # ),
        # (
        #     f"49. Grant CSFeeOracle role PAUSE_ROLE for the new GateSeal instance",
        #     agent_forward([
        #         encode_oz_grant_role(
        #             contract=contracts.cs_fee_oracle,
        #             role_name="PAUSE_ROLE",
        #             grant_to=CS_GATE_SEAL_V2_ADDRESS,
        #         )
        #     ])
        # ),
    )

    bake_vote_items(list(vote_descriptions), list(call_script_items))

    dg_vote = dual_governance_agent_forward(call_script_items)

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(TW_DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(TW_DESCRIPTION)

    assert confirm_vote_script({'Dualgov item': dg_vote}, silent, desc_ipfs), 'Vote not confirmed.'

    vote_id = create_vote({'Dualgov item': dg_vote}, tx_params, desc_ipfs=desc_ipfs)

    vote_tx = Helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=contracts.voting,
    )
    print("ProposalSubmitted", vote_tx.events["ProposalSubmitted"][0])
    Helpers.execute_dg_proposal(6)
    # Helpers.execute_dg_proposal(7)

    return vote_id


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
