"""
TODO description
Voting 23/03/2023.

Shapella Protocol Upgrade

1. Publishing new implementation (0x47EbaB13B806773ec2A2d16873e2dF770D130b50) in Lido app APM repo
2. Updating implementation of Lido app with the new one
3. Publishing new implementation (0x5d39ABaa161e622B99D45616afC8B837E9F19a25) in Node Operators Registry app APM repo
4. Updating implementation of Node Operators Registry app with the new one
5. Publishing new implementation (0x1430194905301504e8830ce4B0b0df7187E84AbD) in Oracle app APM repo
6. Updating implementation of Oracle app with new one

# 7. Call Oracle's finalizeUpgrade_v3() to update internal version counter.
# 8. Create permission for SET_EL_REWARDS_VAULT_ROLE of Lido app assigning it to Voting

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
    network_name,
)
from utils.permissions import encode_permission_create, encode_permission_revoke

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


DEPLOYER_EOA = "0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1"
STAKING_ROUTER = "0x2fa2Cdd94C11B0e8B50205E1F304e97D9797ae09"


# TODO: set content_uri
update_lido_app = {
    "new_address": "0xf798159E0908FB988220eFbab94985De68F4FB55",
    "content_uri": "0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053",
    "id": "0x79ac01111b462384f1b7fba84a17b9ec1f5d2fddcfcb99487d71b443832556ea",
    "version": (10, 0, 0),
}

update_nos_app = {
    "new_address": "0x1fE9E1015DBa106B4dc9d6B7C206aA66129b0a9f",
    "content_uri": "0x697066733a516d61375058486d456a346a7332676a4d3976744850747176754b3832695335455950694a6d7a4b4c7a55353847",
    "id": "0x57384c8fcaf2c1c2144974769a6ea4e5cf69090d47f5327f8fc93827f8c0001a",
    "version": (8, 0, 0),
}

update_oracle_app = {
    "new_address": "0x37d30AB66797326FEb4A80E413cAe8b569eCf460",
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


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    template = prepare_for_voting(DEPLOYER_EOA)
    template_address = template.address

    # TODO: add upgrade_ prefix to the voting script to enable snapshot tests

    voting: interface.Voting = contracts.voting
    lido: interface.Lido = contracts.lido
    lido_oracle: interface.LegacyOracle = contracts.legacy_oracle
    node_operators_registry: interface.NodeOperatorsRegistry = contracts.node_operators_registry

    call_script_items = [
        # TODO
        encode_template_start_upgrade(template_address),
        # 1. Publishing new implementation(TODO)
        #                   in Lido app APM repo 0xF5Dc67E54FC96F993CD06073f71ca732C1E654B1
        add_implementation_to_lido_app_repo(
            update_lido_app["version"], update_lido_app["new_address"], update_lido_app["content_uri"]
        ),
        # 2. Updating implementation of Lido app with the new one TODO
        update_app_implementation(update_lido_app["id"], update_lido_app["new_address"]),
        # 3. Publishing new implementation (TODO)
        #                   in Node Operators Registry app APM repo 0x0D97E876ad14DB2b183CFeEB8aa1A5C788eB1831
        add_implementation_to_nos_app_repo(
            update_nos_app["version"], update_nos_app["new_address"], update_nos_app["content_uri"]
        ),
        # 4. Updating implementation of Node Operators Registry app
        #                   with the new one TODO
        update_app_implementation(update_nos_app["id"], update_nos_app["new_address"]),
        # 5. Publishing new implementation (TODO)
        #     in Oracle app APM repo 0xF9339DE629973c60c4d2b76749c81E6F40960E3A
        add_implementation_to_oracle_app_repo(
            update_oracle_app["version"], update_oracle_app["new_address"], update_oracle_app["content_uri"]
        ),
        # 6. Updating implementation of Oracle app with new one TODO
        update_app_implementation(update_oracle_app["id"], update_oracle_app["new_address"]),
        # 7. Create permission for SET_EL_REWARDS_VAULT_ROLE of Lido app
        #    assigning it to Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
        encode_permission_create(
            entity=STAKING_ROUTER,
            target_app=node_operators_registry,
            permission_name="STAKING_ROUTER_ROLE",
            manager=voting,
        ),
        # 8. Finalize upgrade via template
        encode_template_finish_upgrade(template_address),
        # 9+. Revoke obsolete roles
        # TODO: on goerli the list is larger
        encode_permission_revoke(lido, "MANAGE_FEE", revoke_from=voting),
        encode_permission_revoke(lido, "MANAGE_WITHDRAWAL_KEY", revoke_from=voting),
        encode_permission_revoke(lido, "MANAGE_PROTOCOL_CONTRACTS_ROLE", revoke_from=voting),
        encode_permission_revoke(lido, "SET_EL_REWARDS_VAULT_ROLE", revoke_from=voting),
        encode_permission_revoke(lido, "SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE", revoke_from=voting),
        encode_permission_revoke(node_operators_registry, "ADD_NODE_OPERATOR_ROLE", revoke_from=voting),
        encode_permission_revoke(node_operators_registry, "SET_NODE_OPERATOR_ACTIVE_ROLE", revoke_from=voting),
        encode_permission_revoke(node_operators_registry, "SET_NODE_OPERATOR_NAME_ROLE", revoke_from=voting),
        encode_permission_revoke(node_operators_registry, "SET_NODE_OPERATOR_ADDRESS_ROLE", revoke_from=voting),
        encode_permission_revoke(node_operators_registry, "REPORT_STOPPED_VALIDATORS_ROLE", revoke_from=voting),
        encode_permission_revoke(lido_oracle, "MANAGE_MEMBERS", revoke_from=voting),
        encode_permission_revoke(lido_oracle, "MANAGE_QUORUM", revoke_from=voting),
        encode_permission_revoke(lido_oracle, "SET_BEACON_SPEC", revoke_from=voting),
        encode_permission_revoke(lido_oracle, "SET_REPORT_BOUNDARIES", revoke_from=voting),
        encode_permission_revoke(lido_oracle, "SET_BEACON_REPORT_RECEIVER", revoke_from=voting),
    ]

    vote_desc_items = [
        "X) TODO startUpgrade",
        "1) Publish new implementation in Lido app APM repo",
        "2) Updating implementation of Lido app",
        "3) Publishing new implementation in Node Operators Registry app APM repo",
        "4) Updating implementation of Node Operators Registry app",
        "5) Publishing new implementation in Oracle app APM repo",
        "6) Updating implementation of Oracle app",
        "7) Create permission for STAKING_ROUTER_ROLE of NodeOperatorsRegistry assigning it to StakingRouter",
        "8) Finalize upgrade by calling finalizeUpgrade() of ShapellaUpgradeTemplate",
        "X) TODO revoke 1",
        "X) TODO revoke 2",
        "X) TODO revoke 3",
        "X) TODO revoke 4",
        "X) TODO revoke 5",
        "X) TODO revoke 6",
        "X) TODO revoke 7",
        "X) TODO revoke 8",
        "X) TODO revoke 9",
        "X) TODO revoke 10",
        "X) TODO revoke 11",
        "X) TODO revoke 12",
        "X) TODO revoke 13",
        "X) TODO revoke 14",
        "X) TODO revoke 15",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params)) + [template]


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
