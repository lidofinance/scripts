"""
Staking Router V2
1. Update Lido locator implementation to 0x3ABc4764f0237923d52056CFba7E9AEBf87113D3
2. Revoke STAKING_MODULE_PAUSE_ROLE role on Staking Router from old Deposit Security Module
3. Revoke STAKING_MODULE_RESUME_ROLE role on Staking Router from old Deposit Security Module
4. Grant STAKING_MODULE_UNVETTING_ROLE role on Staking Router to new Deposit Security Module
5. Update Staking Router implementation to 0x89eDa99C0551d4320b56F82DDE8dF2f8D2eF81aA
6. Call finalize upgrade on Staking Router
7. Add new NodeOperatorsRegistry implementation to APM Node Operators Registry app repo
8. Update NodeOperatorsRegistry app. SetApp on Lido DAO (Kernel)
9. Finalize Node Operators Registry upgrade
10. Add new SimpleDVT implementation to SimpleDVT app Repo
11. Update SimpleDVT app. SetApp on Lido DAO (Kernel)
12. Finalize SimpleDVT upgrade
13. Update Accounting Oracle implementation to 0x0e65898527E77210fB0133D00dd4C0E86Dc29bC7
14. Finalize Accounting Oracle upgrade and set consensus version to 2
15. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle to Aragon Agent
16. Update Validator Exit Bus Oracle consensus version to 2
17. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle from Aragon Agent
18. Remove old UpdateTargetValidatorLimits factory for SimpleDVT from EasyTrack
19. Add new UpdateTargetValidatorLimits factory for SimpleDVT to EasyTrack

Community Staking Module
20. Add Community Staking Module 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F to Staking Router
21. Grant REQUEST_BURN_SHARES_ROLE role on Burner to CSAccounting
22. Grant RESUME_ROLE role on CSM to Aragon Agent
23. Resume Community Staking Module
24. Revoke RESUME_ROLE role on CSM from Aragon Agent
25. Update initial epoch on CSHashConsensus
26. Add CSMSettleElStealingPenalty factory to EasyTrack

Instadapp oracle rotation

27) Remove the oracle member with address 0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d from HashConsensus for AccountingOracle
28) Remove the oracle member with address 0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d from HashConsensus for ValidatorsExitBusOracle
29) Grant MANAGE_MEMBERS_AND_QUORUM_ROLE role on CSHashConsensus to Aragon Agent
30) Remove the oracle member with address 0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d from CSHashConsensus for CSFeeOracle
31) Add oracle member with address 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 to HashConsensus for AccountingOracle
32) Add oracle member with address 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 to HashConsensus for ValidatorsExitBusOracle
33) Add oracle member with address 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 to CSHashConsensus for CSFeeOracle
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
    EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY,
    CURATED_STAKING_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD,
    SIMPLE_DVT_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD,
    CS_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD,
    CURATED_STAKING_MODULE_MAX_DEPOSITS_PER_BLOCK,
    SIMPLE_DVT_MODULE_MAX_DEPOSITS_PER_BLOCK,
    CS_MODULE_MAX_DEPOSITS_PER_BLOCK,
    CURATED_STAKING_MODULE_MIN_DEPOSITS_BLOCK_DISTANCE,
    SIMPLE_DVT_MODULE_MIN_DEPOSITS_BLOCK_DISTANCE,
    CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
    AO_CONSENSUS_VERSION,
    VEBO_CONSENSUS_VERSION,
    CS_MODULE_NAME,
    CS_MODULE_TARGET_SHARE_BP,
    CS_MODULE_MODULE_FEE_BP,
    CS_MODULE_TREASURY_FEE_BP,
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
from utils.mainnet_fork import pass_and_exec_dao_vote

# SR

## Easy track
OLD_TARGET_LIMIT_FACTORY = "0x41CF3DbDc939c5115823Fba1432c4EC5E7bD226C"

## Curated module
NOR_VERSION_REPO = ["5", "0", "0"]

## SDVT module
SDVT_VERSION_REPO = ["2", "0", "0"]

## SR
PRIORITY_EXIT_SHARE_THRESHOLDS_BP = [
    CURATED_STAKING_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD,
    SIMPLE_DVT_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD,
]
MAX_DEPOSITS_PER_BLOCK = [CURATED_STAKING_MODULE_MAX_DEPOSITS_PER_BLOCK, SIMPLE_DVT_MODULE_MAX_DEPOSITS_PER_BLOCK]
MIN_DEPOSIT_BLOCK_DISTANCES = [
    CURATED_STAKING_MODULE_MIN_DEPOSITS_BLOCK_DISTANCE,
    SIMPLE_DVT_MODULE_MIN_DEPOSITS_BLOCK_DISTANCE,
]

# Oracle quorum

HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5

# CSM
## Easy track
EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY = "0xF6B6E7997338C48Ea3a8BCfa4BB64a315fDa76f4"

## Parameters
CS_ORACLE_INITIAL_EPOCH = 326715
HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM = 5

# Oracles members
old_oracle_member_to_remove = "0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d"
new_oracle_member_to_add = "0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12"


description = """
Release the Community Staking Module (CSM) for permissionless staking and upgrade the Staking Router to ensure compatibility with CSM and future modules, improving system efficiency. A detailed action plan can be found [on the research forum](https://research.lido.fi/t/staking-router-community-staking-module-upgrade-announcement/8612/6).

1. **Staking Router and related contracts upgrade** following the DAO-approved [LIP-25: Staking Router 2.0](https://snapshot.org/#/lido-snapshot.eth/proposal/0xffb4042d3bfceef33c66f78c092a76fa8e1db198559d93798cc9db3fb4d722e7) and [LIP-23: Negative rebase sanity check with a pluggable second opinion](https://snapshot.org/#/lido-snapshot.eth/proposal/0xa44f6a4dba07d7e24b0e4180025f7a9db6251046daa74d2a8fae84de0d9ce21e) designs.

2. **Add Community Staking Module** to the Staking Router. CSM follows the [approved LIP-26 design and Mainnet Release Setup](https://snapshot.org/#/lido-snapshot.eth/proposal/0xd0d7bfd68f2241524dbb14ae6fe0e8414b9fe3e0dcfc50641a8d28f0067d6693).

**Audits:**
[Staking Router 2.0 upgrade](https://github.com/lidofinance/audits/blob/main/Ackee%20Blockchain%20Lido%20Staking%20Router%20v2%20Report%2010-24.pdf), [CSM](https://github.com/lidofinance/audits/blob/main/Ackee%20Blockchain%20Lido%20Community%20Staking%20Module%20Report%2010-24.pdf) both with deployment verification by Ackee Blockchain; [Staking Router 2.0 & CSM](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20CSM%20Security%20Audit%20Report%2010-24.pdf), [Lido Oracle](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20Oracle%20Security%20Audit%20Report%2010-24.pdf) (incl. CSM Oracle) by Mixbytes;

The AccountingOracle (negative rebase parameters, pluggable second opinion) was part of Staking Router 2.0 upgrade audits and also audited separately: [Mixbytes report](https://github.com/lidofinance/audits/blob/main/Lido%20Sanity%20Checker%20Security%20Audit%20Report.pdf) and [ChainSecurity report](https://github.com/lidofinance/audits/blob/main/ChainSecurity%20Code%20Assessment%20of%20LIP-23%20Negative%20Rebase%20Checks%20Smart%20Contracts%2006-24.pdf).
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


def encode_remove_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_remove_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_remove_validators_cs_fee_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.csm_hash_consensus

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_add_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def encode_add_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def encode_add_cs_fee_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.csm_hash_consensus

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


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
            "1. Update Lido locator implementation to 0x3ABc4764f0237923d52056CFba7E9AEBf87113D3",
            agent_forward([encode_locator_proxy_update(LIDO_LOCATOR_IMPL)]),
        ),
        (
            "2. Revoke STAKING_MODULE_PAUSE_ROLE role on Staking Router from old Deposit Security Module",
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
            "3. Revoke STAKING_MODULE_RESUME_ROLE role on Staking Router from old Deposit Security Module",
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
            "4. Grant STAKING_MODULE_UNVETTING_ROLE role on Staking Router to new Deposit Security Module",
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
            "5. Update Staking Router implementation to 0x89eDa99C0551d4320b56F82DDE8dF2f8D2eF81aA",
            agent_forward([encode_staking_router_proxy_update(STAKING_ROUTER_IMPL)]),
        ),
        (
            "6. Call finalize upgrade on Staking Router",
            encode_staking_router_finalize(),
        ),
        (
            "7. Add new NodeOperatorsRegistry implementation to APM Node Operators Registry app repo",
            add_implementation_to_nor_app_repo(NOR_VERSION_REPO, NODE_OPERATORS_REGISTRY_IMPL, nor_uri),
        ),
        (
            "8. Update NodeOperatorsRegistry app. SetApp on Lido DAO (Kernel)",
            update_app_implementation(NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        ),
        (
            "9. Finalize Node Operators Registry upgrade",
            encode_nor_finalize(),
        ),
        (
            "10. Add new SimpleDVT implementation to SimpleDVT app Repo",
            add_implementation_to_sdvt_app_repo(SDVT_VERSION_REPO, NODE_OPERATORS_REGISTRY_IMPL, simple_dvt_uri),
        ),
        (
            "11. Update SimpleDVT app. SetApp on Lido DAO (Kernel)",
            update_app_implementation(SIMPLE_DVT_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL),
        ),
        (
            "12. Finalize SimpleDVT upgrade",
            encode_sdvt_finalize(),
        ),
        (
            "13. Update Accounting Oracle implementation to 0x0e65898527E77210fB0133D00dd4C0E86Dc29bC7",
            agent_forward([encode_ao_proxy_update(ACCOUNTING_ORACLE_IMPL)]),
        ),
        (
            "14. Finalize Accounting Oracle upgrade and set consensus version to 2",
            encode_ao_finalize(),
        ),
        (
            "15. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle to Aragon Agent",
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
            "16. Update Validator Exit Bus Oracle consensus version to 2",
            agent_forward([encode_set_consensus_version()]),
        ),
        (
            "17. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle from Aragon Agent",
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
        (
            "18. Remove old UpdateTargetValidatorLimits factory for SimpleDVT from EasyTrack",
            remove_evmscript_factory(
                factory=OLD_TARGET_LIMIT_FACTORY,
            ),
        ),
        (
            "19. Add new UpdateTargetValidatorLimits factory for SimpleDVT to EasyTrack",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY,
                permissions=(
                    create_permissions_for_overloaded_method(
                        contracts.simple_dvt, "updateTargetValidatorsLimits", ("uint", "uint", "uint")
                    )
                ),
            ),
        ),
        #
        # CSM
        (
            "20. Add Community Staking Module 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F to Staking Router",
            agent_forward(
                [
                    (
                        contracts.staking_router.address,
                        contracts.staking_router.addStakingModule.encode_input(
                            CS_MODULE_NAME,
                            contracts.csm.address,
                            CS_MODULE_TARGET_SHARE_BP,
                            CS_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD,
                            CS_MODULE_MODULE_FEE_BP,
                            CS_MODULE_TREASURY_FEE_BP,
                            CS_MODULE_MAX_DEPOSITS_PER_BLOCK,
                            CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
                        ),
                    ),
                ]
            ),
        ),
        (
            "21. Grant REQUEST_BURN_SHARES_ROLE role on Burner to CSAccounting",
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
            "22. Grant RESUME_ROLE role on CSM to Aragon Agent",
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
            "23. Resume Community Staking Module",
            agent_forward([(contracts.csm.address, contracts.csm.resume.encode_input())]),
        ),
        (
            "24. Revoke RESUME_ROLE role on CSM from Aragon Agent",
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
            "25. Update initial epoch on CSHashConsensus",
            agent_forward(
                [
                    (
                        contracts.csm_hash_consensus.address,
                        contracts.csm_hash_consensus.updateInitialEpoch.encode_input(CS_ORACLE_INITIAL_EPOCH),
                    )
                ]
            ),
        ),
        (
            "26. Add CSMSettleElStealingPenalty factory to EasyTrack",
            add_evmscript_factory(
                factory=EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY,
                permissions=(create_permissions(contracts.csm, "settleELRewardsStealingPenalty")),
            ),
        ),
        # Instadapp oracle rotation
        (
            "27) Remove the oracle member with address 0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d from HashConsensus for AccountingOracle",
            agent_forward(
                [
                    encode_remove_accounting_oracle_member(
                        old_oracle_member_to_remove, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    )
                ],
            ),
        ),
        (
            "28) Remove the oracle member with address 0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d from HashConsensus for ValidatorsExitBusOracle",
            agent_forward(
                [
                    encode_remove_validators_exit_bus_oracle_member(
                        old_oracle_member_to_remove, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    )
                ],
            ),
        ),
        (
            "29. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE role  on CSHashConsensus to Aragon Agent",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.csm_hash_consensus,
                        role_name="MANAGE_MEMBERS_AND_QUORUM_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "30) Remove the oracle member with address 0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d from CSHashConsensus for CSFeeOracle",
            agent_forward(
                [
                    encode_remove_validators_cs_fee_oracle_member(
                        old_oracle_member_to_remove,
                        HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM,
                    )
                ],
            ),
        ),
        (
            "31) Add oracle member with address 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 to CSHashConsensus for AccountingOracle",
            agent_forward(
                [
                    encode_add_accounting_oracle_member(
                        new_oracle_member_to_add, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    ),
                ]
            ),
        ),
        (
            "32) Add oracle member with address 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 to CSHashConsensus for ValidatorsExitBusOracle",
            agent_forward(
                [
                    encode_add_validators_exit_bus_oracle_member(
                        new_oracle_member_to_add, HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM
                    ),
                ]
            ),
        ),
        (
            "33) Add oracle member with address 0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12 to HashConsensus for ValidatorsExitBusOracle",
            agent_forward(
                [
                    encode_add_cs_fee_oracle_member(new_oracle_member_to_add, HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM),
                ]
            ),
        ),
        # (
        #     "34. Revoke MANAGE_MEMBERS_AND_QUORUM_ROLE role on CSHashConsensus from Aragon Agent",
        #     agent_forward(
        #         [
        #             encode_oz_revoke_role(
        #                 contract=contracts.csm_hash_consensus,
        #                 role_name="MANAGE_MEMBERS_AND_QUORUM_ROLE",
        #                 revoke_from=contracts.agent,
        #             )
        #         ]
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

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.


def start_and_execute_vote_on_fork():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id))
