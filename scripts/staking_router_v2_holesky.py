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
10. Update AO implementation to ${AO_IMPLEMENTATION}`,
11. Finalize AO upgrade and set consensus version to ${AO_CONSENSUS_VERSION}`,
12. Grant manage consensus role to agent ${aragonAgentAddress}`
13. Update VEBO consensus version to ${VEBO_CONSENSUS_VERSION}`
"""

import time

from typing import Dict, Tuple, Optional
from utils.config import (
    get_deployer_account,
    contracts,
    LIDO_LOCATOR,
    LIDO_LOCATOR_IMPL,
    STAKING_ROUTER,
    STAKING_ROUTER_IMPL,
    NODE_OPERATORS_REGISTRY,
    NOR_IMPL,
    ACCOUNTING_ORACLE,
    ACCOUNTING_ORACLE_IMPL,
    VALIDATORS_EXIT_BUS_ORACLE,
    AGENT,
)
from utils.permissions import encode_permission_revoke, encode_permission_grant

from utils.repo import add_implementation_to_nor_app_repo

from utils.kernel import update_app_implementation

from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from brownie.network.transaction import TransactionReceipt


PRIORITY_EXIT_SHARE_THRESHOLDS_BP = [10_000]
MAX_DEPOSITS_PER_BLOCK = [50]
MIN_DEPOSIT_BLOCK_DISTANCES = [25]
NOR_CONTENT_URI = "0x" + "00".repeat(51)  # ?
NOR_VERSION = ["2", "0", "0"]
NOR_APP_ID = "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d"
AO_CONSENSUS_VERSION = 2
VEBO_CONSENSUS_VERSION = 2


def encode_locator_proxy_update(locator_proxy_address: str, implementation: str) -> Tuple[str, str]:
    proxy = interface.LidoLocator(locator_proxy_address)
    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b"")


def encode_staking_router_proxy_update(sr_proxy_address: str, implementation: str) -> Tuple[str, str]:
    proxy = interface.StakingRouter(sr_proxy_address)
    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b"")


def encode_staking_router_finalize(sr_proxy_address: str) -> Tuple[str, str]:
    proxy = interface.StakingRouter(sr_proxy_address)
    return proxy.address, proxy.finalizeUpgrade_v2.encode_input(
        PRIORITY_EXIT_SHARE_THRESHOLDS_BP, MAX_DEPOSITS_PER_BLOCK, MIN_DEPOSIT_BLOCK_DISTANCES
    )


def encode_nor_finalize(nor_address: str) -> Tuple[str, str]:
    proxy = interface.NodeOperatorsRegistry(nor_address)
    return proxy.address, proxy.finalizeUpgrade_v3.encode_input()


def encode_ao_proxy_update(ao_proxy: str, implementation: str) -> Tuple[str, str]:
    proxy = interface.AccountingOracle(ao_proxy)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation, b"")


def encode_ao_finalize(ao: str) -> Tuple[str, str]:
    proxy = interface.AccountingOracle(ao)
    return proxy.address, proxy.finalizeUpgrade_v2.encode_input(AO_CONSENSUS_VERSION)


def encode_set_consensus_version(vebo: str) -> Tuple[str, str]:
    proxy = interface.ValidatorExitBusOracle(vebo)
    return proxy.address, proxy.setConsensusVersion(vebo)


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    call_script_items = [
        # 1)
        encode_locator_proxy_update(LIDO_LOCATOR, LIDO_LOCATOR_IMPL),
        # 2)
        encode_permission_revoke(
            contracts.staking_router, "STAKING_MODULE_PAUSE_ROLE", revoke_from=contracts.deposit_security_module
        ),
        # 3)
        encode_permission_revoke(
            contracts.staking_router, "STAKING_MODULE_RESUME_ROLE", revoke_from=contracts.deposit_security_module
        ),
        # 4)
        encode_permission_grant(
            grant_to=contracts.deposit_security_module_v3,
            target_app=contracts.staking_router,
            permission_name="STAKING_MODULE_UNVETTING_ROLE",
        ),
        # 5)
        encode_staking_router_proxy_update(STAKING_ROUTER, STAKING_ROUTER_IMPL),
        # 6)
        encode_staking_router_finalize(STAKING_ROUTER),
        # 7)
        add_implementation_to_nor_app_repo(NOR_VERSION, NOR_IMPL, NOR_CONTENT_URI),
        # 8)
        update_app_implementation(NOR_APP_ID, NOR_IMPL),
        # 9)
        encode_nor_finalize(NODE_OPERATORS_REGISTRY),
        # 10)
        encode_ao_proxy_update(ACCOUNTING_ORACLE, ACCOUNTING_ORACLE_IMPL),
        # 11)
        encode_ao_finalize(ACCOUNTING_ORACLE),
        # 12)
        encode_permission_grant(
            grant_to=VALIDATORS_EXIT_BUS_ORACLE,
            target_app=AGENT,  # ???
            permission_name="MANAGE_CONSENSUS_VERSION_ROLE",
        ),
        # 13)
        encode_set_consensus_version(VALIDATORS_EXIT_BUS_ORACLE),
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
        "10. Update AO implementation to ${AO_IMPLEMENTATION}",
        "11. Finalize AO upgrade and set consensus version to ${AO_CONSENSUS_VERSION}",
        "12. Grant manage consensus role to agent ${aragonAgentAddress}",
        "13. Update VEBO consensus version to ${VEBO_CONSENSUS_VERSION}",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    # ????
    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
