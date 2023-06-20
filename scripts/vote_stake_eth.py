"""
Voting

1) Stake all Lido Agents ETH
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_execute
from brownie import ZERO_ADDRESS

from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    get_priority_fee,
)


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    current_agent_balance = contracts.agent.balance()

    submit_calldata = contracts.lido.submit.encode_input(ZERO_ADDRESS)
    print(
            contracts.lido.address,
            current_agent_balance,
            'Staking all Lido Agents ETH'
        )
    call_script_items = [
        agent_execute(
            target=contracts.lido.address,
            value=current_agent_balance,
            data=submit_calldata
        ),
    ]

    vote_desc_items = [
        "1) Stake all Lido Agents ETH"
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
