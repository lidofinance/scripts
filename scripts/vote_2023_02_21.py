"""
Voting 21/02/2023.
1. Add TRP LDO top up EVM script factory 0xBd2b6dC189EefD51B273F5cb2d99BA1ce565fb8C to Easy Track
2. Set Staking limit for node operator Blockdaemon to 3800

"""

import time

from typing import Dict, Tuple, Optional, List

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.easy_track import add_evmscript_factory, create_permissions

from utils.config import (
    get_deployer_account,
    lido_dao_finance_address,
    lido_dao_node_operators_registry,
)
from utils.node_operators import (
    encode_set_node_operator_staking_limit
)

def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    finance = interface.Finance(lido_dao_finance_address)

    TRP_topup_factory = interface.TopUpAllowedRecipients("0xBd2b6dC189EefD51B273F5cb2d99BA1ce565fb8C")
    TRP_registry = interface.AllowedRecipientRegistry("0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8")

    NO_registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)
    Blockdaemon_id = 13
    Blockdaemon_limit = 3800

    call_script_items = [
        # 1. Add TRP LDO top up EVM script factory 0xBd2b6dC189EefD51B273F5cb2d99BA1ce565fb8C to Easy Track
        add_evmscript_factory(
            factory=TRP_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(TRP_registry, "updateSpentAmount")[2:],
        ),
        # 2. Set Staking limit for node operator Blockdaemon to 3800
        encode_set_node_operator_staking_limit(Blockdaemon_id, Blockdaemon_limit, NO_registry),
    ]

    vote_desc_items = [
        "1) Add TRP LDO top up EVM script factory 0xBd2b6dC189EefD51B273F5cb2d99BA1ce565fb8C to Easy Track",
        "2) Set Staking limit for node operator Blockdaemon to 3800",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
