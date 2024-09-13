"""

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import interface
from utils.agent import agent_forward
from utils.finance import make_steth_payout
from utils.node_operators import encode_set_node_operator_name
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    STAKING_ROUTER,
    WITHDRAWAL_VAULT,
    WITHDRAWAL_VAULT_IMPL,
    SELF_OWNED_STETH_BURNER,
    get_priority_fee,
)

from utils.easy_track import (
    set_motions_count_limit
)

def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    ANYBLOCKANALYTICS_ID = 12
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    motionsCountLimit = 20

    REWARDS_MULTISIG_ADDRESS = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
    REWARDS_JUNE_BUDGET = 170*1e18

    NO_registry = interface.NodeOperatorsRegistry(contracts.node_operators_registry)
    prysmatic_labs_node_id = 27
    prysmatic_labs_node_new_name = "Prysm Team at Offchain Labs"

    call_script_items = [
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.grantRole.encode_input(STAKING_MODULE_MANAGE_ROLE, contracts.agent.address),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.updateTargetValidatorsLimits.encode_input(1, ANYBLOCKANALYTICS_ID, True, 0),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.renounceRole.encode_input(STAKING_MODULE_MANAGE_ROLE, contracts.agent.address),
                )
            ]
        ),
        make_steth_payout(
            target_address=REWARDS_MULTISIG_ADDRESS,
            steth_in_wei=REWARDS_JUNE_BUDGET,
            reference='reWARDS June budget'
        ),
        set_motions_count_limit(motionsCountLimit),
        agent_forward([
            encode_set_node_operator_name(
                prysmatic_labs_node_id,
                prysmatic_labs_node_new_name,
                NO_registry
            )
        ]),
    ]

    vote_desc_items = [
        "1) ...",
        "2) ...",
        "3) ...",
        "4) ...",
        "5) ...",
        "6) ...",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
