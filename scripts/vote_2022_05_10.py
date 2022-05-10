"""
Voting 10/05/2022.

1. Send 2,000,000 LDO from Lido treasury to the Protocol Guild vesting contract
0xF29Ff96aaEa6C9A1fBa851f74737f3c069d4f1a9
CHECK THE CONTRACT IS VERIFIED BEFORE STARTING THE VOTE

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts
)
from utils.finance import make_ldo_payout
from utils.brownie_prelude import *


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    encoded_call_script = encode_call_script([
        # 1.  Send 2,000,000 LDO from Lido treasury to the Protocol Guild vesting contract
        # 0xF29Ff96aaEa6C9A1fBa851f74737f3c069d4f1a9
        make_ldo_payout(
            target_address='0xF29Ff96aaEa6C9A1fBa851f74737f3c069d4f1a9',
            ldo_in_wei=2_000_000 * (10 ** 18),
            reference="Transfer for the Protocol Guild"
        ),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Send 2,000,000 LDO to the Protocol Guild vesting contract 0xF29Ff96aaEa6C9A1fBa851f74737f3c069d4f1a9.'
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
