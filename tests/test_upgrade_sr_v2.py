import pytest

from scripts.upgrade_sr_v2 import start_vote
from utils.config import LDO_HOLDER_ADDRESS_FOR_TESTS
from brownie import interface, Contract
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.repo_upgrade import validate_repo_upgrade_event, RepoUpgrade
from utils.test.event_validators.aragon import validate_app_update_event
from typing import NamedTuple
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    validate_evmscript_factory_removed_event,
    EVMScriptFactoryAdded,
)
from utils.easy_track import create_permissions, create_permissions_overloaded
from utils.test.event_validators.hash_consensus import (
    validate_hash_consensus_member_removed,
    validate_hash_consensus_member_added,
)

# Addresses that will not be changed

NODE_OPERATORS_REGISTRY = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
SIMPLE_DVT = "0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433"
LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
ACCOUNTING_ORACLE = "0x852deD011285fe67063a08005c71a85690503Cee"
VALIDATORS_EXIT_BUS_ORACLE = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
BURNER = "0xD15a672319Cf0352560eE76d9e89eAB0889046D3"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"

HASH_CONSENSUS_FOR_AO = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
HASH_CONSENSUS_FOR_VEBO = "0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"

# aragon repo
NODE_OPERATORS_REGISTRY_REPO = "0x0D97E876ad14DB2b183CFeEB8aa1A5C788eB1831"
SIMPLE_DVT_REPO = "0x2325b0a607808dE42D918DB07F925FFcCfBb2968"

# Addresses before vote
OLD_LOCATOR_IMPL_ADDRESS = "0x39aFE23cE59e8Ef196b81F0DCb165E9aD38b9463"
OLD_SR_IMPL_ADDRESS = "0xD8784e748f59Ba711fB5643191Ec3fAdD50Fb6df"
OLD_NOR_IMPL = "0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed"
OLD_SDVT_IMPL = "0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed"
OLD_ACCOUNTING_ORACLE_IMPL = "0xF3c5E0A67f32CF1dc07a8817590efa102079a1aF"
DEPOSIT_SECURITY_MODULE_V2 = "0xC77F8768774E1c9244BEed705C4354f2113CFc09"

# Addresses after vote
NEW_LIDO_LOCATOR_IMPL = "0x3ABc4764f0237923d52056CFba7E9AEBf87113D3"
NEW_STAKING_ROUTER_IMPL = "0x89eDa99C0551d4320b56F82DDE8dF2f8D2eF81aA"
NEW_NODE_OPERATORS_REGISTRY_IMPL = "0x1770044a38402e3CfCa2Fcfa0C84a093c9B42135"
NEW_SIMPLE_DVT_IMPL = "0x1770044a38402e3CfCa2Fcfa0C84a093c9B42135"
NEW_ACCOUNTING_ORACLE_IMPL = "0x0e65898527E77210fB0133D00dd4C0E86Dc29bC7"
DEPOSIT_SECURITY_MODULE_V3 = "0xffa96d84def2ea035c7ab153d8b991128e3d72fd"

# Easy track sdvt
OLD_TARGET_LIMIT_FACTORY = "0x41CF3DbDc939c5115823Fba1432c4EC5E7bD226C"
NEW_TARGET_LIMIT_FACTORY = "0x161a4552A625844c822954C5AcBac928ee0f399B"

# CSM
CSM_ADDRESS = "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F"
CS_ACCOUNTING_ADDRESS = "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da"
CS_ORACLE_HASH_CONSENSUS_ADDRESS = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"

# Staking Router parameters
NOR_URI = "0x697066733a516d54346a64693146684d454b5576575351316877786e33365748394b6a656743755a7441684a6b6368526b7a70"
CURATED_PRIORITY_EXIT_SHARE_THRESHOLDS = 10_000
CURATED_MAX_DEPOSITS_PER_BLOCK = 150
CURATED_MIN_DEPOSIT_BLOCK_DISTANCES = 25

SDVT_URI = "0x697066733a516d615353756a484347636e4675657441504777565735426567614d42766e355343736769334c5366767261536f"
SDVT_PRIORITY_EXIT_SHARE_THRESHOLDS = 444
SDVT_MAX_DEPOSITS_PER_BLOCK = 150
SDVT_MIN_DEPOSIT_BLOCK_DISTANCES = 25

# Aragon app ids
NODE_OPERATORS_REGISTRY_ARAGON_APP_ID = "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d"
SIMPLE_DVT_ARAGON_APP_ID = "0xe1635b63b5f7b5e545f2a637558a4029dea7905361a2f0fc28c66e9136cf86a4"

# Easytrack
EASYTRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"


# Accounting oracle
AO_CONSENSUS_VERSION = 2
# Vebo
VEBO_CONSENSUS_VERSION = 2

# NOR
### RewardDistributionState
DISTRIBUTED = 2

## Contract versions
SR_VERSION = 2
NOR_VERSION = 3
SDVT_VERSION = 3
AO_VERSION = 2

