"""
Voting 16/04/2022.

1. Send the equivalent of $1,057,755.00 (+5%) in stETH  to the RCC Multisig wallet address
0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437. The exact amount of stETH shall be determined when the Aragon vote is
initiated.

Vote passed & executed on Apr-22-2022 02:49:48 PM +UTC, block 14635310.

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.finance import make_steth_payout
from utils.evm_script import encode_call_script
from utils.config import (
    get_deployer_account,
    get_is_live
)


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    encoded_call_script = encode_call_script([
        # 1. Send the equivalent of $1,057,755.00 (+5%) in stETH  to the RCC Multisig wallet address
        # 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437.
        make_steth_payout(
            target_address='0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437',
            steth_in_wei=1_057_755 * 1.05 / 3056.17000000 * 10**18,
            #  Price was taken from https://etherscan.io/address/0xCfE54B5cD566aB89272946F602D76Ea879CAb4a8#readContract
            #  latestTimestamp: 1650374735
            #  latestAnswer: 305617000000
            reference='Fund RCC multisig'
        ),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Send the equivalent of $1,057,755.00 (+5%) in stETH  to the RCC Multisig. '
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    tx_params = {'from': get_deployer_account()}

    if get_is_live():
        tx_params['max_fee'] = '300 gwei'
        tx_params['priority_fee'] = '2 gwei'

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5)  # hack for waiting thread #2.
