"""
Voting 08/04/2025. Hoodi network.

1. Create and grant permission `MANAGE_NODE_OPERATOR_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`
2. Create and grant permission `SET_NODE_OPERATOR_LIMIT_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`
3. Create and grant permission `MANAGE_SIGNING_KEYS` on Simple DVT module for `EasyTrackEVMScriptExecutor`
4. Grant `STAKING_ROUTER_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`
5. Add `AddNodeOperators` EVM script factory with address 0x42f2532ab3d41dfD6030db1EC2fF3DBC8DCdf89a
6. Add `ActivateNodeOperators` EVM script factory with address 0xfA3B3EE204E1f0f165379326768667300992530e
7. Add `DeactivateNodeOperators` EVM script factory with address 0x3114bEbC222Faec27DF8AB7f9bD8dF2063d7fc77
8. Add `SetVettedValidatorsLimits` EVM script factory with address 0x956c5dC6cfc8603b2293bF8399B718cbf61a9dda
9. Add `UpdateTargetValidatorLimits` EVM script factory with address 0xc3975Bc4091B585c57357990155B071111d7f4f8
10. Add `SetNodeOperatorNames` EVM script factory with address 0x2F98760650922cf65f1b596635bC5835b6E561d4
11. Add `SetNodeOperatorRewardAddresses` EVM script factory with address 0x3d267e4f8d9dCcc83c2DE66729e6A5B2B0856e31
12. Add `ChangeNodeOperatorManagers` EVM script factory with address 0x8a437cd5685e270cDDb347eeEfEbD22109Fa42a9
"""

import time

from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
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
from utils.permissions import encode_permission_create, encode_permission_grant, encode_set_permission_manager
from utils.easy_track import add_evmscript_factory, create_permissions, create_permissions_for_overloaded_method


description = """
The proposed actions include:

1. Grant permissions to EasyTrack EVMScriptExecutor.
2. Attach new Easy Track EVM Script Factories for the Simple DVT Module to Easy Track registry.
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # Grant permissions to EasyTrackEVMScriptExecutor to make operational changes to Simple DVT module
        #
        (
            "1) Grant permission `MANAGE_NODE_OPERATOR_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`",
            encode_permission_grant(
                target_app=contracts.simple_dvt,
                permission_name="MANAGE_NODE_OPERATOR_ROLE",
                grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
            ),
        ),
        (
            "2) Grant permission `SET_NODE_OPERATOR_LIMIT_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`",
            encode_permission_grant(
                target_app=contracts.simple_dvt,
                permission_name="SET_NODE_OPERATOR_LIMIT_ROLE",
                grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
            ),
        ),
        (
            "3) Transfer permission manager of `MANAGE_SIGNING_KEYS` on Simple DVT module for `EasyTrackEVMScriptExecutor`",
            encode_set_permission_manager(
                new_manager=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="MANAGE_SIGNING_KEYS",
            ),
        ),
        (
            "4) Grant `STAKING_ROUTER_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`",
            encode_permission_grant(
                target_app=contracts.simple_dvt,
                permission_name="STAKING_ROUTER_ROLE",
                grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
            ),
        ),
        #
        # Attach new Easy Track EVM Script Factories for the Simple DVT Module to Easy Track registry
        #
        (
            "5) Add `AddNodeOperators` EVM script factory with address 0x42f2532ab3d41dfD6030db1EC2fF3DBC8DCdf89a",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
                permissions=(
                    create_permissions(contracts.simple_dvt, "addNodeOperator")
                    + create_permissions(contracts.acl, "grantPermissionP")[2:]
                ),
            ),
        ),
        (
            "6) Add `ActivateNodeOperators` EVM script factory with address 0xfA3B3EE204E1f0f165379326768667300992530e",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY,
                permissions=(
                    create_permissions(contracts.simple_dvt, "activateNodeOperator")
                    + create_permissions(contracts.acl, "grantPermissionP")[2:]
                ),
            ),
        ),
        (
            "7) Add `DeactivateNodeOperators` EVM script factory with address 0x3114bEbC222Faec27DF8AB7f9bD8dF2063d7fc77",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY,
                permissions=(
                    create_permissions(contracts.simple_dvt, "deactivateNodeOperator")
                    + create_permissions(contracts.acl, "revokePermission")[2:]
                ),
            ),
        ),
        (
            "8) Add `SetVettedValidatorsLimits` EVM script factory with address 0x956c5dC6cfc8603b2293bF8399B718cbf61a9dda",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "setNodeOperatorStakingLimit")),
            ),
        ),
        (
            "9) Add `UpdateTargetValidatorLimits` EVM script factory with address 0xc3975Bc4091B585c57357990155B071111d7f4f8",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY,
                permissions=(
                    create_permissions_for_overloaded_method(
                        contracts.simple_dvt, "updateTargetValidatorsLimits", ("uint", "uint", "uint")
                    )
                ),
            ),
        ),
        (
            "10) Add `SetNodeOperatorNames` EVM script factory with address 0x2F98760650922cf65f1b596635bC5835b6E561d4",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "setNodeOperatorName")),
            ),
        ),
        (
            "11) Add `SetNodeOperatorRewardAddresses` EVM script factory with address 0x3d267e4f8d9dCcc83c2DE66729e6A5B2B0856e31",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "setNodeOperatorRewardAddress")),
            ),
        ),
        (
            "12) Add `ChangeNodeOperatorManagers` EVM script factory with address 0x8a437cd5685e270cDDb347eeEfEbD22109Fa42a9",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY,
                permissions=(
                    create_permissions(contracts.acl, "revokePermission")
                    + create_permissions(contracts.acl, "grantPermissionP")[2:]
                ),
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

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