# CSM parameters

CS_MODULE_NAME = "Community Staking"
CS_STAKE_SHARE_LIMIT = 100
CS_PRIORITY_EXIT_SHARE_THRESHOLD = 125
CS_STAKING_MODULE_FEE = 600
CS_TREASURY_FEE = 400
CS_MAX_DEPOSITS_PER_BLOCK = 30
CS_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CS_ORACLE_INITIAL_EPOCH = 326715

# CSM steaking penalty factory
EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY = "0xF6B6E7997338C48Ea3a8BCfa4BB64a315fDa76f4"

# Roles
## SR
STAKING_MODULE_UNVETTING_ROLE = "0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57"
STAKING_MODULE_PAUSE_ROLE = "0x00b1e70095ba5bacc3202c3db9faf1f7873186f0ed7b6c84e80c0018dcc6e38e"
STAKING_MODULE_RESUME_ROLE = "0x9a2f67efb89489040f2c48c3b2c38f719fba1276678d2ced3bd9049fb5edc6b2"
MANAGE_CONSENSUS_VERSION_ROLE = "0xc31b1e4b732c5173dc51d519dfa432bad95550ecc4b0f9a61c2a558a2a8e4341"

## CSM
RESUME_ROLE = "0x2fc10cc8ae19568712f7a176fb4978616a610650813c9d05326c34abb62749c7"
REQUEST_BURN_SHARES_ROLE = "0x4be29e0e4eb91f98f709d98803cba271592782e293b84a625e025cbb40197ba8"
MANAGE_MEMBERS_AND_QUORUM_ROLE = "0x66a484cf1a3c6ef8dfd59d24824943d2853a29d96f34a01271efc55774452a51"

# Oracles members
old_oracle_member_to_remove = "0x1Ca0fEC59b86F549e1F1184d97cb47794C8Af58d"
new_oracle_member_to_add = "0x73181107c8D9ED4ce0bbeF7A0b4ccf3320C41d12"


class StakingModuleItem(NamedTuple):
    id: int
    staking_module_address: str
    name: str
    staking_module_fee: int
    stake_share_limit: int
    treasury_fee: int
    priority_exit_share_threshold: int
    max_deposits_per_block: int
    min_deposit_block_distance: int


CURATED_MODULE_BEFORE_VOTE = {
    "id": 1,
    "name": "curated-onchain-v1",
    "stakingModuleAddress": NODE_OPERATORS_REGISTRY,
    "stakingModuleFee": 500,
    "treasuryFee": 500,
    "targetShare": 10000,
    "priorityExitShareThreshold": None,
    "maxDepositsPerBlock": None,
    "minDepositBlockDistance": None,
}

SDVT_MODULE_BEFORE_VOTE = {
    "id": 2,
    "name": "SimpleDVT",
    "stakingModuleAddress": SIMPLE_DVT,
    "stakingModuleFee": 800,
    "treasuryFee": 200,
    "targetShare": 400,
    "priorityExitShareThreshold": None,
    "maxDepositsPerBlock": None,
    "minDepositBlockDistance": None,
}

CURATED_MODULE_AFTER_VOTE = CURATED_MODULE_BEFORE_VOTE.copy()
CURATED_MODULE_AFTER_VOTE.update(
    {
        "priorityExitShareThreshold": CURATED_PRIORITY_EXIT_SHARE_THRESHOLDS,
        "maxDepositsPerBlock": CURATED_MAX_DEPOSITS_PER_BLOCK,
        "minDepositBlockDistance": CURATED_MIN_DEPOSIT_BLOCK_DISTANCES,
    }
)

SDVT_MODULE_AFTER_VOTE = SDVT_MODULE_BEFORE_VOTE.copy()
SDVT_MODULE_AFTER_VOTE.update(
    {
        "priorityExitShareThreshold": SDVT_PRIORITY_EXIT_SHARE_THRESHOLDS,
        "maxDepositsPerBlock": SDVT_MAX_DEPOSITS_PER_BLOCK,
        "minDepositBlockDistance": SDVT_MIN_DEPOSIT_BLOCK_DISTANCES,
    }
)

CSM_AFTER_VOTE = {
    "id": 3,
    "name": CS_MODULE_NAME,
    "stakingModuleAddress": CSM_ADDRESS,
    "stakingModuleFee": CS_STAKING_MODULE_FEE,
    "treasuryFee": CS_TREASURY_FEE,
    "targetShare": CS_STAKE_SHARE_LIMIT,
    "priorityExitShareThreshold": CS_PRIORITY_EXIT_SHARE_THRESHOLD,
    "maxDepositsPerBlock": CS_MAX_DEPOSITS_PER_BLOCK,
    "minDepositBlockDistance": CS_MIN_DEPOSIT_BLOCK_DISTANCE,
}

