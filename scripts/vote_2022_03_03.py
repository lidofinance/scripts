"""
Voting 03/03/2022.

1. Referral program payout of 412,082 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

Vote passed & executed on Mar-04-2022 12:20:58 PM +UTC, block #14320412.
TX URL: https://etherscan.io/tx/0x26260b616ece73da2b76129130d0b63b622efee2623c38e17ab31bd1963afa4e

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
        # 1. Referral program payout of 412,082 LDO to financial multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
        make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=412_082 * (10 ** 18),
            reference="16th period referral rewards"
        ),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Allocate 412,082 LDO tokens for the 16th period referral rewards.'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'max_fee': '300 gwei',
        'priority_fee': '2 gwei'
    })

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5)  # hack for waiting thread #2.
