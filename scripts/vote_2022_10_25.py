"""
Voting 25/10/2022.

1. Send DAI 732,710 from Lido DAO Treasury to the RCC multisig wallet 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
2. Send LDO 50,311 from Lido DAO Treasury to the RCC multisig wallet 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
3. Wrap 11 ETH from Lido DAO Treasury to WETH
4. Send 11 WETH from Lido DAO Treasury to the bloXroute address 0xea48ba2edefae9e4ddd43ea565aa8b9aa22baf08

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
from utils.finance import make_ldo_payout, make_weth_payout, make_dai_payout
from utils.brownie_prelude import *

rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
bloxroute_address = "0xea48ba2edefae9e4ddd43ea565aa8b9aa22baf08"
eth_amount: int = 11 * (10**18)
ldo_amount: int = 50_311 * (10**18)
dai_amount: int = 732_710 * (10**18)


def encode_weth_wrap_agent_execute_call(agent, eth_amount):
    weth_token = interface.WethToken(weth_token_address)
    weth_calldata = weth_token.deposit.encode_input()
    calldata = agent.execute.encode_input(weth_token_address, eth_amount, weth_calldata)

    return (
        agent.address,
        calldata,
    )


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    agent = interface.Agent(lido_dao_agent_address)

    call_script_items = [
        # 1. Send DAI 732,710 from Lido DAO Treasury to the RCC multisig wallet 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_dai_payout(
            target_address=rcc_multisig_address,
            dai_in_wei=dai_amount,
            reference="RCC Multisig Oct DAI Payout",
        ),
        # 2. Send LDO 50,311 from Lido DAO Treasury to the RCC multisig wallet 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_ldo_payout(
            target_address=rcc_multisig_address,
            ldo_in_wei=ldo_amount,
            reference="RCC Multisig Oct LDO Payout",
        ),
        # 3. Wrap 11 ETH from Lido DAO Treasury to WETH
        encode_weth_wrap_agent_execute_call(agent, eth_amount),
        # 4. Send 11 WETH from Lido DAO Treasury to the bloXroute address 0xea48ba2edefae9e4ddd43ea565aa8b9aa22baf08
        make_weth_payout(
            target_address=bloxroute_address,
            weth_in_wei=eth_amount,
            reference="Return 11 ETH back to bloXroute (in WETH form)",
        ),
    ]

    # NB: In case of single vote item the ending period is added automatically
    vote_desc_items = [
        "1) Send DAI 732,710 to the RCC multisig wallet 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
        "2) Send LDO 50,311 to the RCC multisig wallet 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
        "3) Wrap 11 ETH to WETH",
        "4) Send 11 WETH to the bloXroute address 0xea48ba2edefae9e4ddd43ea565aa8b9aa22baf08",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "100 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