OLD_SR_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "_stakingModuleId", "type": "uint256"}],
        "name": "getStakingModule",
        "outputs": [
            {
                "components": [
                    {"internalType": "uint24", "name": "id", "type": "uint24"},
                    {"internalType": "address", "name": "stakingModuleAddress", "type": "address"},
                    {"internalType": "uint16", "name": "stakingModuleFee", "type": "uint16"},
                    {"internalType": "uint16", "name": "treasuryFee", "type": "uint16"},
                    {"internalType": "uint16", "name": "stakeShareLimit", "type": "uint16"},
                    {"internalType": "uint8", "name": "status", "type": "uint8"},
                    {"internalType": "string", "name": "name", "type": "string"},
                    {"internalType": "uint64", "name": "lastDepositAt", "type": "uint64"},
                    {"internalType": "uint256", "name": "lastDepositBlock", "type": "uint256"},
                    {"internalType": "uint256", "name": "exitedValidatorsCount", "type": "uint256"},
                ],
                "internalType": "struct StakingRouter.StakingModule",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    }
]


def test_vote(
    helpers,
    accounts,
    vote_ids_from_env,
):
    sr_proxy = interface.OssifiableProxy(STAKING_ROUTER)
    locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    nor_proxy = interface.AppProxyUpgradeable(NODE_OPERATORS_REGISTRY)
    sdvt_proxy = interface.AppProxyUpgradeable(SIMPLE_DVT)
    ao_proxy = interface.OssifiableProxy(ACCOUNTING_ORACLE)
    vebo = get_vebo()
    burner = get_burner()
    csm = get_csm()
    csm_hash_consensus = get_csm_hash_consensus()
    ao = get_ao()
    simple_dvt = get_simple_dvt()
    staking_router = get_staking_router()
    easy_track = get_easy_track()

    # Before voting tests
    # 1) Locator
    # Check implementation address before vote
    check_ossifiable_proxy_impl(locator_proxy, OLD_LOCATOR_IMPL_ADDRESS)
    # DSM
    # 2)-3) Check old DSM has STAKING_MODULE_PAUSE_ROLE, STAKING_MODULE_RESUME_ROLE
    # 4) Check new DSM doesn't have STAKING_MODULE_UNVETTING_ROLE
    check_dsm_roles_before_vote()
    # SR
    # 5) Check implementation address before vote
    check_ossifiable_proxy_impl(sr_proxy, OLD_SR_IMPL_ADDRESS)
    # 6) Check Curated, SDVT modules before vote
    # id, name, stakingModuleAddress, stakingModuleFee, treasuryFee, targetShare - match corresponding values in CURATED_MODULE_BEFORE_VOTE, SDVT_MODULE_BEFORE_VOTE
    # priorityExitShareThreshold, maxDepositsPerBlock, minDepositBlockDistance - no values in SR yet
    check_module_before_vote(CURATED_MODULE_BEFORE_VOTE)
    check_module_before_vote(SDVT_MODULE_BEFORE_VOTE)
    # Version
    assert staking_router.getContractVersion() == 1
    # NOR
    # 7)-9)
    nor_app_repo = interface.Repo(NODE_OPERATORS_REGISTRY_REPO)
    # Check implementation address before vote
    assert nor_proxy.implementation() == OLD_NOR_IMPL
    nor_old_app = nor_app_repo.getLatest()
    # Check APM Node Operators Registry app repo has OLD_NOR_IMPL before vote
    # version set to 4, Content URI without changes
    assert_repo_before_vote(nor_old_app, 4, OLD_NOR_IMPL, NOR_URI)
    # SDVT
    # 10)-12)
    sdvt_app_repo = interface.Repo(SIMPLE_DVT_REPO)
    # Check implementation address before vote
    assert sdvt_proxy.implementation() == OLD_SDVT_IMPL
    sdvt_old_app = sdvt_app_repo.getLatest()
    # Check SimpleDVT app Repo repo has OLD_SDVT_IMPL before vote
    # version set to 1, Content URI without changes
    assert_repo_before_vote(sdvt_old_app, 1, OLD_SDVT_IMPL, SDVT_URI)
    # AO
    # 13) Check implementation
    check_ossifiable_proxy_impl(ao_proxy, OLD_ACCOUNTING_ORACLE_IMPL)
    # 14) Check AO contract version
    assert ao.getContractVersion() == 1
    assert ao.getConsensusVersion() == 1

    # VEBO
    # 15), 17) Aragon Agent does not have MANAGE_CONSENSUS_VERSION_ROLE role
    check_vebo_doesnt_have_manage_consensus_role()
    # 16) Check consensus version
    assert vebo.getConsensusVersion() == VEBO_CONSENSUS_VERSION - 1
    # 18)-19) simple dvt has old factory
    evm_script_factories_before = easy_track.getEVMScriptFactories()
    assert OLD_TARGET_LIMIT_FACTORY in evm_script_factories_before
    assert NEW_TARGET_LIMIT_FACTORY not in evm_script_factories_before
    # 20) Two modules in SR
    assert staking_router.getStakingModulesCount() == 2
    # 21) CSAccounting doesnt have burn role
    assert not burner.hasRole(REQUEST_BURN_SHARES_ROLE, CS_ACCOUNTING_ADDRESS)
    # 22), 24) Aragon Agent doesnt have resume role
    assert not csm.hasRole(RESUME_ROLE, AGENT)
    # 23) CSM is on pause
    assert csm.isPaused()
    # 25) epoch is set to far future epoch
    assert csm_hash_consensus.getFrameConfig()[0] == 48038396021100853
    # 26) no factory for csm yet
    assert EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY not in evm_script_factories_before

    # 27), 31) before vote old member is still in the quorum of ao hash consensus, new member is not in the quorum
    ao_hash_consensus = get_ao_hash_consensus()
    assert ao_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert not ao_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert ao_hash_consensus.getQuorum() == 5
    # 28), 32) before vote old member is still in the quorum of vebo hash consensus, new member is not in the quorum
    vebo_hash_consensus = get_vebo_hash_consensus()
    assert vebo_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert not vebo_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert vebo_hash_consensus.getQuorum() == 5

    # 29) agent doesnt have role
    assert not csm_hash_consensus.hasRole(MANAGE_MEMBERS_AND_QUORUM_ROLE, AGENT)

    # 30), 33) before vote old member is still in the quorum of cs hash consensus, new member is not in the quorum
    assert csm_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert not csm_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert csm_hash_consensus.getQuorum() == 5

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    voting = get_voting()

    vote_tx = helpers.execute_vote(accounts, vote_id, voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # 1) Locator
    # Check implementation address after vote
    check_ossifiable_proxy_impl(locator_proxy, NEW_LIDO_LOCATOR_IMPL)
    # 2)-4) DSM
    # Check old dsm doesnt have STAKING_MODULE_PAUSE_ROLE, STAKING_MODULE_RESUME_ROLE
    # Check new dsm has STAKING_MODULE_UNVETTING_ROLE
    check_dsm_roles_after_vote()
    # SR
    # 5) implementation update
    check_ossifiable_proxy_impl(sr_proxy, NEW_STAKING_ROUTER_IMPL)
    # 6)
    # finalizeUpgrade_v2
    # Store the maxDepositsPerBlock, minDepositBlockDistance, priorityExitShareThreshold for Curated, Simple DVT modules in the Staking Router's state
    check_module_after_vote(CURATED_MODULE_AFTER_VOTE)
    check_module_after_vote(SDVT_MODULE_AFTER_VOTE)
    # This also updates the contract version to 2
    assert staking_router.getContractVersion() == 2
    # NOR
    # 7)-9)
    # Check implementation address after vote
    assert nor_proxy.implementation() == NEW_NODE_OPERATORS_REGISTRY_IMPL
    # Check APM Node Operators Registry app repo has NEW_NOR_IMPL after vote
    # version set to 5, Content URI without changes
    nor_new_app = nor_app_repo.getLatest()
    assert_repo_update(nor_new_app, nor_old_app, NEW_NODE_OPERATORS_REGISTRY_IMPL, NOR_URI)
    # SDVT
    # 10)-12)
    # Check implementation address after vote
    assert sdvt_proxy.implementation() == NEW_SIMPLE_DVT_IMPL
    # Check SimpleDVT app Repo repo has NEW_SDVT_IMPL before vote
    # version set to 2, Content URI without changes
    sdvt_new_app = sdvt_app_repo.getLatest()
    assert_repo_update(sdvt_new_app, sdvt_old_app, NEW_SIMPLE_DVT_IMPL, SDVT_URI)
    # AO
    # 13)
    check_ossifiable_proxy_impl(ao_proxy, NEW_ACCOUNTING_ORACLE_IMPL)
    # 14) Check AO contract version
    assert ao.getContractVersion() == 2
    assert ao.getConsensusVersion() == 2
    # 15), 17)
    # no permission to manage consensus version on agent
    check_vebo_doesnt_have_manage_consensus_role()
    # 16)
    # VEBO consensus version
    assert vebo.getConsensusVersion() == VEBO_CONSENSUS_VERSION

    # 18)-19) simple dvt has new factory
    evm_script_factories_after = easy_track.getEVMScriptFactories()
    assert OLD_TARGET_LIMIT_FACTORY not in evm_script_factories_after
    assert NEW_TARGET_LIMIT_FACTORY in evm_script_factories_after
    # 20) Three modules in SR
    assert staking_router.getStakingModulesCount() == 3
    check_csm()
    # 21) CSAccounting has request burn role
    assert burner.hasRole(REQUEST_BURN_SHARES_ROLE, CS_ACCOUNTING_ADDRESS)
    # 22), 24) Aragon Agent doesn't have resume_role
    assert not csm.hasRole(RESUME_ROLE, AGENT)
    # 23) CSM is not on pause
    assert not csm.isPaused()
    # 25) Check epoch
    assert csm_hash_consensus.getFrameConfig()[0] == CS_ORACLE_INITIAL_EPOCH
    # 26) Factory check
    assert EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY in evm_script_factories_after

    # 27), 31) after vote old member is not in the quorum of ao hash consensus, new member is in the quorum
    assert not ao_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert ao_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert ao_hash_consensus.getQuorum() == 5
    # 28), 32) after vote old member is not in the quorum of vebo hash consensus, new member is in the quorum
    vebo_hash_consensus = get_vebo_hash_consensus()
    assert not vebo_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert vebo_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert vebo_hash_consensus.getQuorum() == 5

    # 29) agent doesnt have role
    assert csm_hash_consensus.hasRole(MANAGE_MEMBERS_AND_QUORUM_ROLE, AGENT)

    # 30), 33) after vote old member is not in the quorum of cs hash consensus, new member is in the quorum
    assert not csm_hash_consensus.getIsMember(old_oracle_member_to_remove)
    assert csm_hash_consensus.getIsMember(new_oracle_member_to_add)
    assert csm_hash_consensus.getQuorum() == 5

    # Events check
    # display_voting_events(vote_tx)
    events = group_voting_events(vote_tx)

    assert len(events) == 33

    validate_upgrade_events(events[0], NEW_LIDO_LOCATOR_IMPL)
    validate_dsm_roles_events(events)
    validate_upgrade_events(events[4], NEW_STAKING_ROUTER_IMPL)

    validate_staking_module_update(
        events[5],
        [
            StakingModuleItem(
                CURATED_MODULE_AFTER_VOTE["id"],
                CURATED_MODULE_AFTER_VOTE["stakingModuleAddress"],
                CURATED_MODULE_AFTER_VOTE["name"],
                CURATED_MODULE_AFTER_VOTE["stakingModuleFee"],
                CURATED_MODULE_AFTER_VOTE["targetShare"],
                CURATED_MODULE_AFTER_VOTE["treasuryFee"],
                CURATED_MODULE_AFTER_VOTE["priorityExitShareThreshold"],
                CURATED_MODULE_AFTER_VOTE["maxDepositsPerBlock"],
                CURATED_MODULE_AFTER_VOTE["minDepositBlockDistance"],
            ),
            StakingModuleItem(
                SDVT_MODULE_AFTER_VOTE["id"],
                SDVT_MODULE_AFTER_VOTE["stakingModuleAddress"],
                SDVT_MODULE_AFTER_VOTE["name"],
                SDVT_MODULE_AFTER_VOTE["stakingModuleFee"],
                SDVT_MODULE_AFTER_VOTE["targetShare"],
                SDVT_MODULE_AFTER_VOTE["treasuryFee"],
                SDVT_MODULE_AFTER_VOTE["priorityExitShareThreshold"],
                SDVT_MODULE_AFTER_VOTE["maxDepositsPerBlock"],
                SDVT_MODULE_AFTER_VOTE["minDepositBlockDistance"],
            ),
        ],
    )

    validate_repo_upgrade_event(events[6], RepoUpgrade(6, nor_new_app[0]))
    validate_app_update_event(events[7], NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, NEW_NODE_OPERATORS_REGISTRY_IMPL)
    validate_nor_update(events[8], NOR_VERSION)

    validate_repo_upgrade_event(events[9], RepoUpgrade(2, sdvt_new_app[0]))
    validate_app_update_event(events[10], SIMPLE_DVT_ARAGON_APP_ID, NEW_SIMPLE_DVT_IMPL)
    validate_nor_update(events[11], SDVT_VERSION)

    # AO
    validate_upgrade_events(events[12], NEW_ACCOUNTING_ORACLE_IMPL)
    validate_ao_update(events[13], AO_VERSION, AO_CONSENSUS_VERSION)

    validate_grant_role_event(events[14], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT)

    validate_vebo_consensus_version_set(events[15])

    validate_revoke_role_event(events[16], MANAGE_CONSENSUS_VERSION_ROLE, AGENT, AGENT)

    validate_evmscript_factory_removed_event(events[17], OLD_TARGET_LIMIT_FACTORY)

    simple_dvt = get_simple_dvt()

    validate_evmscript_factory_added_event(
        events[18],
        EVMScriptFactoryAdded(
            factory_addr=NEW_TARGET_LIMIT_FACTORY,
            permissions=(
                create_permissions_overloaded(simple_dvt, "updateTargetValidatorsLimits", "uint256,uint256,uint256")
            ),
        ),
    )

    validate_module_add(
        events[19],
        StakingModuleItem(
            CSM_AFTER_VOTE["id"],
            CSM_AFTER_VOTE["stakingModuleAddress"],
            CSM_AFTER_VOTE["name"],
            CSM_AFTER_VOTE["stakingModuleFee"],
            CSM_AFTER_VOTE["targetShare"],
            CSM_AFTER_VOTE["treasuryFee"],
            CSM_AFTER_VOTE["priorityExitShareThreshold"],
            CSM_AFTER_VOTE["maxDepositsPerBlock"],
            CSM_AFTER_VOTE["minDepositBlockDistance"],
        ),
    )
    validate_grant_role_event(events[20], REQUEST_BURN_SHARES_ROLE, CS_ACCOUNTING_ADDRESS, AGENT)
    validate_grant_role_event(events[21], RESUME_ROLE, AGENT, AGENT)

    validate_resume_event(events[22])
    validate_revoke_role_event(events[23], RESUME_ROLE, AGENT, AGENT)
    validate_updateInitial_epoch(events[24])

    validate_evmscript_factory_added_event(
        events[25],
        EVMScriptFactoryAdded(
            factory_addr=EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY,
            permissions=(create_permissions(csm, "settleELRewardsStealingPenalty")),
        ),
        ["LogScriptCall", "EVMScriptFactoryAdded", "ScriptResult", "ExecuteVote"],
    )

    validate_hash_consensus_member_removed(events[26], old_oracle_member_to_remove, 5, new_total_members=8)
    validate_hash_consensus_member_removed(events[27], old_oracle_member_to_remove, 5, new_total_members=8)
    validate_grant_role_event(events[28], MANAGE_MEMBERS_AND_QUORUM_ROLE, AGENT, AGENT)
    validate_hash_consensus_member_removed(
        events[29],
        old_oracle_member_to_remove,
        5,
        new_total_members=8,
    )
    validate_hash_consensus_member_added(events[30], new_oracle_member_to_add, 5, new_total_members=9)
    validate_hash_consensus_member_added(
        events[31],
        new_oracle_member_to_add,
        5,
        new_total_members=9,
    )
    validate_hash_consensus_member_added(
        events[32],
        new_oracle_member_to_add,
        5,
        new_total_members=9,
    )


def get_staking_router():
    return interface.StakingRouter(STAKING_ROUTER)


def get_deposit_security_module_v3():
    return interface.DepositSecurityModule(DEPOSIT_SECURITY_MODULE_V3)


def get_deposit_security_module_v2():
    return interface.DepositSecurityModule(DEPOSIT_SECURITY_MODULE_V2)


def get_vebo():
    return interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE)


