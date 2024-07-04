import pytest

from utils.config import (
    contracts,
    STAKING_ROUTER_IMPL,
    LIDO_LOCATOR_IMPL,
    NODE_OPERATORS_REGISTRY_IMPL,
    NODE_OPERATORS_REGISTRY_ARAGON_APP_ID,
    SIMPLE_DVT_ARAGON_APP_ID,
    SIMPLE_DVT_IMPL,
    ACCOUNTING_ORACLE_IMPL,
    CS_ACCOUNTING_ADDRESS,
)
from scripts.mainnet.vote_sr_v2_mainnet import start_vote
from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
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
from utils.easy_track import create_permissions


class StakingModuleItem(NamedTuple):
    id: int
    staking_module_fee: int
    stake_share_limit: int
    treasury_fee: int
    priority_exit_share_threshold: int
    max_deposits_per_block: int
    min_deposit_block_distance: int


# CSM roles
RESUME_ROLE = "0x2fc10cc8ae19568712f7a176fb4978616a610650813c9d05326c34abb62749c7"
REQUEST_BURN_SHARES_ROLE = "0x4be29e0e4eb91f98f709d98803cba271592782e293b84a625e025cbb40197ba8"

# SR roles
STAKING_MODULE_UNVETTING_ROLE = "0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57"
PAUSE_ROLE = "0x00b1e70095ba5bacc3202c3db9faf1f7873186f0ed7b6c84e80c0018dcc6e38e"
STAKING_MODULE_RESUME_ROLE = "0x9a2f67efb89489040f2c48c3b2c38f719fba1276678d2ced3bd9049fb5edc6b2"
MANAGE_CONSENSUS_VERSION_ROLE = "0xc31b1e4b732c5173dc51d519dfa432bad95550ecc4b0f9a61c2a558a2a8e4341"
OLD_LOCATOR_IMPL_ADDRESS = "0x1D920cc5bACf7eE506a271a5259f2417CaDeCE1d"
OLD_SR_IMPL_ADDRESS = "0xD8784e748f59Ba711fB5643191Ec3fAdD50Fb6df"
OLD_NOR_IMPL = "0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed"
OLD_SDVT_IMPL = "0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed"
OLD_ACCOUNTING_ORACLE_IMPL = "0xF3c5E0A67f32CF1dc07a8817590efa102079a1aF"
CURATED_MODULE_ID = 1
SIMPLE_DVT_MODULE_ID = 2
AO_CONSENSUS_VERSION = 2
VEBO_CONSENSUS_VERSION = 2

SR_VERSION = 2
NOR_VERSION = 3
DISTRIBUTED = 2
SDVT_VERSION = 3
AO_VERSION = 2

# new added fields
CURATED_PRIORITY_EXIT_SHARE_THRESHOLDS = 10000
CURATED_MAX_DEPOSITS_PER_BLOCK = 50
CURATED_MIN_DEPOSIT_BLOCK_DISTANCES = 25
SDVT_PRIORITY_EXIT_SHARE_THRESHOLDS = 10000
SDVT_MAX_DEPOSITS_PER_BLOCK = 50
SDVT_MIN_DEPOSIT_BLOCK_DISTANCES = 25

nor_uri = "0x697066733a516d54346a64693146684d454b5576575351316877786e33365748394b6a656743755a7441684a6b6368526b7a70"
sdvt_uri = "0x697066733a516d615353756a484347636e4675657441504777565735426567614d42766e355343736769334c5366767261536f"

