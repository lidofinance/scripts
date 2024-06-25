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
13. Publish new `Sandbox` implementation in Sandbox app APM repo
14. Update `Sandbox` implementation
15. Finalize Sandbox upgrade
16. Update AO implementation to ${ACCOUNTING_ORACLE_IMPL}`,
17. Finalize AO upgrade and set consensus version to ${AO_CONSENSUS_VERSION}`,
18. Grant manage consensus role to agent ${AGENT}`
19. Update VEBO consensus version to ${VEBO_CONSENSUS_VERSION}`
20. Revoke manage consensus role from agent ${AGENT}"

CSM

21. Grant staking module manage role to agent STAKING_MODULE_MANAGE_ROLE
22. Add staking module
23. Grant request burn role to CSAccounting contract
24. Grant resume role to agent
25. Resume staking module
26. Revoke resume role from agent
27. Update initial epoch
28. Add CS settle EL stealing factory to ET
29. Revoke STAKING_MODULE_MANAGE_ROLE from agent ${AGENT}
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
    get_priority_fee,
    contracts,
    NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
    SIMPLE_DVT_ARAGON_APP_ID,
    SANDBOX_APP_ID,
    LIDO_LOCATOR_IMPL,
    STAKING_ROUTER_IMPL,
    ACCOUNTING_ORACLE_IMPL,
    NODE_OPERATORS_REGISTRY_IMPL,
    CS_ACCOUNTING_ADDRESS,
)
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.repo import (
    add_implementation_to_nor_app_repo,
    add_implementation_to_sdvt_app_repo,
    add_implementation_to_sandbox_app_repo,
)
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.kernel import update_app_implementation
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward


# SR
PRIORITY_EXIT_SHARE_THRESHOLDS_BP = [10_000, 10_000, 10_000]
MAX_DEPOSITS_PER_BLOCK = [50, 50, 50]
MIN_DEPOSIT_BLOCK_DISTANCES = [25, 25, 25]
NOR_VERSION = ["2", "0", "0"]
SDVT_VERSION = ["2", "0", "0"]
SANDBOX_VERSION = ["2", "0", "0"]
AO_CONSENSUS_VERSION = 2
VEBO_CONSENSUS_VERSION = 2

# CSM
CS_MODULE_NAME = "CommunityStaking"
CS_STAKE_SHARE_LIMIT = 2000
CS_PRIORITY_EXIT_SHARE_THRESHOLD = 2500
CS_STAKING_MODULE_FEE = 800
CS_TREASURY_FEE = 200
CS_MAX_DEPOSITS_PER_BLOCK = 30
CS_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CS_ORACLE_INITIAL_EPOCH = 58050

description = """
_REPLACE_ME_
"""


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


