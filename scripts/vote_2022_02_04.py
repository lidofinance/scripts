"""
Voting 04/02/2022.

1. Referral program payout of 180,278 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.finance import make_ldo_payout
from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.config import get_deployer_account


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    encoded_call_script = encode_call_script([
        # 1. Referral program payout of 180,278 LDO to financial multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
        make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=180_278 * (10 ** 18),
            reference="14th period referral rewards"
        )
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Allocate 180,278 LDO tokens for the 14th period referral rewards.'
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

    time.sleep(5)  # hack for waiting thread #2.
