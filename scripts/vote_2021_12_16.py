"""
Voting 16/12/2021.

1. Burn 33.827287 stETH shares on treasury address 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to compensate for Chorus validation penalties


"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script

from utils.config import get_deployer_account, contracts

def burn_shares(burn_address):
    # Chorus sent 33.827287 stETH by two transactions:
    # 1. https://etherscan.io/tx/0xfb8da61b72ee87d862ffb12c6d453887120084749fcee1a718de42c2bc555ba3
    # 2. https://etherscan.io/tx/0xd715e946f51bd82d5a84d87bbc8469413b751fbeaa1eafb73e28be7ff1a86638
    #
    # we calculated shares on the latest block 13804410: 
    # stethAmount = 33.827287 * 10^18
    # lido.getSharesByPooledEth(stethAmount) = 32145684728326685744

    sharesToBurn = 32145684728326685744
    lido = contracts.lido

    return (
        lido.address,
        lido.burnShares.encode_input(
            burn_address,
            sharesToBurn
        )
    )

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    encoded_call_script = encode_call_script([
        # 1. Burn 33.827287 stETH shares on treasury address 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c 
        #    to compensate for Chorus validation penalties
        burn_shares('0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c')
    ])

    if not confirm_vote_script(encoded_call_script, silent):
        return (-1, None)

    return create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Burn 33.827287 stETH shares on treasury address 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c.'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )

def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'max_fee': '100 gwei',
        'priority_fee': '2 gwei'
    })

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5) # hack for waiting thread #2.
