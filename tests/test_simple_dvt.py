"""
Tests for voting 23/01/2023

"""

from typing import List
from scripts.vote_simple_dvt import start_vote
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert, network
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import Permission
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, network_name
from utils.test.helpers import almostEqWithDiff
from configs.config_mainnet import (
    SIMPLE_DVT_IMPL,
    SIMPLE_DVT_ARAGON_APP_ID,
    SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY,
    SIMPLE_DVT_MODULE_TARGET_SHARE_BP,
    SIMPLE_DVT_MODULE_MODULE_FEE_BP,
    SIMPLE_DVT_MODULE_TREASURY_FEE_BP,
    SIMPLE_DVT_MODULE_ID,
    SIMPLE_DVT_MODULE_NAME,
    SIMPLE_DVT_MODULE_TYPE,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY,
    EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY,
    EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY,
)
from utils.test.easy_track_helpers import create_and_enact_payment_motion, check_add_and_remove_recipient_with_voting
from utils.test.event_validators.permission import (
    Permission,
    validate_grant_role_event,
    validate_permission_revoke_event,
    validate_permission_grantp_event,
)
from utils.test.event_validators.hash_consensus import (
    validate_hash_consensus_member_removed,
    validate_hash_consensus_member_added,
)
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_deactivated,
    validate_node_operator_name_set_event,
    NodeOperatorNameSetItem,
)
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
from utils.test.event_validators.allowed_recipients_registry import (
    validate_set_limit_parameter_event,
    validate_update_spent_amount_event,
)
from utils.easy_track import create_permissions
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str


REQUEST_BURN_SHARES_ROLE = "0x4be29e0e4eb91f98f709d98803cba271592782e293b84a625e025cbb40197ba8"
CREATE_VERSION_ROLE = "0x1f56cfecd3595a2e6cc1a7e6cb0b20df84cdbd92eff2fee554e70e4e45a9a7d8"
STAKING_ROUTER_ROLE = "0xbb75b874360e0bfd87f964eadd8276d8efb7c942134fc329b513032d0803e0c6"
MANAGE_NODE_OPERATOR_ROLE = "0x78523850fdd761612f46e844cf5a16bda6b3151d6ae961fd7e8e7b92bfbca7f8"
SET_NODE_OPERATOR_LIMIT_ROLE = "0x07b39e0faf2521001ae4e58cb9ffd3840a63e205d288dc9c93c3774f0d794754"
MANAGE_SIGNING_KEYS = "0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee"

# TODO: check trusted caller address
TRUSTED_CALLER = "0x08637515E85A4633E23dfc7861e2A9f53af640f7"

simple_dvt_repo_ens = "simple-dvt.lidopm.eth"
simple_dvt_content_uri = (
    "0x697066733a516d615353756a484347636e4675657441504777565735426567614d42766e355343736769334c5366767261536f"
)