CURATED_MODULE_BEFORE_VOTE = {
    "id": 1,
    "name": "curated-onchain-v1",
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
    "stakingModuleAddress": "0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433",
    "stakingModuleFee": 800,
    "treasuryFee": 200,
    "targetShare": 50,
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

CS_MODULE_NAME = "CommunityStaking"
CS_STAKE_SHARE_LIMIT = 2000
CS_PRIORITY_EXIT_SHARE_THRESHOLD = 2500
CS_STAKING_MODULE_FEE = 800
CS_TREASURY_FEE = 200
CS_MAX_DEPOSITS_PER_BLOCK = 30
CS_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CS_ORACLE_INITIAL_EPOCH = 58050

CSM_AFTER_VOTE = {
    "id": 4,
    "name": CS_MODULE_NAME,
    "stakingModuleFee": CS_STAKING_MODULE_FEE,
    "treasuryFee": CS_TREASURY_FEE,
    "targetShare": CS_STAKE_SHARE_LIMIT,
    "priorityExitShareThreshold": CS_PRIORITY_EXIT_SHARE_THRESHOLD,
    "maxDepositsPerBlock": CS_MAX_DEPOSITS_PER_BLOCK,
    "minDepositBlockDistance": CS_MIN_DEPOSIT_BLOCK_DISTANCE,
}

OLD_SR_ABI = bi = [
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

OLD_TARGET_LIMIT__FACTORY = "0x41CF3DbDc939c5115823Fba1432c4EC5E7bD226C"
NEW_TARGET_LIMIT_FACTORY = "0xA3b48c7b901fede641B596A4C10a4630052449A6"


def test_vote(
    helpers,
    accounts,
    vote_ids_from_env,
):
    staking_router = contracts.staking_router
    sr_proxy = interface.OssifiableProxy(contracts.staking_router)
    locator_proxy = interface.OssifiableProxy(contracts.lido_locator)
    nor_proxy = interface.AppProxyUpgradeable(contracts.node_operators_registry)
    sdvt_proxy = interface.AppProxyUpgradeable(contracts.simple_dvt)
    ao_proxy = interface.OssifiableProxy(contracts.accounting_oracle)
    vebo_proxy = interface.ValidatorsExitBusOracle(contracts.validators_exit_bus_oracle)

    assert staking_router.getStakingModulesCount() == 2

    # Before voting tests
    # locator
    check_ossifiable_proxy_impl(locator_proxy, OLD_LOCATOR_IMPL_ADDRESS)
    # DSM
    check_dsm_roles_before_vote()
    # SR
    check_ossifiable_proxy_impl(sr_proxy, OLD_SR_IMPL_ADDRESS)
    check_module_before_vote(CURATED_MODULE_BEFORE_VOTE)
    check_module_before_vote(SDVT_MODULE_BEFORE_VOTE)
    # NOR
    nor_old_app = contracts.nor_app_repo.getLatest()
    assert nor_proxy.implementation() == OLD_NOR_IMPL
    assert_repo_before_vote(nor_old_app, 4, OLD_NOR_IMPL, nor_uri)
    # SDVT
    sdvt_old_app = contracts.simple_dvt_app_repo.getLatest()
    assert sdvt_proxy.implementation() == OLD_SDVT_IMPL
    assert_repo_before_vote(sdvt_old_app, 1, OLD_SDVT_IMPL, sdvt_uri)
    # AO
    check_ossifiable_proxy_impl(ao_proxy, OLD_ACCOUNTING_ORACLE_IMPL)
    # no prermission to manage consensus version on agent
    check_manage_consensus_role()

    # VEBO consensus version
    assert vebo_proxy.getConsensusVersion() == VEBO_CONSENSUS_VERSION - 1
    assert not contracts.burner.hasRole(REQUEST_BURN_SHARES_ROLE, CS_ACCOUNTING_ADDRESS)
    assert not contracts.csm.hasRole(RESUME_ROLE, contracts.agent.address)

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    assert staking_router.getStakingModulesCount() == 3

    # locator
    check_ossifiable_proxy_impl(locator_proxy, LIDO_LOCATOR_IMPL)
    # DSM
    check_dsm_roles_after_vote()
    # SR
    check_ossifiable_proxy_impl(sr_proxy, STAKING_ROUTER_IMPL)
    check_module_after_vote(CURATED_MODULE_AFTER_VOTE)
    check_module_after_vote(SDVT_MODULE_AFTER_VOTE)
    # AO
    check_ossifiable_proxy_impl(ao_proxy, ACCOUNTING_ORACLE_IMPL)

    # no prermission to manage consensus version on agent
    check_manage_consensus_role()
    # VEBO consensus version
    assert vebo_proxy.getConsensusVersion() == VEBO_CONSENSUS_VERSION

    assert contracts.burner.hasRole(REQUEST_BURN_SHARES_ROLE, CS_ACCOUNTING_ADDRESS)
    assert not contracts.csm.hasRole(RESUME_ROLE, contracts.agent.address)

    assert contracts.csmHashConsensus.getFrameConfig()[0] == CS_ORACLE_INITIAL_EPOCH

    # Events check
    # events = group_voting_events(vote_tx)
    events = group_voting_events_from_receipt(vote_tx)

    assert len(events) == 25

    validate_upgrade_events(events[0], LIDO_LOCATOR_IMPL)
    validate_dsm_roles_events(events)
    validate_upgrade_events(events[4], STAKING_ROUTER_IMPL)

    validate_staking_module_update(
        events[5],
        [
            StakingModuleItem(
                CURATED_MODULE_AFTER_VOTE["id"],
                CURATED_MODULE_AFTER_VOTE["stakingModuleFee"],
                CURATED_MODULE_AFTER_VOTE["targetShare"],
                CURATED_MODULE_AFTER_VOTE["treasuryFee"],
                CURATED_MODULE_AFTER_VOTE["priorityExitShareThreshold"],
                CURATED_MODULE_AFTER_VOTE["maxDepositsPerBlock"],
                CURATED_MODULE_AFTER_VOTE["minDepositBlockDistance"],
            ),
            StakingModuleItem(
                SDVT_MODULE_AFTER_VOTE["id"],
                SDVT_MODULE_AFTER_VOTE["stakingModuleFee"],
                SDVT_MODULE_AFTER_VOTE["targetShare"],
                SDVT_MODULE_AFTER_VOTE["treasuryFee"],
                SDVT_MODULE_AFTER_VOTE["priorityExitShareThreshold"],
                SDVT_MODULE_AFTER_VOTE["maxDepositsPerBlock"],
                SDVT_MODULE_AFTER_VOTE["minDepositBlockDistance"],
            ),
        ],
    )

    nor_new_app = contracts.nor_app_repo.getLatest()
    assert_repo_update(nor_new_app, nor_old_app, NODE_OPERATORS_REGISTRY_IMPL, nor_uri)
    validate_repo_upgrade_event(events[6], RepoUpgrade(6, nor_new_app[0]))
    validate_app_update_event(events[7], NODE_OPERATORS_REGISTRY_ARAGON_APP_ID, NODE_OPERATORS_REGISTRY_IMPL)
    validate_nor_update(events[8], NOR_VERSION)

    sdvt_new_app = contracts.simple_dvt_app_repo.getLatest()
    assert_repo_update(sdvt_new_app, sdvt_old_app, SIMPLE_DVT_IMPL, sdvt_uri)
    validate_repo_upgrade_event(events[9], RepoUpgrade(2, sdvt_new_app[0]))
    validate_app_update_event(events[10], SIMPLE_DVT_ARAGON_APP_ID, SIMPLE_DVT_IMPL)
    validate_nor_update(events[11], SDVT_VERSION)

    # AO
    validate_upgrade_events(events[12], ACCOUNTING_ORACLE_IMPL)
    validate_ao_update(events[13], AO_VERSION, AO_CONSENSUS_VERSION)

    validate_grant_role_event(
        events[14], MANAGE_CONSENSUS_VERSION_ROLE, contracts.agent.address, contracts.agent.address
    )

    validate_vebo_consensus_version_set(events[15])

    validate_revoke_role_event(
        events[16], MANAGE_CONSENSUS_VERSION_ROLE, contracts.agent.address, contracts.agent.address
    )

    validate_evmscript_factory_removed_event(events[17], OLD_TARGET_LIMIT__FACTORY)

    validate_evmscript_factory_added_event(
        events[18],
        EVMScriptFactoryAdded(
            factory_addr=NEW_TARGET_LIMIT_FACTORY,
            permissions=(create_permissions(contracts.simple_dvt, "updateTargetValidatorsLimits")),
        ),
    )

    # 20 - add of staking module

    # validate_module_add(events[19], CSM_AFTER_VOTE)
    validate_grant_role_event(events[20], REQUEST_BURN_SHARES_ROLE, CS_ACCOUNTING_ADDRESS, contracts.agent.address)
    validate_grant_role_event(events[21], RESUME_ROLE, contracts.agent.address, contracts.agent.address)

    validate_resume_event(events[22])
    validate_revoke_role_event(events[23], RESUME_ROLE, contracts.agent.address, contracts.agent.address)
    # validate_updateInitial_epoch(events[24])

    # check_csm()


def check_ossifiable_proxy_impl(proxy, expected_impl):
    current_impl_address = proxy.proxy__getImplementation()
    assert current_impl_address == expected_impl, f"Expected {expected_impl} impl but got {current_impl_address}"


def check_dsm_roles_before_vote():
    new_dsm_doesnt_have_unvet_role = contracts.staking_router.hasRole(
        STAKING_MODULE_UNVETTING_ROLE, contracts.deposit_security_module
    )
    assert not new_dsm_doesnt_have_unvet_role

    old_dsm_has_pause_role = contracts.staking_router.hasRole(PAUSE_ROLE, contracts.deposit_security_module_v2)

    assert old_dsm_has_pause_role

    old_dsm_has_resume_role = contracts.staking_router.hasRole(
        STAKING_MODULE_RESUME_ROLE, contracts.deposit_security_module_v2
    )

    assert old_dsm_has_resume_role


def check_dsm_roles_after_vote():
    new_dsm_has_unvet_role = contracts.staking_router.hasRole(
        STAKING_MODULE_UNVETTING_ROLE, contracts.deposit_security_module
    )
    assert new_dsm_has_unvet_role

    old_dsm_doesnt_have_pause_role = contracts.staking_router.hasRole(PAUSE_ROLE, contracts.deposit_security_module_v2)
    assert not old_dsm_doesnt_have_pause_role

    old_dsm_doesnt_have_resume_role = contracts.staking_router.hasRole(
        STAKING_MODULE_RESUME_ROLE, contracts.deposit_security_module_v2
    )
    assert not old_dsm_doesnt_have_resume_role


def check_manage_consensus_role():
    agent_has_manage_consensus_role = contracts.validators_exit_bus_oracle.hasRole(
        MANAGE_CONSENSUS_VERSION_ROLE, contracts.agent.address
    )
    assert not agent_has_manage_consensus_role


def check_module_before_vote(expected_module_data: Dict):
    sr_contract = Contract.from_abi("StakingContract", contracts.staking_router.address, OLD_SR_ABI)
    module = sr_contract.getStakingModule(expected_module_data["id"])
    assert module["id"] == expected_module_data["id"]
    assert module["stakingModuleFee"] == expected_module_data["stakingModuleFee"]
    assert module["treasuryFee"] == expected_module_data["treasuryFee"]
    assert module["stakeShareLimit"] == expected_module_data["targetShare"]
    assert "priorityExitShareThreshold" not in module
    assert "maxDepositsPerBlock" not in module
    assert "minDepositBlockDistance" not in module


def check_module_after_vote(expected_module_data: Dict):
    module = contracts.staking_router.getStakingModule(expected_module_data["id"])
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
    assert events["Upgraded"]["implementation"] == implementation, "Wrong withdrawal vault proxy implementation"


def validate_dsm_roles_events(events: EventDict):
    validate_revoke_role_event(
        events[1], PAUSE_ROLE, contracts.deposit_security_module_v2.address, contracts.agent.address
    )
    validate_revoke_role_event(
        events[2], STAKING_MODULE_RESUME_ROLE, contracts.deposit_security_module_v2.address, contracts.agent.address
    )

    validate_grant_role_event(
        events[3], STAKING_MODULE_UNVETTING_ROLE, contracts.deposit_security_module.address, contracts.agent.address
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


def validate_module_add(event, csm):
    _events_chain = [
        "LogScriptCall",
        "StakingRouterETHDeposited",
        "StakingModuleAdded",
        "StakingModuleFeesSet",
        "StakingModuleMaxDepositsPerBlockSet",
        "StakingModuleMinDepositBlockDistanceSet",
        "ScriptResult",
    ]
    validate_events_chain([e.name for e in event], _events_chain)


def check_csm():
    cs = contracts.staking_router.getStakingModule(3)

    assert cs["name"] == CSM_AFTER_VOTE["name"]
    assert cs["stakingModuleFee"] == CSM_AFTER_VOTE["stakingModuleFee"]
    assert cs["treasuryFee"] == CSM_AFTER_VOTE["treasuryFee"]
    assert cs["stakeShareLimit"] == CSM_AFTER_VOTE["targetShare"]
    assert cs["priorityExitShareThreshold"] == CSM_AFTER_VOTE["priorityExitShareThreshold"]
    assert cs["maxDepositsPerBlock"] == CSM_AFTER_VOTE["maxDepositsPerBlock"]
    assert cs["minDepositBlockDistance"] == CSM_AFTER_VOTE["minDepositBlockDistance"]
