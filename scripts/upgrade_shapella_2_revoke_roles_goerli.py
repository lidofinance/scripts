"""

Voting 24/03/2023.

Lido V2 (Shapella-ready) protocol upgrade on Görli

1. Call `ShapellaUpgradeTemplate.assertUpgradeIsFinishedCorrectly()`
2. Revoke `MANAGE_FEE` role from `Voting`
3. Revoke `MANAGE_WITHDRAWAL_KEY` role from `Voting`
4. Revoke `MANAGE_PROTOCOL_CONTRACTS_ROLE` role from `Voting`
5. Revoke `SET_EL_REWARDS_VAULT_ROLE` role from `Voting`
6. Revoke `SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE` role from `Voting`
7. Revoke `ADD_NODE_OPERATOR_ROLE` role from `Voting`
8. Revoke `SET_NODE_OPERATOR_ACTIVE_ROLE` role from `Voting`
9. Revoke `SET_NODE_OPERATOR_NAME_ROLE` role from `Voting`
10. Revoke `SET_NODE_OPERATOR_ADDRESS_ROLE` role from `Voting`
11. Revoke `REPORT_STOPPED_VALIDATORS_ROLE` role from `Voting`
12. Revoke `MANAGE_MEMBERS` role from `Voting`
13. Revoke `MANAGE_QUORUM` role from `Voting`
14. Revoke `SET_BEACON_SPEC` role from `Voting`
15. Revoke `SET_REPORT_BOUNDARIES` role from `Voting`
16. Revoke `SET_BEACON_REPORT_RECEIVER` role from `Voting`

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import ShapellaUpgradeTemplate

from utils.shapella_upgrade import prepare_for_voting
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    ContractsLazyLoader,
)
from utils.permissions import encode_permission_revoke

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


def encode_template_check_upgrade_finished(template_address: str) -> Tuple[str, str]:
    template = ShapellaUpgradeTemplate.at(template_address)
    return template.address, template.revertIfUpgradeNotFinished.encode_input()


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting: interface.Voting = contracts.voting
    lido: interface.Lido = contracts.lido
    lido_oracle: interface.LegacyOracle = contracts.legacy_oracle
    node_operators_registry: interface.NodeOperatorsRegistry = contracts.node_operators_registry

    call_script_items = [
        # TODO
        encode_template_check_upgrade_finished(ContractsLazyLoader.upgrade_template),
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
        "1) Call `ShapellaUpgradeTemplate.assertUpgradeIsFinishedCorrectly()`",
        "2) Revoke `MANAGE_FEE` role from `Voting`",
        "3) Revoke `MANAGE_WITHDRAWAL_KEY` role from `Voting`",
        "4) Revoke `MANAGE_PROTOCOL_CONTRACTS_ROLE` role from `Voting`",
        "5) Revoke `SET_EL_REWARDS_VAULT_ROLE` role from `Voting`",
        "6) Revoke `SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE` role from `Voting`",
        "7) Revoke `ADD_NODE_OPERATOR_ROLE` role from `Voting`",
        "8) Revoke `SET_NODE_OPERATOR_ACTIVE_ROLE` role from `Voting",
        "9) Revoke `SET_NODE_OPERATOR_NAME_ROLE` role from `Voting`",
        "10) Revoke `SET_NODE_OPERATOR_ADDRESS_ROLE` role from `Voting`",
        "11) Revoke `REPORT_STOPPED_VALIDATORS_ROLE` role from `Voting`",
        "12) Revoke `MANAGE_MEMBERS` role from `Voting`",
        "13) Revoke `MANAGE_QUORUM` role from `Voting`",
        "14) Revoke `SET_BEACON_SPEC` role from `Voting`",
        "15) Revoke `SET_REPORT_BOUNDARIES` role from `Voting`",
        "16) Revoke `SET_BEACON_REPORT_RECEIVER` role from `Voting`",
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
