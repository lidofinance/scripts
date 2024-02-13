"""
Voting SimpleDVT
"""

import time

from typing import Dict, List, NamedTuple
from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_execute, agent_forward
from utils.kernel import update_app_implementation
from utils.repo import create_new_app_repo
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    SIMPLE_DVT_IMPL,
    SIMPLE_DVT_ARAGON_APP_ID,
    SIMPLE_DVT_MODULE_NAME,
    SIMPLE_DVT_MODULE_TYPE,
    SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY,
    SIMPLE_DVT_MODULE_TARGET_SHARE_BP,
    SIMPLE_DVT_MODULE_MODULE_FEE_BP,
    SIMPLE_DVT_MODULE_TREASURY_FEE_BP,
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
from utils.permissions import (
    encode_permission_create,
    encode_permission_grant,
    encode_permission_revoke,
    encode_permission_grant_p,
    encode_oz_grant_role,
)
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op
from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
)

create_simple_dvt_app = {
    "name": "simple-dvt",
    "new_address": SIMPLE_DVT_IMPL,
    "content_uri": "0x697066733a516d615353756a484347636e4675657441504777565735426567614d42766e355343736769334c5366767261536f",
    "id": SIMPLE_DVT_ARAGON_APP_ID,
    "version": (1, 0, 0),
    "module_type": SIMPLE_DVT_MODULE_TYPE,
    "penalty_delay": SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY,
}


