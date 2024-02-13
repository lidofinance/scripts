"""
Tests for voting 23/01/2023

"""

from typing import List
from scripts.vote_simple_dvt import start_vote
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert, network
from utils.test.event_validators.aragon import validate_app_update_event, validate_push_to_repo_event
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.staking_router import StakingModuleItem, validate_staking_module_added_event
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, network_name

from configs.config_mainnet import (
    SIMPLE_DVT_IMPL,
    SIMPLE_DVT_ARAGON_APP_NAME,
    SIMPLE_DVT_ARAGON_APP_ID,
    SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY,
    SIMPLE_DVT_MODULE_TARGET_SHARE_BP,
    SIMPLE_DVT_MODULE_MODULE_FEE_BP,
    SIMPLE_DVT_MODULE_TREASURY_FEE_BP,
    SIMPLE_DVT_MODULE_ID,
    SIMPLE_DVT_MODULE_NAME,
    SIMPLE_DVT_MODULE_TYPE,
    EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY,
    EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY,
    EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY,
    REPO_APP_ID,
)
from utils.test.event_validators.repo_upgrade import (
    CREATE_VERSION_ROLE,
    NewRepoItem,
    validate_new_repo_with_version_event,
)
from utils.test.event_validators.permission import (
    Permission,
    validate_grant_role_event,
    validate_permission_revoke_event,
    validate_permission_grantp_event,
    validate_permission_grant_event,
    validate_permission_create_event,
)
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)
from utils.easy_track import create_permissions
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str


REQUEST_BURN_SHARES_ROLE = "0x4be29e0e4eb91f98f709d98803cba271592782e293b84a625e025cbb40197ba8"
STAKING_ROUTER_ROLE = "0xbb75b874360e0bfd87f964eadd8276d8efb7c942134fc329b513032d0803e0c6"
MANAGE_NODE_OPERATOR_ROLE = "0x78523850fdd761612f46e844cf5a16bda6b3151d6ae961fd7e8e7b92bfbca7f8"
SET_NODE_OPERATOR_LIMIT_ROLE = "0x07b39e0faf2521001ae4e58cb9ffd3840a63e205d288dc9c93c3774f0d794754"
MANAGE_SIGNING_KEYS = "0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee"
MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE = "0x0cf253eb71298c92e2814969a122f66b781f9b217f8ecde5401e702beb9345f6"
MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE = "0xf6ac39904c42f8e23056f1b678e4892fc92caa68ae836dc474e137f0e67f5716"

simple_dvt_repo_ens = "simple-dvt.lidopm.eth"
simple_dvt_content_uri = (
    "0x697066733a516d615353756a484347636e4675657441504777565735426567614d42766e355343736769334c5366767261536f"
)
simple_dvt_semantic_version = (1, 0, 0)


