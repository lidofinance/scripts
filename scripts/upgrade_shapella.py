"""
Voting 12/05/2023.

Lido V2 (Shapella-ready) protocol upgrade

1. Update `WithdrawalVault` proxy implementation
2. Call `ShapellaUpgradeTemplate.startUpgrade()`
3. Publish new `Lido` implementation in Lido app APM repo
4. Update `Lido` implementation
5. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo
6. Update `NodeOperatorsRegistry` implementation
7. Publish new `LidoOracle` implementation in LidoOracle app APM repo
8. Update `LidoOracle` implementation to `LegacyOracle`
9. Create new role `STAKING_ROLE_ROLE` and assign to `StakingRouter`
10. Call `ShapellaUpgradeTemplate.finishUpgrade()`
11. Revoke `MANAGE_FEE` role from `Voting`
12. Revoke `MANAGE_WITHDRAWAL_KEY` role from `Voting`
13. Revoke `MANAGE_PROTOCOL_CONTRACTS_ROLE` role from `Voting`
14. Revoke `SET_EL_REWARDS_VAULT_ROLE` role from `Voting`
15. Revoke `SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE` role from `Voting`
16. Revoke `DEPOSIT_ROLE` role from old `DepositSecurityModule`
17. Revoke `BURN_ROLE` role from `SelfOwnedStETHBurner`
18. Revoke `ADD_NODE_OPERATOR_ROLE` role from `Voting`
19. Revoke `SET_NODE_OPERATOR_ACTIVE_ROLE` role from `Voting`
20. Revoke `SET_NODE_OPERATOR_NAME_ROLE` role from `Voting`
21. Revoke `SET_NODE_OPERATOR_ADDRESS_ROLE` role from `Voting`
22. Revoke `REPORT_STOPPED_VALIDATORS_ROLE` role from `Voting`
23. Revoke `MANAGE_MEMBERS` role from `Voting`
24. Revoke `MANAGE_QUORUM` role from `Voting`
25. Revoke `SET_BEACON_SPEC` role from `Voting`
26. Revoke `SET_REPORT_BOUNDARIES` role from `Voting`
27. Revoke `SET_BEACON_REPORT_RECEIVER` role from `Voting`
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import ShapellaUpgradeTemplate

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.repo import (
    add_implementation_to_lido_app_repo,
    add_implementation_to_nor_app_repo,
    add_implementation_to_oracle_app_repo,
)
from utils.kernel import update_app_implementation
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    LIDO_STAKING_ROUTER,
    LIDO_WITHDRAWAL_VAULT,
    LIDO_WITHDRAWAL_VAULT_IMPL,
    LIDO_SELF_OWNED_STETH_BURNER,
    get_priority_fee,
)
from utils.permissions import encode_permission_create, encode_permission_revoke

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


update_lido_app = {
    "new_address": "0x17144556fd3424EDC8Fc8A4C940B2D04936d17eb",
    # TODO: set content_uri after Aragon UI deployment
    "content_uri": "0x697066733a516d63354a64475a3576326844466d64516844535a70514a6554394a55364e34386d5678546474685667677a766d",
    "id": "0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320",
    "version": (4, 0, 0),
}

update_nor_app = {
    "new_address": "0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed",
    # TODO: set content_uri after Aragon UI deployment
    "content_uri": "0x697066733a516d5342796b4e4a61363734547146334b7366677642666444315a545158794c4a6e707064776b36477463534c4d",
    "id": "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d",
    "version": (4, 0, 0),
}

update_oracle_app = {
    "new_address": "0xa29b819654cE6224A222bb5f586920105E2D7E0E",
    # TODO: set content_uri after Aragon UI deployment
    "content_uri": "0x697066733a516d66414348396f5348465767563831446838525356636761564264686b5a7548685a5932695a76357379424a4b",
    "id": "0x8b47ba2a8454ec799cd91646e7ec47168e91fd139b23f017455f3e5898aaba93",
    "version": (4, 0, 0),
}


def encode_template_start_upgrade(template_address: str) -> Tuple[str, str]:
    template = ShapellaUpgradeTemplate.at(template_address)
    return template.address, template.startUpgrade.encode_input()


def encode_template_finish_upgrade(template_address: str) -> Tuple[str, str]:
    template = ShapellaUpgradeTemplate.at(template_address)
    return template.address, template.finishUpgrade.encode_input()


def encode_withdrawal_vault_proxy_update(vault_proxy_address: str, implementation: str) -> Tuple[str, str]:
    proxy = interface.WithdrawalVaultManager(vault_proxy_address)
    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b"")


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    voting = contracts.voting
    node_operators_registry = contracts.node_operators_registry
    lido = contracts.lido
    legacy_oracle = contracts.legacy_oracle

    call_script_items = [
        # 1)
        encode_withdrawal_vault_proxy_update(LIDO_WITHDRAWAL_VAULT, LIDO_WITHDRAWAL_VAULT_IMPL),
        # 2)
        encode_template_start_upgrade(contracts.shapella_upgrade_template),
        # 3)
        add_implementation_to_lido_app_repo(
            update_lido_app["version"], update_lido_app["new_address"], update_lido_app["content_uri"]
        ),
        # 4)
        update_app_implementation(update_lido_app["id"], update_lido_app["new_address"]),
        # 5)
        add_implementation_to_nor_app_repo(
            update_nor_app["version"], update_nor_app["new_address"], update_nor_app["content_uri"]
        ),
        # 6)
        update_app_implementation(update_nor_app["id"], update_nor_app["new_address"]),
        # 7)
        add_implementation_to_oracle_app_repo(
            update_oracle_app["version"], update_oracle_app["new_address"], update_oracle_app["content_uri"]
        ),
        # 8)
        update_app_implementation(update_oracle_app["id"], update_oracle_app["new_address"]),
        # 9)
        encode_permission_create(LIDO_STAKING_ROUTER, node_operators_registry, "STAKING_ROUTER_ROLE", manager=voting),
        # 10)
        encode_template_finish_upgrade(contracts.shapella_upgrade_template),
        # 11)
        encode_permission_revoke(lido, "MANAGE_FEE", revoke_from=voting),
        # 12)
        encode_permission_revoke(lido, "MANAGE_WITHDRAWAL_KEY", revoke_from=voting),
        # 13)
        encode_permission_revoke(lido, "MANAGE_PROTOCOL_CONTRACTS_ROLE", revoke_from=voting),
        # 14)
        encode_permission_revoke(lido, "SET_EL_REWARDS_VAULT_ROLE", revoke_from=voting),
        # 15)
        encode_permission_revoke(lido, "SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE", revoke_from=voting),
        # 16)
        encode_permission_revoke(lido, "DEPOSIT_ROLE", revoke_from=contracts.deposit_security_module_v1),
        # 17)
        encode_permission_revoke(lido, "BURN_ROLE", revoke_from=LIDO_SELF_OWNED_STETH_BURNER),
        # 18)
        encode_permission_revoke(node_operators_registry, "ADD_NODE_OPERATOR_ROLE", revoke_from=voting),
        # 19)
        encode_permission_revoke(node_operators_registry, "SET_NODE_OPERATOR_ACTIVE_ROLE", revoke_from=voting),
        # 20)
        encode_permission_revoke(node_operators_registry, "SET_NODE_OPERATOR_NAME_ROLE", revoke_from=voting),
        # 21)
        encode_permission_revoke(node_operators_registry, "SET_NODE_OPERATOR_ADDRESS_ROLE", revoke_from=voting),
        # 22)
        encode_permission_revoke(node_operators_registry, "REPORT_STOPPED_VALIDATORS_ROLE", revoke_from=voting),
        # 23)
        encode_permission_revoke(legacy_oracle, "MANAGE_MEMBERS", revoke_from=voting),
        # 24)
        encode_permission_revoke(legacy_oracle, "MANAGE_QUORUM", revoke_from=voting),
        # 25)
        encode_permission_revoke(legacy_oracle, "SET_BEACON_SPEC", revoke_from=voting),
        # 26)
        encode_permission_revoke(legacy_oracle, "SET_REPORT_BOUNDARIES", revoke_from=voting),
        # 27)
        encode_permission_revoke(legacy_oracle, "SET_BEACON_REPORT_RECEIVER", revoke_from=voting),
    ]

    vote_desc_items = [
        "1) Update `WithdrawalVault` proxy implementation",
        "2) Call `ShapellaUpgradeTemplate.startUpgrade()",
        "3) Publish new implementation in Lido app APM repo",
        "4) Updating implementation of Lido app",
        "5) Publishing new implementation in Node Operators Registry app APM repo",
        "6) Updating implementation of Node Operators Registry app",
        "7) Publishing new implementation in Oracle app APM repo",
        "8) Updating implementation of Oracle app",
        "9) Create permission for STAKING_ROUTER_ROLE of NodeOperatorsRegistry assigning it to StakingRouter",
        "10) Finish upgrade by calling `ShapellaUpgradeTemplate.finishUpgrade()`",
        "11) Revoke `MANAGE_FEE` role from `Voting`",
        "12) Revoke `MANAGE_WITHDRAWAL_KEY` role from `Voting`",
        "13) Revoke `MANAGE_PROTOCOL_CONTRACTS_ROLE` role from `Voting`",
        "14) Revoke `SET_EL_REWARDS_VAULT_ROLE` role from `Voting`",
        "15) Revoke `SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE` role from `Voting`",
        "16) Revoke `DEPOSIT_ROLE` role from old `DepositSecurityModule`",
        "17) Revoke `BURN_ROLE` role from `SelfOwnedStETHBurner`",
        "18) Revoke `ADD_NODE_OPERATOR_ROLE` role from `Voting`",
        "19) Revoke `SET_NODE_OPERATOR_ACTIVE_ROLE` role from `Voting",
        "20) Revoke `SET_NODE_OPERATOR_NAME_ROLE` role from `Voting`",
        "21) Revoke `SET_NODE_OPERATOR_ADDRESS_ROLE` role from `Voting`",
        "22) Revoke `REPORT_STOPPED_VALIDATORS_ROLE` role from `Voting`",
        "23) Revoke `MANAGE_MEMBERS` role from `Voting`",
        "24) Revoke `MANAGE_QUORUM` role from `Voting`",
        "25) Revoke `SET_BEACON_SPEC` role from `Voting`",
        "26) Revoke `SET_REPORT_BOUNDARIES` role from `Voting`",
        "27) Revoke `SET_BEACON_REPORT_RECEIVER` role from `Voting`",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
