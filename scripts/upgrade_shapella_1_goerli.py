"""
Voting 24/03/2023.

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

from utils.shapella_upgrade import prepare_for_voting
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.repo import (
    add_implementation_to_lido_app_repo,
    add_implementation_to_nos_app_repo,
    add_implementation_to_oracle_app_repo,
)
from utils.kernel import update_app_implementation
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    lido_dao_staking_router,
    ContractsLazyLoader,
    lido_dao_withdrawal_vault,
    lido_dao_withdrawal_vault_implementation,
)
from utils.permissions import encode_permission_create, encode_permission_revoke

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


# TODO: set content_uri
update_lido_app = {
    "new_address": "0xEE227CC91A769881b1e81350224AEeF7587eBe76",
    "content_uri": "0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053",
    "id": "0x79ac01111b462384f1b7fba84a17b9ec1f5d2fddcfcb99487d71b443832556ea",
    "version": (10, 0, 0),
}

update_nos_app = {
    "new_address": "0xCAfe9Ac6a4bE2eAfCFf949693C0da9eebF985C3B",
    "content_uri": "0x697066733a516d61375058486d456a346a7332676a4d3976744850747176754b3832695335455950694a6d7a4b4c7a55353847",
    "id": "0x57384c8fcaf2c1c2144974769a6ea4e5cf69090d47f5327f8fc93827f8c0001a",
    "version": (8, 0, 0),
}

update_oracle_app = {
    "new_address": "0xcF9d64942DC9096520a8962a2d4496e680c6403b",
    "content_uri": "0x697066733a516d554d506669454b71354d786d387932475951504c756a47614a69577a31747665703557374564414767435238",
    "id": "0xb2977cfc13b000b6807b9ae3cf4d938f4cc8ba98e1d68ad911c58924d6aa4f11",
    "version": (5, 0, 0),
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

    template_address = ContractsLazyLoader.upgrade_template
    assert template_address != "", "Upgrade template must be deployed preliminary"

    voting: interface.Voting = contracts.voting
    node_operators_registry: interface.NodeOperatorsRegistry = contracts.node_operators_registry

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
        add_implementation_to_nos_app_repo(
            update_nos_app["version"], update_nos_app["new_address"], update_nos_app["content_uri"]
        ),
        # 6)
        update_app_implementation(update_nos_app["id"], update_nos_app["new_address"]),
        # 7)
        add_implementation_to_oracle_app_repo(
            update_oracle_app["version"], update_oracle_app["new_address"], update_oracle_app["content_uri"]
        ),
        # 8)
        update_app_implementation(update_oracle_app["id"], update_oracle_app["new_address"]),
        # 9)
        encode_permission_create(
            entity=lido_dao_staking_router,
            target_app=node_operators_registry,
            permission_name="STAKING_ROUTER_ROLE",
            manager=voting,
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
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