def get_simple_dvt():
    return interface.SimpleDVT(SIMPLE_DVT)


def get_burner():
    return interface.Burner(BURNER)


def get_csm():
    return interface.CSModule(CSM_ADDRESS)


def get_voting():
    return interface.Voting(VOTING)


def get_csm_hash_consensus():
    return interface.CSHashConsensus(CS_ORACLE_HASH_CONSENSUS_ADDRESS)


def get_ao():
    return interface.AccountingOracle(ACCOUNTING_ORACLE)


def get_easy_track():
    return interface.EasyTrack(EASYTRACK)


def get_ao_hash_consensus():
    return interface.HashConsensus(HASH_CONSENSUS_FOR_AO)


def get_vebo_hash_consensus():
    return interface.HashConsensus(HASH_CONSENSUS_FOR_VEBO)


def check_ossifiable_proxy_impl(proxy, expected_impl):
    current_impl_address = proxy.proxy__getImplementation()
    assert current_impl_address == expected_impl, f"Expected {expected_impl} impl but got {current_impl_address}"


def check_dsm_roles_before_vote():
    staking_router = get_staking_router()
    deposit_security_module_v2 = get_deposit_security_module_v2()
    deposit_security_module_v3 = get_deposit_security_module_v3()
    new_dsm_has_unvet_role = staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, deposit_security_module_v3)
    assert not new_dsm_has_unvet_role

    old_dsm_has_pause_role = staking_router.hasRole(STAKING_MODULE_PAUSE_ROLE, deposit_security_module_v2)

    assert old_dsm_has_pause_role

    old_dsm_has_resume_role = staking_router.hasRole(STAKING_MODULE_RESUME_ROLE, deposit_security_module_v2)

    assert old_dsm_has_resume_role


