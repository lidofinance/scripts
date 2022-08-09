"""
Voting 09/08/2022.

1. Wrap $1,117,380.00 +5% ETH to WETH
2. Send $1,117,380.00 +5% in WETH to the RCC multisig 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
3. Send 67,017.32 LDO to the RCC multisig 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.config import (
    get_deployer_account,
    get_is_live,
    lido_dao_agent_address,
    weth_token_address,
)
from utils.finance import make_ldo_payout, make_weth_payout
from utils.brownie_prelude import *

rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
eth_amount: int = 700 * (10**18)  # 1_117_380 * 1.05 / 1700
ldo_amount: int = 67_017.32 * (10**18)


def encode_weth_wrap_agent_execute_call(agent, weth_token):
    weth_calldata = weth_token.deposit.encode_input()
    calldata = agent.execute.encode_input(weth_token_address, eth_amount, weth_calldata)

    return (
        agent.address,
        calldata,
    )


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    agent = interface.Agent(lido_dao_agent_address)
    weth_token = interface.WethToken(weth_token_address)

    call_script_items = [
        # 1. Send $1,117,380.00 +5% in ETH to the RCC multisig 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        encode_weth_wrap_agent_execute_call(agent, weth_token),
        # 2. Send $1,117,380.00 +5% in WETH to the RCC multisig 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_weth_payout(
            target_address=rcc_multisig_address, weth_in_wei=eth_amount, reference="RCC Multisig Jul-Sep Payout"
        ),
        # 3. Send 67,017.32 LDO to the RCC multisig 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_ldo_payout(
            target_address=rcc_multisig_address, ldo_in_wei=ldo_amount, reference="RCC Multisig Jul-Sep Payout"
        ),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Wrap $1,117,380.00 +5% ETH to WETH",
        "2) Send $1,117,380.00 +5% in WETH to the RCC multisig 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
        "3) Send 67,017.32 LDO to the RCC multisig 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
