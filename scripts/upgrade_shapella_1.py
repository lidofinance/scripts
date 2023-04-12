"""
Voting ??/05/2023.

Lido V2 (Shapella-ready) protocol upgrade on Görli

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
    lido_dao_staking_router,
    lido_dao_withdrawal_vault,
    lido_dao_withdrawal_vault_implementation,
    get_priority_fee,
)
from utils.permissions import encode_permission_create

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


update_lido_app = {
    "new_address": "0xE5418393B2D9D36e94b7a8906Fb2e4E9dce9DEd3",
    # TODO: set content_uri after Aragon UI deployment
    "content_uri": "0x697066733a516d63354a64475a3576326844466d64516844535a70514a6554394a55364e34386d5678546474685667677a766d",
    "id": "0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320",
    "version": (4, 0, 0),
}

update_nor_app = {
    "new_address": "0x18Ce1d296Cebe2596A5c295202a195F898021E5D",
    # TODO: set content_uri after Aragon UI deployment
    "content_uri": "0x697066733a516d5342796b4e4a61363734547146334b7366677642666444315a545158794c4a6e707064776b36477463534c4d",
    "id": "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d",
    "version": (4, 0, 0),
}

update_oracle_app = {
    "new_address": "0xCb461e10f5AD0575172e7261589049e44aAf209B",
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


def start_vote(
    tx_params: Dict[str, str], silent: bool, template_address: str = None
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    # TODO: when the template is deployed remove the if-else setup
    if template_address is None:
        if contracts.shapella_upgrade_template is None:
            # Deterministic address from dev local-fork deployment
            template_address = "0xc601E93D9F48D5E374820957CdA57516e2523d6C"
        else:
            # Use pre-deployed template specified in config
            template_address = contracts.shapella_upgrade_template.address

    call_script_items = [
        # 1)
        encode_withdrawal_vault_proxy_update(lido_dao_withdrawal_vault, lido_dao_withdrawal_vault_implementation),
        # 2)
        encode_template_start_upgrade(template_address),
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
        encode_permission_create(
            entity=lido_dao_staking_router,
            target_app=contracts.node_operators_registry,
            permission_name="STAKING_ROUTER_ROLE",
            manager=contracts.voting,
        ),
        # 10)
        encode_template_finish_upgrade(template_address),
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
        "10) Finalize upgrade by calling `ShapellaUpgradeTemplate.finalizeUpgrade()`",
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