def check_dsm_roles_after_vote():
    staking_router = get_staking_router()
    deposit_security_module_v2 = get_deposit_security_module_v2()
    deposit_security_module_v3 = get_deposit_security_module_v3()
    new_dsm_has_unvet_role = staking_router.hasRole(STAKING_MODULE_UNVETTING_ROLE, deposit_security_module_v3)
    assert new_dsm_has_unvet_role

    old_dsm_has_pause_role = staking_router.hasRole(STAKING_MODULE_PAUSE_ROLE, deposit_security_module_v2)
    assert not old_dsm_has_pause_role

    old_dsm_has_resume_role = staking_router.hasRole(STAKING_MODULE_RESUME_ROLE, deposit_security_module_v2)
    assert not old_dsm_has_resume_role


def check_vebo_doesnt_have_manage_consensus_role():
    vebo = get_vebo()
    agent_has_manage_consensus_role = vebo.hasRole(MANAGE_CONSENSUS_VERSION_ROLE, AGENT)
    assert not agent_has_manage_consensus_role


def check_module_before_vote(expected_module_data: Dict):
    staking_router = Contract.from_abi("StakingContract", STAKING_ROUTER, OLD_SR_ABI)
    module = staking_router.getStakingModule(expected_module_data["id"])
    assert module["id"] == expected_module_data["id"]
    assert module["stakingModuleFee"] == expected_module_data["stakingModuleFee"]
    assert module["treasuryFee"] == expected_module_data["treasuryFee"]
    assert module["stakeShareLimit"] == expected_module_data["targetShare"]
    assert "priorityExitShareThreshold" not in module
    assert "maxDepositsPerBlock" not in module
    assert "minDepositBlockDistance" not in module


