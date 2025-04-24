from typing import Dict, Tuple, Optional
from utils.config import contracts, VALIDATORS_EXIT_BUS_ORACLE_IMPL, WITHDRAWAL_VAULT_IMPL, STAKING_ROUTER_IMPL, NODE_OPERATORS_REGISTRY_IMPL, NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, SIMPLE_DVT_ARAGON_APP_ID
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
            1. Update VEBO implementation
            2. Call finalizeUpgrade_v2 on VEBO
            3. Grant VEBO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            4. Update VEBO consensus version to `6`
            5. Revoke VEBO MANAGE_CONSENSUS_VERSION_ROLE from AGENT
            6. Update WithdrawalVault implementation
            7. Finalize WV upgrade
            8. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEBO in WithdrawalVault
            9. Grant MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            10. Update AO consensus version to `4`
            11. Update SR implementation
            12. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo
            13. Update `NodeOperatorsRegistry` implementation
            14. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo
            15. Update `SimpleDVT` implementation
            16. Revoke MANAGE_CONSENSUS_VERSION_ROLE from AGENT
            17. Add REPORT_EXITED_VALIDATORS_STATUS_ROLE to ValidatorExitVerifier
            --- Oracle configs ---
            30. Grant CONFIG_MANAGER_ROLE role to the AGENT
            31. Remove NODE_OPERATOR_NETWORK_PENETRATION_THRESHOLD_BP variable from OracleDaemonConfig
            32. Remove VALIDATOR_DELAYED_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            33. Remove VALIDATOR_DELINQUENT_TIMEOUT_IN_SLOTS variable from OracleDaemonConfig
            34. Add EXIT_EVENTS_LOOKBACK_WINDOW_SLOTS variable to OracleDaemonConfig
            35. Revoke CONFIG_MANAGER_ROLE from AGENT
            --- Temp ---
            40. Add ADD_WITHDRAWAL_REQUEST_ROLE for Consolidation to the TEMP-DEVNET-01
            41. Add ADD_CONSOLIDATION_REQUEST_ROLE for Triggerable Withdrawal to the TEMP-DEVNET-01
            42. Add DIRECT_EXIT_ROLE for direct exits to the TEMP-DEVNET-01
            43. Add PAUSE_ROLE for VEB to the TEMP-DEVNET-01
            44. Add PAUSE_ROLE for WV to the TEMP-DEVNET-01
            45. Add SUBMIT_REPORT_HASH_ROLE to the TEMP-DEVNET-01
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
            "4. Update VEBO consensus version to `6`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.validators_exit_bus_oracle, 6)
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
            "6. Update WithdrawalVault implementation",
            encode_wv_proxy_upgrade_to(contracts.withdrawal_vault, WITHDRAWAL_VAULT_IMPL)
        ),
        (
            "7. Finalize WV upgrade",
            (
                contracts.withdrawal_vault.address,
                contracts.withdrawal_vault.finalizeUpgrade_v2.encode_input(
                    contracts.agent,
                ),
            )
        ),
        (
            "8. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEBO in WithdrawalVault",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.validators_exit_bus_oracle,
                )
            ])
        ),
        (
            "9. Grant MANAGE_CONSENSUS_VERSION_ROLE to the ${AGENT}",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            "10. Update AO consensus version to `4`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.accounting_oracle, AO_CONSENSUS_VERSION)
            ])
        ),
        (
            "11. Update SR implementation",
            agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)]),
        ),
        (
            "12. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo",
            add_implementation_to_nor_app_repo(NOR_VERSION, NODE_OPERATORS_REGISTRY_IMPL, nor_uri),
        ),
        (
            "13. Update `NodeOperatorsRegistry` implementation",
            update_app_implementation(NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        ),
        # TODO: Implement after devnet-01
        # (
        #     "14. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo",
        #     add_implementation_to_sdvt_app_repo(SDVT_VERSION, NODE_OPERATORS_REGISTRY_IMPL, simple_dvt_uri),
        # ),
        # (
        #     "15. Update `SimpleDVT` implementation",
        #     update_app_implementation(SIMPLE_DVT_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        # ),
        (
            "16. Revoke MANAGE_CONSENSUS_VERSION_ROLE from ${AGENT}",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
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