def encode_sandbox_finalize() -> Tuple[str, str]:
    proxy = interface.NodeOperatorsRegistry(contracts.sandbox)
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
    sandbox_repo = contracts.sandbox_repo.address

    nor_uri = get_repo_uri(nor_repo)
    simple_dvt_uri = get_repo_uri(simple_dvt_repo)
    sandbox_uri = get_repo_uri(sandbox_repo)

    vote_desc_items, call_script_items = zip(
        #
        # SR 2
        #
        (
            "1. Update locator implementation",
            agent_forward([encode_locator_proxy_update(LIDO_LOCATOR_IMPL)]),
        ),
        (
            "2. Revoke pause role from old DSM",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.staking_router,
                        role_name="STAKING_MODULE_PAUSE_ROLE",
                        revoke_from=contracts.deposit_security_module_v2,
                    )
                ]
            ),
        ),
        (
            "3. Revoke resume role from old DSM",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.staking_router,
                        role_name="STAKING_MODULE_RESUME_ROLE",
                        revoke_from=contracts.deposit_security_module_v2,
                    )
                ]
            ),
        ),
        (
            "4. Grant unvetting role to new DSM",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.staking_router,
                        role_name="STAKING_MODULE_UNVETTING_ROLE",
                        grant_to=contracts.deposit_security_module,
                    )
                ]
            ),
        ),
        (
            "5. Update SR implementation",
            agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)]),
        ),
        (
            "6. Call finalize upgrade on SR",
            encode_staking_router_finalize(),
        ),
        (
            "7. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo",
            add_implementation_to_nor_app_repo(NOR_VERSION, NODE_OPERATORS_REGISTRY_IMPL, nor_uri),
        ),
        (
            "8. Update `NodeOperatorsRegistry` implementation",
            update_app_implementation(NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        ),
        (
            "9. Finalize NOR upgrade",
            encode_nor_finalize(),
        ),
        (
            "10. Publish new `SimpleDVT` implementation in SimpleDVT app APM repo",
            add_implementation_to_sdvt_app_repo(SDVT_VERSION, NODE_OPERATORS_REGISTRY_IMPL, simple_dvt_uri),
        ),
        (
            "11. Update `SimpleDVT` implementation",
            update_app_implementation(SIMPLE_DVT_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        ),
        (
            "12. Finalize SimpleDVT upgrade",
            encode_sdvt_finalize(),
        ),
        (
            "13. Publish new `Sandbox` implementation in Sandbox app APM repo",
            add_implementation_to_sandbox_app_repo(SANDBOX_VERSION, NODE_OPERATORS_REGISTRY_IMPL, sandbox_uri),
        ),
        (
            "14. Update `Sandbox` implementation",
            update_app_implementation(SANDBOX_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        ),
        (
            "15. Finalize Sandbox upgrade",
            encode_sandbox_finalize(),
        ),
        (
            "16. Update AO implementation to ${ACCOUNTING_ORACLE_IMPL}",
            agent_forward([encode_ao_proxy_update(ACCOUNTING_ORACLE_IMPL)]),
        ),
        (
            "17. Finalize AO upgrade and set consensus version to ${AO_CONSENSUS_VERSION}",
            encode_ao_finalize(),
        ),
        (
            "18. Grant manage consensus role to agent ${AGENT}",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "19. Update VEBO consensus version to ${VEBO_CONSENSUS_VERSION}",
            agent_forward([encode_set_consensus_version()]),
        ),
        (
            "20. Revoke manage consensus role from agent ${AGENT}",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        #
        # CSM
        #
        (
            "21. Grant staking module manage role to agent STAKING_MODULE_MANAGE_ROLE",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.staking_router,
                        role_name="STAKING_MODULE_MANAGE_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "22. Add staking module",
            agent_forward(
                [
                    (
                        contracts.staking_router.address,
                        contracts.staking_router.addStakingModule.encode_input(
                            CS_MODULE_NAME,
                            contracts.csm.address,
                            CS_STAKE_SHARE_LIMIT,
                            CS_PRIORITY_EXIT_SHARE_THRESHOLD,
                            CS_STAKING_MODULE_FEE,
                            CS_TREASURY_FEE,
                            CS_MAX_DEPOSITS_PER_BLOCK,
                            CS_MIN_DEPOSIT_BLOCK_DISTANCE,
                        ),
                    ),
                ]
            ),
        ),
        (
            "23. Grant request burn role to CSAccounting contract",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.burner,
                        role_name="REQUEST_BURN_SHARES_ROLE",
                        grant_to=CS_ACCOUNTING_ADDRESS,
                    )
                ]
            ),
        ),
        (
            "24. Grant resume role to agent",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.csm,
                        role_name="RESUME_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "25. Resume staking module",
            agent_forward([(contracts.csm.address, contracts.csm.resume.encode_input())]),
        ),
        (
            "26. Revoke resume role from agent",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.csm,
                        role_name="RESUME_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "27. Update initial epoch",
            agent_forward(
                [
                    (
                        contracts.csmHashConsensus.address,
                        contracts.csmHashConsensus.updateInitialEpoch.encode_input(CS_ORACLE_INITIAL_EPOCH),
                    )
                ]
            ),
        ),
        # (
        #     "28. Add CS settle EL stealing factory to ET",
        #      add_evmscript_factory(
        #         factory=EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY,
        #         permissions=(create_permissions(contracts.csm, "settleELRewardsStealingPenalty")),
        #     ),
        # ),
        (
            "29. Revoke STAKING_MODULE_MANAGE_ROLE from agent ${AGENT}",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.staking_router,
                        role_name="STAKING_MODULE_MANAGE_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=True) # disable IPFS description for Holesky

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(10)  # hack for waiting thread #2.
