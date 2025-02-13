

from typing import Dict, Tuple, Optional
from utils.config import contracts, VALIDATORS_EXIT_BUS_ORACLE_IMPL, WITHDRAWAL_VAULT_IMPL
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.agent import agent_forward

from scripts.triggerable_withdrawals import variables

try:
    from brownie import interface
except ImportError as e:
    print(f"ImportError: {e}")
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


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
            2. Grant VEBO MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            3. Update VEBO consensus version to `4`
            4. Revoke VEBO MANAGE_CONSENSUS_VERSION_ROLE from AGENT
            5. Update WithdrawalVault implementation
            6. Finalize WV upgrade
            7. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEBO in WithdrawalVault
            8. Grant MANAGE_CONSENSUS_VERSION_ROLE to the AGENT
            9. Update AO consensus version to `4`
            10. Revoke MANAGE_CONSENSUS_VERSION_ROLE from AGENT
    """

    vote_descriptions, call_script_items = zip(
        (
            "1. Update VEBO implementation",
            agent_forward([
                encode_proxy_upgrade_to(contracts.validators_exit_bus_oracle, VALIDATORS_EXIT_BUS_ORACLE_IMPL)
            ])
        ),
        (
            "2. Grant VEBO MANAGE_CONSENSUS_VERSION_ROLE to the ${AGENT}",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            "3. Update VEBO consensus version to `4`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.validators_exit_bus_oracle, 6)
            ])
        ),
        (
            "4. Revoke VEBO MANAGE_CONSENSUS_VERSION_ROLE from ${AGENT}",
            agent_forward([
                encode_oz_revoke_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    revoke_from=contracts.agent,
                )
            ])
        ),
        (
            "5. Update WithdrawalVault implementation",
            encode_wv_proxy_upgrade_to(contracts.withdrawal_vault, WITHDRAWAL_VAULT_IMPL)
        ),
        (
            "6. Finalize WV upgrade",
            (
                contracts.withdrawal_vault.address,
                contracts.withdrawal_vault.finalizeUpgrade_v2.encode_input(
                    contracts.agent,
                ),
            )
        ),
        (
            "7. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEBO in WithdrawalVault",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.withdrawal_vault,
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.validators_exit_bus_oracle,
                )
            ])
        ),
        (
            "8. Grant MANAGE_CONSENSUS_VERSION_ROLE to the ${AGENT}",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.accounting_oracle,
                    role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                    grant_to=contracts.agent,
                )
            ])
        ),
        (
            "9. Update AO consensus version to `4`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.accounting_oracle, variables.AO_CONSENSUS_VERSION)
            ])
        ),
        (
            "10. Revoke MANAGE_CONSENSUS_VERSION_ROLE from ${AGENT}",
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
        desc_ipfs = calculate_vote_ipfs_description(variables.TW_DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(variables.TW_DESCRIPTION)

    assert confirm_vote_script(vote_items, silent, desc_ipfs), 'Vote not confirmed.'

    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