description = """
Deploy SimpleDVT
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Create new Aragon DAO Application Repo for SimpleDVT
        #
        (
            "1) Create new Repo for SimpleDVT app",
            create_new_app_repo(
                name=create_simple_dvt_app["name"],
                manager=contracts.voting,
                version=create_simple_dvt_app["version"],
                address=create_simple_dvt_app["new_address"],
                content_uri=create_simple_dvt_app["content_uri"],
            ),
        ),
        #
        # II. Setup and initialize SimpleDVT module as new Aragon app
        #
        (
            "2) Setup SimpleDVT as Aragon DAO app",
            update_app_implementation(create_simple_dvt_app["id"], create_simple_dvt_app["new_address"]),
        ),
        (
            "3) Initialize SimpleDVT module",
            (
                contracts.simple_dvt.address,
                contracts.simple_dvt.initialize.encode_input(
                    contracts.lido_locator,
                    create_simple_dvt_app["module_type"],
                    create_simple_dvt_app["penalty_delay"],
                ),
            ),
        ),
        #
        # III. Add SimpleDVT module to Staking Router
        #
        (
            "4) Create and grant permission STAKING_ROUTER_ROLE on SimpleDVT module for StakingRouter",
            encode_permission_create(
                entity=contracts.staking_router,
                target_app=contracts.simple_dvt,
                permission_name="STAKING_ROUTER_ROLE",
                manager=contracts.voting,
            ),
        ),
        (
            "5) Grant REQUEST_BURN_SHARES_ROLE on Burner for SimpleDVT module",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.burner,
                        role_name="REQUEST_BURN_SHARES_ROLE",
                        grant_to=contracts.simple_dvt,
                    )
                ]
            ),
        ),
        (
            "6) Add SimpleDVT module to StakingRouter",
            agent_forward(
                [
                    (
                        contracts.staking_router.address,
                        contracts.staking_router.addStakingModule.encode_input(
                            SIMPLE_DVT_MODULE_NAME,
                            contracts.simple_dvt,
                            SIMPLE_DVT_MODULE_TARGET_SHARE_BP,
                            SIMPLE_DVT_MODULE_MODULE_FEE_BP,
                            SIMPLE_DVT_MODULE_TREASURY_FEE_BP,
                        ),
                    ),
                ]
            ),
        ),
        #
        # IV. Grant permissions to EasyTrackEVMScriptExecutor to make operational changes to SimpleDVT module
        #
        (
            "7) Create and grant permission MANAGE_NODE_OPERATOR_ROLE on SimpleDVT module for EasyTrackEVMScriptExecutor",
            encode_permission_create(
                entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="MANAGE_NODE_OPERATOR_ROLE",
                manager=contracts.voting,
            ),
        ),
        (
            "8) Create and grant permission SET_NODE_OPERATOR_LIMIT_ROLE on SimpleDVT module for EasyTrackEVMScriptExecutor",
            encode_permission_create(
                entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="SET_NODE_OPERATOR_LIMIT_ROLE",
                manager=contracts.voting,
            ),
        ),
        (
            "9) Create and grant permission MANAGE_SIGNING_KEYS on SimpleDVT module for EasyTrackEVMScriptExecutor",
            encode_permission_create(
                entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="MANAGE_SIGNING_KEYS",
                manager=EASYTRACK_EVMSCRIPT_EXECUTOR,
            ),
        ),
        (
            "10) Grant STAKING_ROUTER_ROLE on SimpleDVT module for EasyTrackEVMScriptExecutor",
            encode_permission_grant(
                target_app=contracts.simple_dvt,
                permission_name="STAKING_ROUTER_ROLE",
                grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
            ),
        ),
        #
        # V. Add EasyTrack EVM script factories for SimpleDVT module to EasyTrack registry
        #
        (
            "11) Add AddNodeOperators EVM script factory",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
                permissions=(
                    create_permissions(contracts.simple_dvt, "addNodeOperator")
                    + create_permissions(contracts.acl, "grantPermissionP")[2:]
                ),
            ),
        ),
        (
            "12) Add ActivateNodeOperators EVM script factory",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY,
                permissions=(
                    create_permissions(contracts.simple_dvt, "activateNodeOperator")
                    + create_permissions(contracts.acl, "grantPermissionP")[2:]
                ),
            ),
        ),
        (
            "13) Add DeactivateNodeOperators EVM script factory",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY,
                permissions=(
                    create_permissions(contracts.simple_dvt, "deactivateNodeOperator")
                    + create_permissions(contracts.acl, "revokePermission")[2:]
                ),
            ),
        ),
        (
            "14) Add SetVettedValidatorsLimits EVM script factory",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "setNodeOperatorStakingLimit")),
            ),
        ),
        (
            "15) Add UpdateTargetValidatorLimits EVM script factory",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "updateTargetValidatorsLimits")),
            ),
        ),
        (
            "16) Add SetNodeOperatorNames EVM script factory",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "setNodeOperatorName")),
            ),
        ),
        (
            "17) Add SetNodeOperatorRewardAddresses EVM script factory",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "setNodeOperatorRewardAddress")),
            ),
        ),
        (
            "18) Add ChangeNodeOperatorManagers EVM script factory",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY,
                permissions=(
                    create_permissions(contracts.acl, "revokePermission")
                    + create_permissions(contracts.acl, "grantPermissionP")[2:]
                ),
            ),
        ),
        #
        # VI. Update Oracle Report Sanity Checker parameters
        #
        (
            "19)  Grant MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE to the Lido DAO Agent on OracleReportSanityChecker contract",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.oracle_report_sanity_checker,
                        role_name="MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "20)  Grant MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE to the Lido DAO Agent on OracleReportSanityChecker contract",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.oracle_report_sanity_checker,
                        role_name="MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "21) Set maxAccountingExtraDataListItemsCount sanity checker parameter to 4",
            agent_forward(
                [
                    (
                        contracts.oracle_report_sanity_checker.address,
                        contracts.oracle_report_sanity_checker.setMaxAccountingExtraDataListItemsCount.encode_input(4),
                    ),
                ]
            ),
        ),
        (
            "22) Set maxNodeOperatorsPerExtraDataItemCount sanity checker parameter to 50",
            agent_forward(
                [
                    (
                        contracts.oracle_report_sanity_checker.address,
                        contracts.oracle_report_sanity_checker.setMaxNodeOperatorsPerExtraDataItemCount.encode_input(
                            50
                        ),
                    ),
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

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
