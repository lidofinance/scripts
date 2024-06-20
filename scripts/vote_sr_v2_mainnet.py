"""
SR V2
1. Update locator implementation
2. Revoke pause role from old DSM
3. Revoke resume role from old DSM
4. Grant unvetting role to new DSM
5. Update SR implementation
6. Call finalize upgrade on SR
7. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo
8. Update `NodeOperatorsRegistry` implementation
9. Finalize NOR upgrade
10. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo
11. Update `SimpleDVT` implementation
12. Finalize SimpleDVT upgrade
13. Update AO implementation to ${ACCOUNTING_ORACLE_IMPL}`,
14. Finalize AO upgrade and set consensus version to ${AO_CONSENSUS_VERSION}`,
15. Grant manage consensus role to agent ${AGENT}`
16. Update VEBO consensus version to ${VEBO_CONSENSUS_VERSION}`
17. Revoke manage consensus role from agent ${AGENT}
"""

import time

try:
    from brownie import interface, accounts
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


from typing import Dict, Tuple, Optional
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    LIDO_LOCATOR_IMPL,
    STAKING_ROUTER_IMPL,
    NODE_OPERATORS_REGISTRY_IMPL,
    ACCOUNTING_ORACLE_IMPL,
    AGENT,
)

from utils.repo import add_implementation_to_nor_app_repo, add_implementation_to_sdvt_app_repo

from utils.kernel import update_app_implementation

from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward


PRIORITY_EXIT_SHARE_THRESHOLDS_BP = [10_000, 10_000]
MAX_DEPOSITS_PER_BLOCK = [50, 50]
MIN_DEPOSIT_BLOCK_DISTANCES = [25, 25]
NOR_VERSION = ["5", "0", "0"]
SDVT_VERSION = ["2", "0", "0"]
NOR_APP_ID = "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d"
SDVT_APP_ID = "0xe1635b63b5f7b5e545f2a637558a4029dea7905361a2f0fc28c66e9136cf86a4"
AO_CONSENSUS_VERSION = 2
VEBO_CONSENSUS_VERSION = 2


