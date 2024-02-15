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
### I. Create new Aragon DAO Application Repo for Simple DVT

1. **Create new Aragon DAO Application Repo for Simple DVT app**  with parameters:
    * Name: `simple-dvt`
    * Version: `1.0.0`
    * Implementation address: [0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed](https://etherscan.io/address/0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed)
    * Content IPFS URI: [ipfs:QmaSSujHCGcnFuetAPGwVW5BegaMBvn5SCsgi3LSfvraSo](https://ipfs.io/ipfs/QmaSSujHCGcnFuetAPGwVW5BegaMBvn5SCsgi3LSfvraSo) (hex-encoded: `0x697066733a516d615353756a484347636e4675657441504777565735426567614d42766e355343736769334c5366767261536f`)


### II. Setup and initialize Simple DVT module as new Aragon app

2. **Setup Simple DVT module as Aragon DAO app** with the same [contract implementation](https://etherscan.io/address/0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed) as the NodeOperatorsRegistry.

3. **Initialize of Simple DVT module** with parameters:
    * Module Type = `curated-onchain-v1` (hex-encoded: `0x637572617465642d6f6e636861696e2d76310000000000000000000000000000`)
    * Stuck Penalty Delay = `432000` (5 days - the same as in Curated Module)


### III. Add Simple DVT module to StakingRouter

4. **Create and grant permission `STAKING_ROUTER_ROLE` on Simple DVT module for StakingRouter**. This is necessary for the Simple DVT module to function as a staking module

5. **Grant `REQUEST_BURN_SHARES_ROLE` on Burner for Simple DVT module**. This role is required for ability to burn stETH tokens in case of operator’s penalties, you can read more [here](https://docs.lido.fi/guides/protocol-levers/#burning-steth-tokens)

6. **Add Simple DVT module to StakingRouter**. This action finally sets up new Simple DVT module contract to the [StakingRouter](https://etherscan.io/address/0xFdDf38947aFB03C621C71b06C9C70bce73f12999) as the second module


### IV. Grant permissions to EasyTrackEVMScriptExecutor to make operational changes to Simple DVT module

7. **Create and grant permission `MANAGE_NODE_OPERATOR_ROLE` on Simple DVT module for [EasyTrackEVMScriptExecutor](https://etherscan.io/address/0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977)**. This one and next 3 actions are needed to setup permissions required for [EasyTrack](https://etherscan.io/address/0xF0211b7660680B49De1A7E9f25C65660F0a13Fea) to manage operational tasks on the Simple DVT module

8. **Create and grant permission `SET_NODE_OPERATOR_LIMIT_ROLE` on Simple DVT module for EasyTrackEVMScriptExecutor**

9. **Create and grant permission `MANAGE_SIGNING_KEYS` on Simple DVT module for EasyTrackEVMScriptExecutor**

10. **Grant `STAKING_ROUTER_ROLE` on Simple DVT module for EasyTrackEVMScriptExecutor**


### V. Add Easy Track EVM script factories for Simple DVT module to EasyTrack registry

11. **Add AddNodeOperators EVM script factory** with address [0xcAa3AF7460E83E665EEFeC73a7a542E5005C9639](https://etherscan.io/address/0xcAa3AF7460E83E665EEFeC73a7a542E5005C9639)

12. **Add ActivateNodeOperators EVM script factory** with address [0xCBb418F6f9BFd3525CE6aADe8F74ECFEfe2DB5C8](https://etherscan.io/address/0xCBb418F6f9BFd3525CE6aADe8F74ECFEfe2DB5C8)

13. **Add DeactivateNodeOperators EVM script factory** with address [0x8B82C1546D47330335a48406cc3a50Da732672E7](https://etherscan.io/address/0x8B82C1546D47330335a48406cc3a50Da732672E7)

14. **Add SetVettedValidatorsLimits EVM script factory** with address [0xD75778b855886Fc5e1eA7D6bFADA9EB68b35C19D](https://etherscan.io/address/0xD75778b855886Fc5e1eA7D6bFADA9EB68b35C19D)

15. **Add UpdateTargetValidatorLimits EVM script factory** with address [0x41CF3DbDc939c5115823Fba1432c4EC5E7bD226C](https://etherscan.io/address/0x41CF3DbDc939c5115823Fba1432c4EC5E7bD226C)

16. **Add SetNodeOperatorNames EVM script factory** with address [0x7d509BFF310d9460b1F613e4e40d342201a83Ae4](https://etherscan.io/address/0x7d509BFF310d9460b1F613e4e40d342201a83Ae4)

17. **Add SetNodeOperatorRewardAddresses EVM script factory** with address [0x589e298964b9181D9938B84bB034C3BB9024E2C0](https://etherscan.io/address/0x589e298964b9181D9938B84bB034C3BB9024E2C0)

18. **Add ChangeNodeOperatorManagers EVM script factory** with address [0xE31A0599A6772BCf9b2bFc9e25cf941e793c9a7D](https://etherscan.io/address/0xE31A0599A6772BCf9b2bFc9e25cf941e793c9a7D)


### VI. Update Oracle Report Sanity Checker parameters

19. **Grant `MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE` to the [Lido DAO Agent](https://etherscan.io/address/0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c) on [OracleReportSanityChecker](https://etherscan.io/address/0x9305c1Dbfe22c12c66339184C0025d7006f0f1cC) contract**. This makes possible to set sanity checker parameter values (see next actions)

20. **Grant `MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE` to the `Lido DAO Agent` on `OracleReportSanityChecker` contract**

22. **Set `maxAccountingExtraDataListItemsCount` sanity checker parameter to 4**. This will allow to report extra data for 2 modules in 3rd phase of the accounting oracle report simultaneously

22. **Set `maxNodeOperatorsPerExtraDataItemCount` sanity checker parameter to `50`**. Limiting the number of operators guarantees a successful oracle report within the block gas limit
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Create new Aragon DAO Application Repo for Simple DVT
        #
        (
            "1) Create new Aragon DAO Application Repo for Simple DVT app",
            create_new_app_repo(
                name=create_simple_dvt_app["name"],
                manager=contracts.voting,
                version=create_simple_dvt_app["version"],
                address=create_simple_dvt_app["new_address"],
                content_uri=create_simple_dvt_app["content_uri"],
            ),
        ),
        #
        # II. Setup and initialize Simple DVT module as new Aragon app
        #
        (
            "2) Setup Simple DVT module as Aragon DAO app",
            update_app_implementation(create_simple_dvt_app["id"], create_simple_dvt_app["new_address"]),
        ),
        (
            "3) Initialize of Simple DVT module",
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
        # III. Add Simple DVT module to Staking Router
        #
        (
            "4) *Create and grant permission STAKING_ROUTER_ROLE on Simple DVT module for StakingRouter",
            encode_permission_create(
                entity=contracts.staking_router,
                target_app=contracts.simple_dvt,
                permission_name="STAKING_ROUTER_ROLE",
                manager=contracts.voting,
            ),
        ),
        (
            "5) Grant REQUEST_BURN_SHARES_ROLE on Burner for Simple DVT module",
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
            "6) Add Simple DVT module to StakingRouter",
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
            "7) Create and grant permission MANAGE_NODE_OPERATOR_ROLE on Simple DVT module for EasyTrackEVMScriptExecutor",
            encode_permission_create(
                entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="MANAGE_NODE_OPERATOR_ROLE",
                manager=contracts.voting,
            ),
        ),
        (
            "8) Create and grant permission SET_NODE_OPERATOR_LIMIT_ROLE on Simple DVT module for EasyTrackEVMScriptExecutor",
            encode_permission_create(
                entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="SET_NODE_OPERATOR_LIMIT_ROLE",
                manager=contracts.voting,
            ),
        ),
        (
            "9) Create and grant permission MANAGE_SIGNING_KEYS on Simple DVT module for EasyTrackEVMScriptExecutor",
            encode_permission_create(
                entity=EASYTRACK_EVMSCRIPT_EXECUTOR,
                target_app=contracts.simple_dvt,
                permission_name="MANAGE_SIGNING_KEYS",
                manager=EASYTRACK_EVMSCRIPT_EXECUTOR,
            ),
        ),
        (
            "10) Grant STAKING_ROUTER_ROLE on Simple DVT module for EasyTrackEVMScriptExecutor",
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
            "19) Grant MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT_ROLE to the Lido DAO Agent on OracleReportSanityChecker contract",
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
            "20) Grant MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT_ROLE to the Lido DAO Agent on OracleReportSanityChecker contract",
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
