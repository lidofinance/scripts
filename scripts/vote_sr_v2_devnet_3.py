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
13. Update AO implementation to ${ACCOUNTING_ORACLE_IMPL}`
14. Finalize AO upgrade and set consensus version to ${AO_CONSENSUS_VERSION}`
15. Grant manage consensus role to agent ${AGENT}`
16. Update VEBO consensus version to ${VEBO_CONSENSUS_VERSION}`
17. Revoke manage consensus role from agent ${AGENT}

CSM

20. Add staking module
21. Grant request burn role to CSAccounting contract
22. Grant resume role to agent
23. Resume staking module
24. Revoke resume role from agent
25. Update initial epoch
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
)
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
    create_permissions_for_overloaded_method,
    remove_evmscript_factory,
)
from utils.kernel import update_app_implementation
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward

# SR

## Easy track
# OLD_TARGET_LIMIT__FACTORY = "0x41CF3DbDc939c5115823Fba1432c4EC5E7bD226C"
# !!!! that is locally deployed factory address, before run set contract address here
# NEW_TARGET_LIMIT_FACTORY = "0x8a6E9a8E0bB561f8cdAb1619ECc4585aaF126D73"

## Curated module
nor_uri = "0x697066733a516d54346a64693146684d454b5576575351316877786e33365748394b6a656743755a7441684a6b6368526b7a70"
CURATED_PRIORITY_EXIT_SHARE_THRESHOLDS = 10_000
CURATED_MAX_DEPOSITS_PER_BLOCK = 150
CURATED_MIN_DEPOSIT_BLOCK_DISTANCES = 25
NOR_VERSION_REPO = ["2", "0", "0"]

### RewardDistributionState
DISTRIBUTED = 2

## SDVT module
sdvt_uri = "0x697066733a516d615353756a484347636e4675657441504777565735426567614d42766e355343736769334c5366767261536f"
SDVT_PRIORITY_EXIT_SHARE_THRESHOLDS = 10_000
SDVT_MAX_DEPOSITS_PER_BLOCK = 150
SDVT_MIN_DEPOSIT_BLOCK_DISTANCES = 25
SDVT_VERSION_REPO = ["2", "0", "0"]

## SR
PRIORITY_EXIT_SHARE_THRESHOLDS_BP = [CURATED_PRIORITY_EXIT_SHARE_THRESHOLDS, SDVT_PRIORITY_EXIT_SHARE_THRESHOLDS]
MAX_DEPOSITS_PER_BLOCK = [CURATED_MAX_DEPOSITS_PER_BLOCK, SDVT_MAX_DEPOSITS_PER_BLOCK]
MIN_DEPOSIT_BLOCK_DISTANCES = [CURATED_MIN_DEPOSIT_BLOCK_DISTANCES, SDVT_MIN_DEPOSIT_BLOCK_DISTANCES]

## Accounting oracle
AO_CONSENSUS_VERSION = 2
## Vebo
VEBO_CONSENSUS_VERSION = 2

# CSM
## Easy track
# !!!! that is locally deployed factory address, before run set contract address here
# EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY = "0x2963ff0196a901ec3F56d7531e7C4Ce8F226462B"

## Parameters
CS_MODULE_NAME = "Community Staking"
CS_STAKE_SHARE_LIMIT = 100
CS_PRIORITY_EXIT_SHARE_THRESHOLD = 100
CS_STAKING_MODULE_FEE = 600
CS_TREASURY_FEE = 400
CS_MAX_DEPOSITS_PER_BLOCK = 30
CS_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CS_ORACLE_INITIAL_EPOCH = 58050

description = """
Proposal to support SR 2.0 and CSM Module
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
            add_implementation_to_nor_app_repo(NOR_VERSION_REPO, NODE_OPERATORS_REGISTRY_IMPL, nor_uri),
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
            add_implementation_to_sdvt_app_repo(SDVT_VERSION_REPO, NODE_OPERATORS_REGISTRY_IMPL, simple_dvt_uri),
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
            "13. Update AO implementation to ${ACCOUNTING_ORACLE_IMPL}",
            agent_forward([encode_ao_proxy_update(ACCOUNTING_ORACLE_IMPL)]),
        ),
        (
            "14. Finalize AO upgrade and set consensus version to ${AO_CONSENSUS_VERSION}",
            encode_ao_finalize(),
        ),
        (
            "15. Grant manage consensus role to agent ${AGENT}",
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
            "16. Update VEBO consensus version to ${VEBO_CONSENSUS_VERSION}",
            agent_forward([encode_set_consensus_version()]),
        ),
        (
            "17. Revoke manage consensus role from agent ${AGENT}",
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
        # (
        #     "18. Remove old target limit factory",
        #     remove_evmscript_factory(
        #         factory=OLD_TARGET_LIMIT__FACTORY,
        #     ),
        # ),
        # (
        #     "19. Add Target limit for SDVT factory to ET",
        #     add_evmscript_factory(
        #         factory=NEW_TARGET_LIMIT_FACTORY,
        #         permissions=(
        #             create_permissions_for_overloaded_method(
        #                 contracts.simple_dvt, "updateTargetValidatorsLimits", ("uint", "uint", "uint")
        #             )
        #         ),
        #     ),
        # ),
        #
        # CSM
        (
            "18. Add staking module",
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
            "19. Grant request burn role to CSAccounting contract",
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
            "20. Grant resume role to agent",
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
            "21. Resume staking module",
            agent_forward([(contracts.csm.address, contracts.csm.resume.encode_input())]),
        ),
        (
            "22. Revoke resume role from agent",
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
            "23. Update initial epoch",
            agent_forward(
                [
                    (
                        contracts.csm_hash_consensus.address,
                        contracts.csm_hash_consensus.updateInitialEpoch.encode_input(CS_ORACLE_INITIAL_EPOCH),
                    )
                ]
            ),
        ),
        # (
        #     "26. Add CS settle EL stealing factory to ET",
        #     add_evmscript_factory(
        #         factory=EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY,
        #         permissions=(create_permissions(contracts.csm, "settleELRewardsStealingPenalty")),
        #     ),
        # ),
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

    vote_id, _ = start_vote(tx_params=tx_params, silent=True)  # disable temporary

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