def encode_locator_proxy_update(implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(contracts.lido_locator)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_staking_router_proxy_update(implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(contracts.staking_router)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_staking_router_finalize() -> Tuple[str, str]:
    proxy = interface.StakingRouter(contracts.staking_router)
    return proxy.address, proxy.finalizeUpgrade_v2.encode_input(
        PRIORITY_EXIT_SHARE_THRESHOLDS_BP, MAX_DEPOSITS_PER_BLOCK, MIN_DEPOSIT_BLOCK_DISTANCES
    )


def encode_nor_finalize() -> Tuple[str, str]:
    proxy = interface.NodeOperatorsRegistry(contracts.node_operators_registry)
    return proxy.address, proxy.finalizeUpgrade_v3.encode_input()


def encode_sdvt_finalize() -> Tuple[str, str]:
    proxy = interface.NodeOperatorsRegistry(contracts.simple_dvt)
    return proxy.address, proxy.finalizeUpgrade_v3.encode_input()


def encode_ao_proxy_update(implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(contracts.accounting_oracle)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def encode_ao_finalize() -> Tuple[str, str]:
    proxy = interface.AccountingOracle(contracts.accounting_oracle)
    return proxy.address, proxy.finalizeUpgrade_v2.encode_input(AO_CONSENSUS_VERSION)


def encode_set_consensus_version() -> Tuple[str, str]:
    proxy = interface.ValidatorsExitBusOracle(contracts.validators_exit_bus_oracle)
    return proxy.address, proxy.setConsensusVersion.encode_input(VEBO_CONSENSUS_VERSION)


def get_repo_uri(repo_address: str) -> str:
    contract = interface.Repo(repo_address).getLatest()
    return contract["contentURI"]


def get_repo_version(repo_address: str) -> tuple[int, int, int]:
    contract = interface.Repo(repo_address).getLatest()
    return contract["semanticVersion"]


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    nor_repo = contracts.nor_app_repo.address
    simple_dvt_repo = contracts.simple_dvt_app_repo.address

    nor_uri = get_repo_uri(nor_repo)
    simple_dvt_uri = get_repo_uri(simple_dvt_repo)

    call_script_items = [
        # 1)
        agent_forward([encode_locator_proxy_update(LIDO_LOCATOR_IMPL)]),
        # 2)
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.revokeRole.encode_input(
                        # keccak256 STAKING_MODULE_PAUSE_ROLE
                        "0x00b1e70095ba5bacc3202c3db9faf1f7873186f0ed7b6c84e80c0018dcc6e38e",
                        contracts.deposit_security_module_v2,
                    ),
                )
            ]
        ),
        # 3)
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.revokeRole.encode_input(
                        # keccak256 STAKING_MODULE_RESUME_ROLE
                        "0x9a2f67efb89489040f2c48c3b2c38f719fba1276678d2ced3bd9049fb5edc6b2",
                        contracts.deposit_security_module_v2,
                    ),
                )
            ]
        ),
        # 4)
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.grantRole.encode_input(
                        # keccak256 STAKING_MODULE_UNVETTING_ROLE
                        "0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57",
                        contracts.deposit_security_module,
                    ),
                )
            ]
        ),
        # 5)
        agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)]),
        # 6)
        encode_staking_router_finalize(),
        # 7)
        add_implementation_to_nor_app_repo(NOR_VERSION, NODE_OPERATORS_REGISTRY_IMPL, nor_uri),
        # 8)
        update_app_implementation(NOR_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        # 9)
        encode_nor_finalize(),
        # 10)
        add_implementation_to_sdvt_app_repo(SDVT_VERSION, NODE_OPERATORS_REGISTRY_IMPL, simple_dvt_uri),
        # 11)
        update_app_implementation(SDVT_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        # 12)
        encode_sdvt_finalize(),
        # 13)
        agent_forward([encode_ao_proxy_update(ACCOUNTING_ORACLE_IMPL)]),
        # 14)
        encode_ao_finalize(),
        # 15)
        agent_forward(
            [
                (
                    contracts.validators_exit_bus_oracle.address,
                    contracts.validators_exit_bus_oracle.grantRole.encode_input(
                        # keccak256 MANAGE_CONSENSUS_VERSION_ROLE
                        "0xc31b1e4b732c5173dc51d519dfa432bad95550ecc4b0f9a61c2a558a2a8e4341",
                        AGENT,
                    ),
                )
            ]
        ),
        # 16)
        agent_forward([encode_set_consensus_version()]),
        # 17)
        agent_forward(
            [
                (
                    contracts.validators_exit_bus_oracle.address,
                    contracts.validators_exit_bus_oracle.revokeRole.encode_input(
                        # keccak256 MANAGE_CONSENSUS_VERSION_ROLE
                        "0xc31b1e4b732c5173dc51d519dfa432bad95550ecc4b0f9a61c2a558a2a8e4341",
                        AGENT,
                    ),
                )
            ]
        ),
    ]

    vote_desc_items = [
        "1. Update locator implementation",
        "2. Revoke pause role from old DSM",
        "3. Revoke resume role from old DSM",
        "4. Grant unvetting role to new DSM",
        "5. Update SR implementation",
        "6. Call finalize upgrade on SR",
        "7. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo",
        "8. Update `NodeOperatorsRegistry` implementation",
        "9. Finalize NOR upgrade",
        "10. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo",
        "11. Update `SimpleDVT` implementation",
        "12. Finalize SimpleDVT upgrade",
        "13. Update AO implementation to ${ACCOUNTING_ORACLE_IMPL}",
        "14. Finalize AO upgrade and set consensus version to ${AO_CONSENSUS_VERSION}",
        "15. Grant manage consensus role to agent ${AGENT}",
        "16. Update VEBO consensus version to ${VEBO_CONSENSUS_VERSION}",
        "17. Revoke manage consensus role from agent ${AGENT}",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    print(f"tx = {tx_params}")

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
