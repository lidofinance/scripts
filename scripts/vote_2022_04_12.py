"""
Voting 12/04/2022.

1. Refund previous depositor' spending to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
   with 254.684812629886507249 ETH.
2. Fund depositor bot with 130 ETH.

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.finance import make_eth_payout
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
        # 1. Refund previous depositor' spending to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
        # with 254.684812629886507249 ETH.
        make_eth_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            eth_in_wei=254_684_812_629_886_507_249,
            reference='Refund depositor\'s spending'
        ),
        # 2. Fund dedicated depositor multisig 0x5181d5D56Af4f823b96FE05f062D7a09761a5a53 with 130 ETH.
        make_eth_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            eth_in_wei=130 * (10 ** 18),
            reference='Fund depositor bot'
        ),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Refund previous depositor\' spending to finance multisig with 254.684812629886507249 ETH; '
            '2) Fund depositor bot with 130 ETH.'
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