def check_module_after_vote(expected_module_data: Dict):
    staking_router = get_staking_router()
    module = staking_router.getStakingModule(expected_module_data["id"])
    assert module["id"] == expected_module_data["id"]
    assert module["stakingModuleFee"] == expected_module_data["stakingModuleFee"]
    assert module["treasuryFee"] == expected_module_data["treasuryFee"]
    assert module["stakeShareLimit"] == expected_module_data["targetShare"]
    assert module["priorityExitShareThreshold"] == expected_module_data["priorityExitShareThreshold"]
    assert module["maxDepositsPerBlock"] == expected_module_data["maxDepositsPerBlock"]
    assert module["minDepositBlockDistance"] == expected_module_data["minDepositBlockDistance"]


def assert_repo_before_vote(old_app, version, contract_address, old_content_uri):
    assert old_app[0][0] == version
    assert old_app[2] == old_content_uri, "Content uri before vote is wrong"
    assert old_app[1] == contract_address, "New address should match"


def assert_repo_update(new_app, old_app, contract_address, old_content_uri):
    assert old_app[1] != new_app[1], "Address should change"
    assert new_app[1] == contract_address, "New address should match"
    assert new_app[0][0] == old_app[0][0] + 1, "Major version should increment"
    assert old_app[2] == new_app[2], "Content uri should not be changed"
    assert new_app[2] == old_content_uri, "Content uri should match"