def test_vote(helpers, accounts, vote_ids_from_env, stranger, bypass_events_decoding, ldo_holder):
    simple_dvt = contracts.simple_dvt
    kernel = contracts.kernel
    burner = contracts.burner
    voting = contracts.voting
    acl = contracts.acl
    agent = contracts.agent
    easy_track = contracts.easy_track
    staking_router = contracts.staking_router

    assert staking_router.getStakingModulesCount() == 1
    assert kernel.getApp(kernel.APP_BASES_NAMESPACE(), SIMPLE_DVT_ARAGON_APP_ID) == ZERO_ADDRESS
    assert not burner.hasRole(kernel.APP_BASES_NAMESPACE(), simple_dvt.address)

    assert not network.web3.ens.resolve(simple_dvt_repo_ens)

    # TODO: check absence of repo ?

    evm_script_factories_before = easy_track.getEVMScriptFactories()

    add_node_operators_evm_script_factory = EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY
    activate_node_operators_evm_script_factory = EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY
    deactivate_node_operators_evm_script_factory = EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY
    set_vetted_validators_limits_evm_script_factory = EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY
    set_node_operator_names_evm_script_factory = EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY
    set_node_operator_reward_addresses_evm_script_factory = (
        EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY
    )
    update_target_validator_limits_evm_script_factory = EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY
    change_node_operator_managers_evm_script_factory = EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY

    assert add_node_operators_evm_script_factory not in evm_script_factories_before
    assert activate_node_operators_evm_script_factory not in evm_script_factories_before
    assert deactivate_node_operators_evm_script_factory not in evm_script_factories_before
    assert set_vetted_validators_limits_evm_script_factory not in evm_script_factories_before
    assert set_node_operator_names_evm_script_factory not in evm_script_factories_before
    assert set_node_operator_reward_addresses_evm_script_factory not in evm_script_factories_before
    assert update_target_validator_limits_evm_script_factory not in evm_script_factories_before
    assert change_node_operator_managers_evm_script_factory not in evm_script_factories_before

    sanity_checker_limits = contracts.oracle_report_sanity_checker.getOracleReportLimits()
    assert sanity_checker_limits["maxAccountingExtraDataListItemsCount"] == 2
    assert sanity_checker_limits["maxNodeOperatorsPerExtraDataItemCount"] == 100

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # I. Setup SimpleDVT module as new Aragon app
    assert kernel.getApp(kernel.APP_BASES_NAMESPACE(), SIMPLE_DVT_ARAGON_APP_ID) == SIMPLE_DVT_IMPL

    simple_dvt_repo = interface.Repo(network.web3.ens.resolve(simple_dvt_repo_ens))
    assert simple_dvt_repo

    # Voting has permission to update repo
    assert simple_dvt_repo.canPerform(voting.address, CREATE_VERSION_ROLE, [])

    # Latest version in repo is 1st and only one
    latest_ver = simple_dvt_repo.getLatest()
    assert latest_ver["semanticVersion"] == simple_dvt_semantic_version
    assert latest_ver["contractAddress"] == SIMPLE_DVT_IMPL
    assert latest_ver["contentURI"] == simple_dvt_content_uri

    # StakingRouter params
    assert staking_router.getStakingModulesCount() == 2
    assert staking_router.hasStakingModule(SIMPLE_DVT_MODULE_ID)

    module = staking_router.getStakingModule(SIMPLE_DVT_MODULE_ID)
    assert module["id"] == SIMPLE_DVT_MODULE_ID
    assert module["stakingModuleAddress"] == simple_dvt.address
    assert module["stakingModuleFee"] == SIMPLE_DVT_MODULE_MODULE_FEE_BP
    assert module["treasuryFee"] == SIMPLE_DVT_MODULE_TREASURY_FEE_BP
    assert module["targetShare"] == SIMPLE_DVT_MODULE_TARGET_SHARE_BP
    assert module["status"] == 0  # StakingModuleStatus.Active
    assert module["name"] == SIMPLE_DVT_MODULE_NAME
    assert module["lastDepositBlock"] == vote_tx.block_number
    assert module["exitedValidatorsCount"] == 0

    # SimpleDVT app papams
    assert simple_dvt.appId() == SIMPLE_DVT_ARAGON_APP_ID
    assert simple_dvt.kernel() == kernel.address
    assert simple_dvt.hasInitialized()
    assert simple_dvt.getLocator() == contracts.lido_locator.address
    assert simple_dvt.getType() == SIMPLE_DVT_MODULE_TYPE
    assert simple_dvt.getStuckPenaltyDelay() == SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY
    assert simple_dvt.getNodeOperatorsCount() == 0
    assert simple_dvt.getActiveNodeOperatorsCount() == 0
    assert simple_dvt.getNonce() == 0

    module_summary = simple_dvt.getStakingModuleSummary()
    assert module_summary["totalExitedValidators"] == 0
    assert module_summary["totalDepositedValidators"] == 0
    assert module_summary["depositableValidatorsCount"] == 0

    # II. Permissions
    assert acl.getPermissionManager(simple_dvt.address, STAKING_ROUTER_ROLE) == voting.address
    assert simple_dvt.canPerform(staking_router.address, STAKING_ROUTER_ROLE, [])
    assert simple_dvt.canPerform(EASYTRACK_EVMSCRIPT_EXECUTOR, STAKING_ROUTER_ROLE, [])

    assert acl.getPermissionManager(simple_dvt.address, MANAGE_NODE_OPERATOR_ROLE) == voting.address
    assert simple_dvt.canPerform(EASYTRACK_EVMSCRIPT_EXECUTOR, MANAGE_NODE_OPERATOR_ROLE, [])

    assert acl.getPermissionManager(simple_dvt.address, SET_NODE_OPERATOR_LIMIT_ROLE) == voting.address
    assert simple_dvt.canPerform(EASYTRACK_EVMSCRIPT_EXECUTOR, SET_NODE_OPERATOR_LIMIT_ROLE, [])

    assert acl.getPermissionManager(simple_dvt.address, MANAGE_SIGNING_KEYS) == EASYTRACK_EVMSCRIPT_EXECUTOR
    assert simple_dvt.canPerform(EASYTRACK_EVMSCRIPT_EXECUTOR, MANAGE_SIGNING_KEYS, [])

    # III. EasyTrack factories
    evm_script_factories = easy_track.getEVMScriptFactories()

    assert add_node_operators_evm_script_factory in evm_script_factories
    assert activate_node_operators_evm_script_factory in evm_script_factories
    assert deactivate_node_operators_evm_script_factory in evm_script_factories
    assert set_vetted_validators_limits_evm_script_factory in evm_script_factories
    assert update_target_validator_limits_evm_script_factory in evm_script_factories
    assert set_node_operator_names_evm_script_factory in evm_script_factories
    assert set_node_operator_reward_addresses_evm_script_factory in evm_script_factories
    assert change_node_operator_managers_evm_script_factory in evm_script_factories

    assert interface.AddNodeOperators(add_node_operators_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    assert (
        interface.AddNodeOperators(add_node_operators_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.ActivateNodeOperators(activate_node_operators_evm_script_factory).nodeOperatorsRegistry()
        == simple_dvt
    )
    assert (
        interface.ActivateNodeOperators(activate_node_operators_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.DeactivateNodeOperators(deactivate_node_operators_evm_script_factory).nodeOperatorsRegistry()
        == simple_dvt
    )
    assert (
        interface.DeactivateNodeOperators(deactivate_node_operators_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.SetVettedValidatorsLimits(set_vetted_validators_limits_evm_script_factory).nodeOperatorsRegistry()
        == simple_dvt
    )
    assert (
        interface.SetVettedValidatorsLimits(set_vetted_validators_limits_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.SetNodeOperatorNames(set_node_operator_names_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    )
    assert (
        interface.SetNodeOperatorNames(set_node_operator_names_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.SetNodeOperatorRewardAddresses(
            set_node_operator_reward_addresses_evm_script_factory
        ).nodeOperatorsRegistry()
        == simple_dvt
    )
    assert (
        interface.SetNodeOperatorRewardAddresses(set_node_operator_reward_addresses_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.UpdateTargetValidatorLimits(update_target_validator_limits_evm_script_factory).nodeOperatorsRegistry()
        == simple_dvt
    )
    assert (
        interface.UpdateTargetValidatorLimits(update_target_validator_limits_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.ChangeNodeOperatorManagers(change_node_operator_managers_evm_script_factory).nodeOperatorsRegistry()
        == simple_dvt
    )
    assert (
        interface.ChangeNodeOperatorManagers(change_node_operator_managers_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )

    sanity_checker_limits = contracts.oracle_report_sanity_checker.getOracleReportLimits()
    assert sanity_checker_limits["maxAccountingExtraDataListItemsCount"] == 4
    assert sanity_checker_limits["maxNodeOperatorsPerExtraDataItemCount"] == 50

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 22, "Incorrect voting items count"

    metadata = find_metadata_by_vote_id(vote_id)
    print("metadata", metadata)

    # TODO fix description
    # assert get_lido_vote_cid_from_str(metadata) == "bafkreibugpzhp7nexxg7c6jpmmszikvaj2vscxw426zewa6uyv3z5y6ak4"

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    # I. Create new Aragon DAO Application Repo for SimpleDVT
    repo_params = NewRepoItem(
        name=SIMPLE_DVT_ARAGON_APP_NAME,
        app=simple_dvt.address,
        app_id=SIMPLE_DVT_ARAGON_APP_ID,
        repo_app_id=REPO_APP_ID,
        semantic_version=simple_dvt_semantic_version,
        apm=contracts.apm_registry.address,
        manager=voting.address,
    )
    validate_new_repo_with_version_event(evs[0], repo_params)

    # II. Setup and initialize SimpleDVT module as new Aragon app
    validate_app_update_event(evs[1], SIMPLE_DVT_ARAGON_APP_ID, SIMPLE_DVT_IMPL)
    validate_simple_dvt_intialize_event(evs[2])

    # III. Add SimpleDVT module to Staking Router
    # Create and grant permission STAKING_ROUTER_ROLE on SimpleDVT module for StakingRouter
    permission = Permission(
        entity=staking_router,
        app=simple_dvt,
        role=STAKING_ROUTER_ROLE,  # simple_dvt.STAKING_ROUTER_ROLE(),
    )
    validate_permission_create_event(evs[3], permission, manager=voting)

    # Grant REQUEST_BURN_SHARES_ROLE on Burner for SimpleDVT module
    validate_grant_role_event(evs[4], REQUEST_BURN_SHARES_ROLE, simple_dvt, agent)

    # Add SimpleDVT module to StakingRouter
    module_item = StakingModuleItem(
        SIMPLE_DVT_MODULE_ID,
        simple_dvt.address,
        SIMPLE_DVT_MODULE_NAME,
        SIMPLE_DVT_MODULE_TARGET_SHARE_BP,
        SIMPLE_DVT_MODULE_MODULE_FEE_BP,
        SIMPLE_DVT_MODULE_TREASURY_FEE_BP,
    )
    validate_staking_module_added_event(evs[5], module_item)

    # IV. Grant permissions to make operational changes to SimpleDVT module
    permission = Permission(
        entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
        app=simple_dvt,
        role=MANAGE_NODE_OPERATOR_ROLE,  # simple_dvt.MANAGE_NODE_OPERATOR_ROLE(),
    )
    validate_permission_create_event(evs[6], permission, manager=voting)

    permission = Permission(
        entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
        app=simple_dvt,
        role=SET_NODE_OPERATOR_LIMIT_ROLE,  # simple_dvt.SET_NODE_OPERATOR_LIMIT_ROLE(),
    )
    validate_permission_create_event(evs[7], permission, manager=voting)

    permission = Permission(
        entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
        app=simple_dvt,
        role=MANAGE_SIGNING_KEYS,  # simple_dvt.MANAGE_SIGNING_KEYS(),
    )
    validate_permission_create_event(evs[8], permission, manager=EASYTRACK_EVMSCRIPT_EXECUTOR)

    permission = Permission(entity=EASYTRACK_EVMSCRIPT_EXECUTOR, app=simple_dvt, role=STAKING_ROUTER_ROLE)
    validate_permission_grant_event(evs[9], permission)

    # IV. Add EasyTrack EVM script factories for SimpleDVT module
    validate_evmscript_factory_added_event(
        evs[10],
        EVMScriptFactoryAdded(
            factory_addr=add_node_operators_evm_script_factory,
            permissions=create_permissions(simple_dvt, "addNodeOperator")
            + create_permissions(contracts.acl, "grantPermissionP")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[11],
        EVMScriptFactoryAdded(
            factory_addr=activate_node_operators_evm_script_factory,
            permissions=create_permissions(simple_dvt, "activateNodeOperator")
            + create_permissions(contracts.acl, "grantPermissionP")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[12],
        EVMScriptFactoryAdded(
            factory_addr=deactivate_node_operators_evm_script_factory,
            permissions=create_permissions(simple_dvt, "deactivateNodeOperator")
            + create_permissions(contracts.acl, "revokePermission")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[13],
        EVMScriptFactoryAdded(
            factory_addr=set_vetted_validators_limits_evm_script_factory,
            permissions=create_permissions(simple_dvt, "setNodeOperatorStakingLimit"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[14],
        EVMScriptFactoryAdded(
            factory_addr=update_target_validator_limits_evm_script_factory,
            permissions=create_permissions(simple_dvt, "updateTargetValidatorsLimits"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[15],
        EVMScriptFactoryAdded(
            factory_addr=set_node_operator_names_evm_script_factory,
            permissions=create_permissions(simple_dvt, "setNodeOperatorName"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[16],
        EVMScriptFactoryAdded(
            factory_addr=set_node_operator_reward_addresses_evm_script_factory,
            permissions=create_permissions(simple_dvt, "setNodeOperatorRewardAddress"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[17],
        EVMScriptFactoryAdded(
            factory_addr=change_node_operator_managers_evm_script_factory,
            permissions=create_permissions(contracts.acl, "revokePermission")
            + create_permissions(contracts.acl, "grantPermissionP")[2:],
        ),
    )

    # VI. Update Oracle Report Sanity Checker parameters
    validate_grant_role_event(evs[18], MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE, agent, agent)
    validate_grant_role_event(evs[19], MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE, agent, agent)
    validate_max_extra_data_list_items_count_event(evs[20], 4)
    validate_max_operators_per_extra_data_item_count_event(evs[21], 50)


def has_permission(permission: Permission, how: List[int]) -> bool:
    return contracts.acl.hasPermission["address,address,bytes32,uint[]"](
        permission.entity, permission.app, permission.role, how
    )


def validate_max_extra_data_list_items_count_event(event: EventDict, value: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "MaxAccountingExtraDataListItemsCountSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("MaxAccountingExtraDataListItemsCountSet") == 1
    assert event["MaxAccountingExtraDataListItemsCountSet"]["maxAccountingExtraDataListItemsCount"] == value


def validate_max_operators_per_extra_data_item_count_event(event: EventDict, value: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "MaxNodeOperatorsPerExtraDataItemCountSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("MaxNodeOperatorsPerExtraDataItemCountSet") == 1
    assert event["MaxNodeOperatorsPerExtraDataItemCountSet"]["maxNodeOperatorsPerExtraDataItemCount"] == value


def validate_simple_dvt_intialize_event(event: EventDict):
    _events_chain = [
        "LogScriptCall",
        "ContractVersionSet",
        "StuckPenaltyDelayChanged",
        "Approval",
        "LocatorContractSet",
        "StakingModuleTypeSet",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ContractVersionSet") == 1
    assert event.count("StuckPenaltyDelayChanged") == 1
    assert event.count("Approval") == 1
    assert event.count("LocatorContractSet") == 1
    assert event.count("StakingModuleTypeSet") == 1

    assert event["Approval"]["owner"] == contracts.simple_dvt.address
    assert event["Approval"]["spender"] == contracts.burner.address
    assert event["Approval"]["value"] == 2**256 - 1  # uint256 max

    assert event["ContractVersionSet"]["version"] == 2
    assert event["StuckPenaltyDelayChanged"]["stuckPenaltyDelay"] == SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY
    assert event["LocatorContractSet"]["locatorAddress"] == contracts.lido_locator.address
    assert event["StakingModuleTypeSet"]["moduleType"] == SIMPLE_DVT_MODULE_TYPE