def test_vote(helpers, accounts, vote_ids_from_env, stranger, bypass_events_decoding, ldo_holder):
    simple_dvt = contracts.simple_dvt
    kernel = contracts.kernel
    burner = contracts.burner
    voting = contracts.voting
    acl = contracts.acl
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
    assert latest_ver["semanticVersion"] == (1, 0, 0)
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
    # assert simple_dvt_module["status"] == simple_dvt.address
    assert module["name"] == SIMPLE_DVT_MODULE_NAME
    # assert simple_dvt_module["lastDepositBlock"] == vote_tx.block_number
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
    assert set_node_operator_names_evm_script_factory in evm_script_factories
    assert set_node_operator_reward_addresses_evm_script_factory in evm_script_factories
    assert update_target_validator_limits_evm_script_factory in evm_script_factories
    assert change_node_operator_managers_evm_script_factory in evm_script_factories

    evs = group_voting_events(vote_tx)

    validate_evmscript_factory_added_event(
        evs[8],
        EVMScriptFactoryAdded(
            factory_addr=add_node_operators_evm_script_factory,
            permissions=create_permissions(simple_dvt, "addNodeOperator")
            + create_permissions(contracts.acl, "grantPermissionP")[2:]
        )
    )
    validate_evmscript_factory_added_event(
        evs[9],
        EVMScriptFactoryAdded(
            factory_addr=activate_node_operators_evm_script_factory,
            permissions=create_permissions(simple_dvt, "activateNodeOperator")
            + create_permissions(contracts.acl, "grantPermissionP")[2:]
        )
    )
    validate_evmscript_factory_added_event(
        evs[10],
        EVMScriptFactoryAdded(
            factory_addr=deactivate_node_operators_evm_script_factory,
            permissions=create_permissions(simple_dvt, "deactivateNodeOperator")
            + create_permissions(contracts.acl, "revokePermission")[2:]
        )
    )
    validate_evmscript_factory_added_event(
        evs[11],
        EVMScriptFactoryAdded(
            factory_addr=set_vetted_validators_limits_evm_script_factory,
            permissions=create_permissions(simple_dvt, "setNodeOperatorStakingLimit")
        )
    )
    validate_evmscript_factory_added_event(
        evs[12],
        EVMScriptFactoryAdded(
            factory_addr=update_target_validator_limits_evm_script_factory,
            permissions=create_permissions(simple_dvt, "updateTargetValidatorsLimits")
        )
    )
    validate_evmscript_factory_added_event(
        evs[13],
        EVMScriptFactoryAdded(
            factory_addr=set_node_operator_names_evm_script_factory,
            permissions=create_permissions(simple_dvt, "setNodeOperatorName")
        )
    )
    validate_evmscript_factory_added_event(
        evs[14],
        EVMScriptFactoryAdded(
            factory_addr=set_node_operator_reward_addresses_evm_script_factory,
            permissions=create_permissions(simple_dvt, "setNodeOperatorRewardAddress")
        )
    )
    validate_evmscript_factory_added_event(
        evs[15],
        EVMScriptFactoryAdded(
            factory_addr=change_node_operator_managers_evm_script_factory,
            permissions=create_permissions(contracts.acl, "revokePermission")
                + create_permissions(contracts.acl, "grantPermissionP")[2:]
        )
    )

    assert interface.AddNodeOperators(add_node_operators_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    assert interface.AddNodeOperators(add_node_operators_evm_script_factory).trustedCaller() == TRUSTED_CALLER
    assert interface.ActivateNodeOperators(activate_node_operators_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    assert interface.ActivateNodeOperators(activate_node_operators_evm_script_factory).trustedCaller() == TRUSTED_CALLER
    assert interface.DeactivateNodeOperators(deactivate_node_operators_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    assert interface.DeactivateNodeOperators(deactivate_node_operators_evm_script_factory).trustedCaller() == TRUSTED_CALLER
    assert interface.SetVettedValidatorsLimits(set_vetted_validators_limits_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    assert interface.SetVettedValidatorsLimits(set_vetted_validators_limits_evm_script_factory).trustedCaller() == TRUSTED_CALLER
    assert interface.SetNodeOperatorNames(set_node_operator_names_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    assert interface.SetNodeOperatorNames(set_node_operator_names_evm_script_factory).trustedCaller() == TRUSTED_CALLER
    assert interface.SetNodeOperatorRewardAddresses(set_node_operator_reward_addresses_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    assert interface.SetNodeOperatorRewardAddresses(set_node_operator_reward_addresses_evm_script_factory).trustedCaller() == TRUSTED_CALLER
    assert interface.UpdateTargetValidatorLimits(update_target_validator_limits_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    assert interface.UpdateTargetValidatorLimits(update_target_validator_limits_evm_script_factory).trustedCaller() == TRUSTED_CALLER
    assert interface.ChangeNodeOperatorManagers(change_node_operator_managers_evm_script_factory).nodeOperatorsRegistry() == simple_dvt
    assert interface.ChangeNodeOperatorManagers(change_node_operator_managers_evm_script_factory).trustedCaller() == TRUSTED_CALLER



    # validate vote events
    # assert count_vote_items_by_events(vote_tx, contracts.voting) == 65, "Incorrect voting items count"

    # display_voting_events(vote_tx)

    # if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
    #     return



def has_permission(permission: Permission, how: List[int]) -> bool:
    return contracts.acl.hasPermission["address,address,bytes32,uint[]"](
        permission.entity, permission.app, permission.role, how
    )
