try:
    from brownie import interface, accounts, TransactionReceipt
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


from typing import Dict, Tuple, Optional
from utils.config import contracts
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import encode_oz_grant_role
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.agent import agent_forward

from scripts.triggerable_withdrawals import variables


def encode_proxy_upgrade_to(proxy: interface.Contract, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_oracle_upgrade_consensus(proxy: interface.Contract, consensus_version: int) -> Tuple[str, str]:
    oracle = interface.BaseOracle(proxy)
    return oracle.address, oracle.setConsensusVersion.encode_input(consensus_version)


def create_tw_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """
        Triggerable withdrawals voting baking and sending.

        Contains next steps:
            1. Update VEBO implementation
            2. Update VEBO consensus version to `4`
            # 3. Call finalize upgrade on VEBO  # TODO
            4. Update WithdrawalVault implementation
            5. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEBO in WithdrawalVault
            # 6. Call finalize upgrade on WV  # TODO
            7. Update AO consensus version to `4`
    """

    vote_descriptions, call_script_items = zip(
        (
            "1. Update VEBO implementation",
            agent_forward([
                encode_proxy_upgrade_to(contracts.validator_exit_bus_oracle, contracts.VALIDATORS_EXIT_BUS_ORACLE_IMPL)
            ])
        ),
        (
            "2. Update VEBO consensu version to `4`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.validator_exit_bus_oracle, variables.VEBO_CONSENSUS_VERSION)
            ])
        ),
        # (
        #     "3. Call finalize upgrade on VEBO",
        #     agent_forward([
        #         TODO
        #     ])
        # ),
        (
            "4. Update WithdrawalVault implementation",
            agent_forward([
                encode_proxy_upgrade_to(contracts.withdrawal_vault, contracts.WITHDRAWAL_VAULT_IMPL)
            ])
        ),
        (
            "5. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEBO in WithdrawalVault",
            agent_forward([
                encode_oz_grant_role(
                    contract=contracts.WithdrawalVault,
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=contracts.validator_exit_bus_oracle,
                )
            ])
        ),
        (
            "6. Update AO consensus version to `4`",
            agent_forward([
                encode_oracle_upgrade_consensus(contracts.accounting_oracle, variables.AO_CONSENSUS_VERSION)
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