# Events check


def validate_upgrade_events(events: EventDict, implementation: str):
    _events_chain = ["LogScriptCall", "LogScriptCall", "Upgraded", "ScriptResult"]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("Upgraded") == 1
    assert events["Upgraded"]["implementation"] == implementation, "Wrong proxy implementation address"


def validate_dsm_roles_events(events: list[EventDict]):
    validate_revoke_role_event(
        events[1],
        STAKING_MODULE_PAUSE_ROLE,
        DEPOSIT_SECURITY_MODULE_V2,
        AGENT,
    )
    validate_revoke_role_event(
        events[2],
        STAKING_MODULE_RESUME_ROLE,
        DEPOSIT_SECURITY_MODULE_V2,
        AGENT,
    )

    validate_grant_role_event(
        events[3],
        STAKING_MODULE_UNVETTING_ROLE,
        DEPOSIT_SECURITY_MODULE_V3,
        AGENT,
    )


def validate_staking_module_update(event: EventDict, module_items: List[StakingModuleItem]):
    assert len(module_items) == 2

    _events_chain = [
        "LogScriptCall",
        "StakingModuleShareLimitSet",
        "StakingModuleFeesSet",
        "StakingModuleMaxDepositsPerBlockSet",
        "StakingModuleMinDepositBlockDistanceSet",
        "StakingModuleShareLimitSet",
        "StakingModuleFeesSet",
        "StakingModuleMaxDepositsPerBlockSet",
        "StakingModuleMinDepositBlockDistanceSet",
        "ContractVersionSet",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("StakingModuleFeesSet") == 2
    assert event.count("StakingModuleShareLimitSet") == 2
    assert event.count("StakingModuleMinDepositBlockDistanceSet") == 2
    assert event.count("StakingModuleMaxDepositsPerBlockSet") == 2
    assert event.count("ContractVersionSet") == 1

    # curated
    assert event["StakingModuleShareLimitSet"][0]["stakingModuleId"] == module_items[0].id
    assert event["StakingModuleShareLimitSet"][0]["stakeShareLimit"] == module_items[0].stake_share_limit
    assert (
        event["StakingModuleShareLimitSet"][0]["priorityExitShareThreshold"]
        == module_items[0].priority_exit_share_threshold
    )
    assert event["StakingModuleFeesSet"][0]["stakingModuleId"] == module_items[0].id
    assert event["StakingModuleFeesSet"][0]["stakingModuleFee"] == module_items[0].staking_module_fee
    assert event["StakingModuleFeesSet"][0]["treasuryFee"] == module_items[0].treasury_fee

    assert (
        event["StakingModuleMaxDepositsPerBlockSet"][0]["maxDepositsPerBlock"] == module_items[0].max_deposits_per_block
    )

    assert (
        event["StakingModuleMinDepositBlockDistanceSet"][0]["minDepositBlockDistance"]
        == module_items[0].min_deposit_block_distance
    )

    assert event["ContractVersionSet"]["version"] == SR_VERSION

    assert event["StakingModuleShareLimitSet"][1]["stakingModuleId"] == module_items[1].id
    assert event["StakingModuleShareLimitSet"][1]["stakeShareLimit"] == module_items[1].stake_share_limit
    assert (
        event["StakingModuleShareLimitSet"][1]["priorityExitShareThreshold"]
        == module_items[1].priority_exit_share_threshold
    )
    assert event["StakingModuleFeesSet"][1]["stakingModuleId"] == module_items[1].id
    assert event["StakingModuleFeesSet"][1]["stakingModuleFee"] == module_items[1].staking_module_fee
    assert event["StakingModuleFeesSet"][1]["treasuryFee"] == module_items[1].treasury_fee

    assert (
        event["StakingModuleMaxDepositsPerBlockSet"][1]["maxDepositsPerBlock"] == module_items[1].max_deposits_per_block
    )

    assert (
        event["StakingModuleMinDepositBlockDistanceSet"][1]["minDepositBlockDistance"]
        == module_items[1].min_deposit_block_distance
    )


def validate_nor_update(event: EventDict, version):
    _events_chain = [
        "LogScriptCall",
        "ContractVersionSet",
        "RewardDistributionStateChanged",
    ]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event["ContractVersionSet"]["version"] == version
    assert event["RewardDistributionStateChanged"]["state"] == DISTRIBUTED


def validate_ao_update(event: EventDict, version, ao_consensus_version):
    _events_chain = [
        "LogScriptCall",
        "ContractVersionSet",
        "ConsensusVersionSet",
    ]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event["ContractVersionSet"]["version"] == version
    assert event["ConsensusVersionSet"]["version"] == ao_consensus_version
    assert event["ConsensusVersionSet"]["prevVersion"] == ao_consensus_version - 1


def validate_vebo_consensus_version_set(event: EventDict):
    _events_chain = ["LogScriptCall", "LogScriptCall", "ConsensusVersionSet", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event["ConsensusVersionSet"]["version"] == VEBO_CONSENSUS_VERSION


def validate_resume_event(event: EventDict):
    _events_chain = ["LogScriptCall", "LogScriptCall", "Resumed", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("Resumed") == 1


def validate_updateInitial_epoch(event: EventDict):
    _events_chain = ["LogScriptCall", "LogScriptCall", "FrameConfigSet", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event["FrameConfigSet"]["newInitialEpoch"] == CS_ORACLE_INITIAL_EPOCH


def validate_module_add(event, csm: StakingModuleItem):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "StakingRouterETHDeposited",
        "StakingModuleAdded",
        "StakingModuleShareLimitSet",
        "StakingModuleFeesSet",
        "StakingModuleMaxDepositsPerBlockSet",
        "StakingModuleMinDepositBlockDistanceSet",
        "ScriptResult",
    ]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event["StakingRouterETHDeposited"]["stakingModuleId"] == csm.id
    assert event["StakingRouterETHDeposited"]["amount"] == 0
    assert event["StakingModuleAdded"]["stakingModuleId"] == csm.id
    assert event["StakingModuleAdded"]["stakingModule"] == csm.staking_module_address
    assert event["StakingModuleAdded"]["name"] == csm.name

    assert event["StakingModuleShareLimitSet"]["stakingModuleId"] == csm.id
    assert event["StakingModuleShareLimitSet"]["stakeShareLimit"] == csm.stake_share_limit
    assert event["StakingModuleShareLimitSet"]["priorityExitShareThreshold"] == csm.priority_exit_share_threshold

    assert event["StakingModuleFeesSet"]["stakingModuleId"] == csm.id
    assert event["StakingModuleFeesSet"]["stakingModuleFee"] == csm.staking_module_fee
    assert event["StakingModuleFeesSet"]["treasuryFee"] == csm.treasury_fee

    assert event["StakingModuleMaxDepositsPerBlockSet"]["maxDepositsPerBlock"] == csm.max_deposits_per_block

    assert event["StakingModuleMinDepositBlockDistanceSet"]["minDepositBlockDistance"] == csm.min_deposit_block_distance


def check_csm():
    staking_router = get_staking_router()
    cs = staking_router.getStakingModule(3)

    assert cs["name"] == CSM_AFTER_VOTE["name"]
    assert cs["stakingModuleFee"] == CSM_AFTER_VOTE["stakingModuleFee"]
    assert cs["treasuryFee"] == CSM_AFTER_VOTE["treasuryFee"]
    assert cs["stakeShareLimit"] == CSM_AFTER_VOTE["targetShare"]
    assert cs["priorityExitShareThreshold"] == CSM_AFTER_VOTE["priorityExitShareThreshold"]
    assert cs["maxDepositsPerBlock"] == CSM_AFTER_VOTE["maxDepositsPerBlock"]
    assert cs["minDepositBlockDistance"] == CSM_AFTER_VOTE["minDepositBlockDistance"]
