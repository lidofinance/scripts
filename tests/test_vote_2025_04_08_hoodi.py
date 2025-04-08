"""
Tests for voting 08/04/2025. Hoodi network.

"""

import pytest
from typing import List
from brownie import interface
from scripts.vote_2025_04_08_hoodi import start_vote

from utils.test.simple_dvt_helpers import (
    fill_simple_dvt_ops,
    get_managers_address,
)
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
)
from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grant_event,
    validate_permission_create_event,
    validate_set_permission_manager_event,
)
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)
from utils.easy_track import create_permissions, create_permissions_for_overloaded_method
from utils.voting import find_metadata_by_vote_id


STAKING_ROUTER_ROLE = "0xbb75b874360e0bfd87f964eadd8276d8efb7c942134fc329b513032d0803e0c6"
MANAGE_NODE_OPERATOR_ROLE = "0x78523850fdd761612f46e844cf5a16bda6b3151d6ae961fd7e8e7b92bfbca7f8"
SET_NODE_OPERATOR_LIMIT_ROLE = "0x07b39e0faf2521001ae4e58cb9ffd3840a63e205d288dc9c93c3774f0d794754"
MANAGE_SIGNING_KEYS = "0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee"


def test_vote(helpers, accounts, vote_ids_from_env):
    simple_dvt = contracts.simple_dvt
    voting = contracts.voting
    easy_track = contracts.easy_track

    evm_script_factories_before = easy_track.getEVMScriptFactories()

    add_node_operators_evm_script_factory = "0x42f2532ab3d41dfD6030db1EC2fF3DBC8DCdf89a"
    activate_node_operators_evm_script_factory = "0xfA3B3EE204E1f0f165379326768667300992530e"
    deactivate_node_operators_evm_script_factory = "0x3114bEbC222Faec27DF8AB7f9bD8dF2063d7fc77"
    set_vetted_validators_limits_evm_script_factory = "0x956c5dC6cfc8603b2293bF8399B718cbf61a9dda"
    set_node_operator_names_evm_script_factory = "0x2F98760650922cf65f1b596635bC5835b6E561d4"
    set_node_operator_reward_addresses_evm_script_factory = "0x3d267e4f8d9dCcc83c2DE66729e6A5B2B0856e31"
    update_target_validator_limits_evm_script_factory = "0xc3975Bc4091B585c57357990155B071111d7f4f8"
    change_node_operator_managers_evm_script_factory = "0x8a437cd5685e270cDDb347eeEfEbD22109Fa42a9"

    EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER = "0xbB958292042c604855d23F8db458855d20e16996"

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

    vote_tx = helpers.execute_vote(accounts, vote_id, voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # I. EasyTrack factories
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

    # validate vote events
    assert count_vote_items_by_events(vote_tx, voting) == 12, "Incorrect voting items count"

    metadata = find_metadata_by_vote_id(vote_id)
    print("metadata", metadata)

    # assert get_lido_vote_cid_from_str(metadata) == "xxxxx"

    evs = group_voting_events_from_receipt(vote_tx)

    # Grant permissions to make operational changes to SimpleDVT module
    permission = Permission(
        entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
        app=simple_dvt,
        role=MANAGE_NODE_OPERATOR_ROLE,  # simple_dvt.MANAGE_NODE_OPERATOR_ROLE(),
    )
    validate_permission_grant_event(evs[0], permission)

    permission = Permission(
        entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
        app=simple_dvt,
        role=SET_NODE_OPERATOR_LIMIT_ROLE,  # simple_dvt.SET_NODE_OPERATOR_LIMIT_ROLE(),
    )
    validate_permission_grant_event(evs[1], permission)

    validate_set_permission_manager_event(
        evs[2], app=simple_dvt, role=MANAGE_SIGNING_KEYS, manager=EASYTRACK_EVMSCRIPT_EXECUTOR
    )

    permission = Permission(entity=EASYTRACK_EVMSCRIPT_EXECUTOR, app=simple_dvt, role=STAKING_ROUTER_ROLE)
    validate_permission_grant_event(evs[3], permission)

    # Add EasyTrack EVM script factories for SimpleDVT module
    validate_evmscript_factory_added_event(
        evs[4],
        EVMScriptFactoryAdded(
            factory_addr=add_node_operators_evm_script_factory,
            permissions=create_permissions(simple_dvt, "addNodeOperator")
            + create_permissions(contracts.acl, "grantPermissionP")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[5],
        EVMScriptFactoryAdded(
            factory_addr=activate_node_operators_evm_script_factory,
            permissions=create_permissions(simple_dvt, "activateNodeOperator")
            + create_permissions(contracts.acl, "grantPermissionP")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[6],
        EVMScriptFactoryAdded(
            factory_addr=deactivate_node_operators_evm_script_factory,
            permissions=create_permissions(simple_dvt, "deactivateNodeOperator")
            + create_permissions(contracts.acl, "revokePermission")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[7],
        EVMScriptFactoryAdded(
            factory_addr=set_vetted_validators_limits_evm_script_factory,
            permissions=create_permissions(simple_dvt, "setNodeOperatorStakingLimit"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[8],
        EVMScriptFactoryAdded(
            factory_addr=update_target_validator_limits_evm_script_factory,
            permissions=(
                create_permissions_for_overloaded_method(
                    contracts.simple_dvt, "updateTargetValidatorsLimits", ("uint", "uint", "uint")
                )
            ),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[9],
        EVMScriptFactoryAdded(
            factory_addr=set_node_operator_names_evm_script_factory,
            permissions=create_permissions(simple_dvt, "setNodeOperatorName"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[10],
        EVMScriptFactoryAdded(
            factory_addr=set_node_operator_reward_addresses_evm_script_factory,
            permissions=create_permissions(simple_dvt, "setNodeOperatorRewardAddress"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[11],
        EVMScriptFactoryAdded(
            factory_addr=change_node_operator_managers_evm_script_factory,
            permissions=create_permissions(contracts.acl, "revokePermission")
            + create_permissions(contracts.acl, "grantPermissionP")[2:],
        ),
    )
