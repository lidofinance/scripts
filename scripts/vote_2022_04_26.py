"""
Voting 26/04/2022.

1. Send 650,000 LDO to TokenManager contract 0xf73a1260d222f447210581DDf212D915c09a3249
   for Chorus One vesting
2. Assign 650,000 LDO from TokenManager contract with 2-year vesting for Chorus One to
   0x3983083d7fa05f66b175f282ffd83e0d861c777a

Vote passed & executed on Apr-29-2022 02:19:26 PM +UTC, block 14679687
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


def make_ldo_with_vesting_payment(
    target_address: str,
    amount: int,
    start: int,
    cliff: int,
    vested: int
) -> Tuple[str, str]:
    token_manager: interface.TokenManager = contracts.token_manager

    revokable = False

    return (
        token_manager.address,
        token_manager.assignVested.encode_input(
            target_address,
            amount,
            start,
            cliff,
            vested,
            revokable
        )
    )


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    encoded_call_script = encode_call_script([
        # 1. Send 650,000 LDO to TokenManager contract 0xf73a1260d222f447210581DDf212D915c09a3249
        #    for Chorus One vesting
        make_ldo_payout(
            target_address='0xf73a1260d222f447210581DDf212D915c09a3249',
            ldo_in_wei=650_000 * (10 ** 18),
            reference="TokenManager transfer for Chorus One vesting"
        ),
        # 2. Assign 650,000 LDO with 2-year vesting for Chorus One to 0x3983083d7fa05f66b175f282ffd83e0d861c777a.
        make_ldo_with_vesting_payment(
            target_address='0x3983083d7fa05f66b175f282ffd83e0d861c777a',
            amount=650_000 * 10**18,
             #start (Apr 10, 2022, 11:00 PM UTC)
            start=1649631600,
            cliff=1649631600,
            #end (Apr 10, 2024, 11:00 PM UTC)
            vested=1712790000,
        ),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Send 650,000 LDO to TokenManager contract 0xf73a1260d222f447210581DDf212D915c09a3249 for Chorus One vesting;'
            '2) Assign 650,000 LDO with 2-year vesting for Chorus One to 0x3983083d7fa05f66b175f282ffd83e0d861c777a.'
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
