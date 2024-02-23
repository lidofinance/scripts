"""
Voting 20/02/2024.

1. Create new Aragon repo for Simple DVT app
2. Setup Simple DVT module as Aragon app
3. Initialize Simple DVT module with module parameters
4. Create and grant permission `STAKING_ROUTER_ROLE` on Simple DVT module for `StakingRouter`
5. Grant `REQUEST_BURN_SHARES_ROLE` on `Burner` for Simple DVT module
6. Add Simple DVT module to `StakingRouter`
7. Create and grant permission `MANAGE_NODE_OPERATOR_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`
8. Create and grant permission `SET_NODE_OPERATOR_LIMIT_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`
9. Create and grant permission `MANAGE_SIGNING_KEYS` on Simple DVT module for `EasyTrackEVMScriptExecutor`
10. Grant `STAKING_ROUTER_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`
11. Add `AddNodeOperators` EVM script factory with address 0xcAa3AF7460E83E665EEFeC73a7a542E5005C9639
12. Add `ActivateNodeOperators` EVM script factory with address 0xCBb418F6f9BFd3525CE6aADe8F74ECFEfe2DB5C8
13. Add `DeactivateNodeOperators` EVM script factory with address 0x8B82C1546D47330335a48406cc3a50Da732672E7
14. Add `SetVettedValidatorsLimits` EVM script factory with address 0xD75778b855886Fc5e1eA7D6bFADA9EB68b35C19D
15. Add `UpdateTargetValidatorLimits` EVM script factory with address 0x41CF3DbDc939c5115823Fba1432c4EC5E7bD226C
16. Add `SetNodeOperatorNames` EVM script factory with address 0x7d509BFF310d9460b1F613e4e40d342201a83Ae4
17. Add `SetNodeOperatorRewardAddresses` EVM script factory with address 0x589e298964b9181D9938B84bB034C3BB9024E2C0
18. Add `ChangeNodeOperatorManagers` EVM script factory with address 0xE31A0599A6772BCf9b2bFc9e25cf941e793c9a7D
19. Grant `MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE` to the Lido DAO Agent on `OracleReportSanityChecker` contract
20. Grant `MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE` to the Lido DAO Agent on `OracleReportSanityChecker` contract
22. Set `maxAccountingExtraDataListItemsCount` sanity checker parameter to 4
22. Set `maxNodeOperatorsPerExtraDataItemCount` sanity checker parameter to 50
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
    encode_oz_grant_role,
)
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
This vote follows a [Lido DAO decision on Snapshot](https://snapshot.org/#/lido-snapshot.eth/proposal/0xf3ac657484444f0b54eba2c251135c47f875e3d1821496247d11bdd7fab0f291) and [proposes to release](https://research.lido.fi/t/simple-dvt-release/6613) the Simple DVT module on the mainnet, introducing new Easy Track factories for operational efficiency, and adjusting Oracle Report Sanity Checker parameters.
All audit reports can be found here: [Simple DVT app](https://github.com/lidofinance/audits/blob/main/Certora%20Lido%20V2%20Audit%20Report%2004-23.pdf) (same implementation as Node Operators Registry), [Easy Track factories](https://github.com/lidofinance/audits/blob/main/Statemind%20Lido%20Simple%20DVT%20Easy%20Track%20Factories%20Audit%20Report%2001-24.pdf), [SSV module](https://github.com/bloxapp/ssv-network/blob/v1.0.2/contracts/audits/2023-30-10_Quantstamp_v1.0.2.pdf), [Obol module](https://obol.tech/charon_quantstamp_audit.pdf).

The proposed actions include:

1. Create new Aragon repo for Simple DVT app: Establish a dedicated repository with the implementation address 0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed. View the content at the URI: ipfs:[QmaSSujHCGcnFuetAPGwVW5BegaMBvn5SCsgi3LSfvraSo](https://ipfs.io/ipfs/QmaSSujHCGcnFuetAPGwVW5BegaMBvn5SCsgi3LSfvraSo/).  Item 1.
2. Setup and Initialize Simple DVT as a new Aragon App: Model after the [NodeOperatorsRegistry's contract](https://etherscan.io/address/0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5) implementation for the Simple DVT app. Items 2, 3.
3. Integrate Simple DVT Module with StakingRouter: Add the Simple DVT module to [the StakingRouter](https://etherscan.io/address/0xFdDf38947aFB03C621C71b06C9C70bce73f12999) capped at 0.5% of total Lido stake, with 10% fee split as 2% to DAO Treasury / 8% to the Simple DVT module. Items 4-6.
4. Grant permissions to [EasyTrackEVMScriptExecutor](https://etherscan.io/address/0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977): Enabling operational adjustments within the Simple DVT module via Easy Track. Items 7-10.
5. Attach new Easy Track EVM Script Factories for the Simple DVT Module to Easy Track registry: Equip the [Simple DVT Module Committee Multisig](https://app.safe.global/settings/setup?safe=eth:0x08637515E85A4633E23dfc7861e2A9f53af640f7) ([forum proposal](https://research.lido.fi/t/simple-dvt-module-committee-multisig/6520)) with the ability to manage Node Operators: adding, activating, deactivating, and adjusting validator limits and details. All factories addresses could be found on the [forum proposal](https://research.lido.fi/t/simple-dvt-release/6613). Items 11-18.
6. Adjust Oracle Report Sanity Checker Parameters: Modify parameters to support several-module reporting, enhancing the system's reporting capabilities. Items 19-22.
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Create new Aragon repo for Simple DVT app
        #
        (
            "1) Create new Aragon repo for Simple DVT app",
            create_new_app_repo(
                name=create_simple_dvt_app["name"],
                manager=contracts.voting,
                version=create_simple_dvt_app["version"],
                address=create_simple_dvt_app["new_address"],
                content_uri=create_simple_dvt_app["content_uri"],
            ),
        ),
        #
        # II. Setup and initialize Simple DVT module as a new Aragon app
        #
        (
            "2) Setup Simple DVT module as Aragon app",
            update_app_implementation(create_simple_dvt_app["id"], create_simple_dvt_app["new_address"]),
        ),
        (
            "3) Initialize Simple DVT module with module parameters",
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
        # III. Integrate Simple DVT Module with StakingRouter
        #
        (
            "4) Create and grant permission `STAKING_ROUTER_ROLE` on Simple DVT module for `StakingRouter`",
            encode_permission_create(
                entity=contracts.staking_router,
                target_app=contracts.simple_dvt,
                permission_name="STAKING_ROUTER_ROLE",
                manager=contracts.voting,
            ),
        ),
        (
            "5) Grant `REQUEST_BURN_SHARES_ROLE` on `Burner` for Simple DVT module",
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
            "6) Add Simple DVT module to `StakingRouter`",
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
        # IV. Grant permissions to EasyTrackEVMScriptExecutor to make operational changes to Simple DVT module
        #
        (
            "7) Create and grant permission `MANAGE_NODE_OPERATOR_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`",
            encode_permission_create(
                entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="MANAGE_NODE_OPERATOR_ROLE",
                manager=contracts.voting,
            ),
        ),
        (
            "8) Create and grant permission `SET_NODE_OPERATOR_LIMIT_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`",
            encode_permission_create(
                entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="SET_NODE_OPERATOR_LIMIT_ROLE",
                manager=contracts.voting,
            ),
        ),
        (
            "9) Create and grant permission `MANAGE_SIGNING_KEYS` on Simple DVT module for `EasyTrackEVMScriptExecutor`",
            encode_permission_create(
                entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="MANAGE_SIGNING_KEYS",
                manager=EASYTRACK_EVMSCRIPT_EXECUTOR,
            ),
        ),
        (
            "10) Grant `STAKING_ROUTER_ROLE` on Simple DVT module for `EasyTrackEVMScriptExecutor`",
            encode_permission_grant(
                target_app=contracts.simple_dvt,
                permission_name="STAKING_ROUTER_ROLE",
                grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
            ),
        ),
        #
        # V. Attach new Easy Track EVM Script Factories for the Simple DVT Module to Easy Track registry
        #
        (
            "11) Add `AddNodeOperators` EVM script factory with address 0xcAa3AF7460E83E665EEFeC73a7a542E5005C9639",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
                permissions=(
                    create_permissions(contracts.simple_dvt, "addNodeOperator")
                    + create_permissions(contracts.acl, "grantPermissionP")[2:]
                ),
            ),
        ),
        (
            "12) Add `ActivateNodeOperators` EVM script factory with address 0xCBb418F6f9BFd3525CE6aADe8F74ECFEfe2DB5C8",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY,
                permissions=(
                    create_permissions(contracts.simple_dvt, "activateNodeOperator")
                    + create_permissions(contracts.acl, "grantPermissionP")[2:]
                ),
            ),
        ),
        (
            "13) Add `DeactivateNodeOperators` EVM script factory with address 0x8B82C1546D47330335a48406cc3a50Da732672E7",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY,
                permissions=(
                    create_permissions(contracts.simple_dvt, "deactivateNodeOperator")
                    + create_permissions(contracts.acl, "revokePermission")[2:]
                ),
            ),
        ),
        (
            "14) Add `SetVettedValidatorsLimits` EVM script factory with address 0xD75778b855886Fc5e1eA7D6bFADA9EB68b35C19D",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "setNodeOperatorStakingLimit")),
            ),
        ),
        (
            "15) Add `UpdateTargetValidatorLimits` EVM script factory with address 0x41CF3DbDc939c5115823Fba1432c4EC5E7bD226C",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "updateTargetValidatorsLimits")),
            ),
        ),
        (
            "16) Add `SetNodeOperatorNames` EVM script factory with address 0x7d509BFF310d9460b1F613e4e40d342201a83Ae4",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "setNodeOperatorName")),
            ),
        ),
        (
            "17) Add `SetNodeOperatorRewardAddresses` EVM script factory with address 0x589e298964b9181D9938B84bB034C3BB9024E2C0",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY,
                permissions=(create_permissions(contracts.simple_dvt, "setNodeOperatorRewardAddress")),
            ),
        ),
        (
            "18) Add `ChangeNodeOperatorManagers` EVM script factory with address 0xE31A0599A6772BCf9b2bFc9e25cf941e793c9a7D",
            add_evmscript_factory(
                factory=EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY,
                permissions=(
                    create_permissions(contracts.acl, "revokePermission")
                    + create_permissions(contracts.acl, "grantPermissionP")[2:]
                ),
            ),
        ),
        #
        # VI. Adjust Oracle Report Sanity Checker Parameters
        #
        (
            "19) Grant `MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE` to the Lido DAO Agent on `OracleReportSanityChecker` contract",
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
            "20) Grant `MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE` to the Lido DAO Agent on `OracleReportSanityChecker` contract",
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
            "21) Set `maxAccountingExtraDataListItemsCount` sanity checker parameter to 4",
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
            "22) Set `maxNodeOperatorsPerExtraDataItemCount` sanity checker parameter to 50",
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
