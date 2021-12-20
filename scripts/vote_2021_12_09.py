"""
Voting 09/12/2021.

1. Top up Curve LP reward program with 3,550,000 LDO to 0x753D5167C31fBEB5b49624314d74A957Eb271709.
2. Top up Balancer LP reward program with 300,000 LDO to address 0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8
3. Top up Sushi LP reward program with 50,000 LDO to 0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4
4. Referral program payout of 140,414 LDO to financial multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

Vote passed & executed on 2021-12-10, 15:34, block 13777444.

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.finance import make_ldo_payout
from utils.evm_script import encode_call_script

from utils.config import get_deployer_account

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    encoded_call_script = encode_call_script([
        # 1. Top up Curve LP reward program with 3,550,000 LDO to 0x753D5167C31fBEB5b49624314d74A957Eb271709

        make_ldo_payout(
            target_address='0x753D5167C31fBEB5b49624314d74A957Eb271709',
            ldo_in_wei=3_550_000 * (10 ** 18),
            reference='Curve LP reward program'
        ),

        # 2. Top up Balancer LP reward program with 300,000 LDO to 0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8

        make_ldo_payout(
            target_address='0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8',
            ldo_in_wei=300_000 * (10 ** 18),
            reference="Balancer LP reward program"
        ),

        # 3. Top up Sushi LP reward program with 50,000 LDO to 0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4

        make_ldo_payout(
            target_address='0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4',
            ldo_in_wei=50_000 * (10 ** 18),
            reference="Sushi LP reward program"
        ),

        # 4. Referral program payout of 140,414 LDO to financial multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

        make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=140_414 * (10 ** 18),
            reference="Tenth period referral rewards"
        )
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Top up Curve LP reward program with 3,550,000 LDO;'
            '2) Top up Balancer LP reward program with 300,000 LDO;'
            '3) Top up Sushi LP reward program with 50,000 LDO;'
            '4) Allocate 140,414 LDO to the financial multisig for 10th period referral rewards.'
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
