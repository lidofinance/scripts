"""
Voting 03/05/2022.

1. Create role ISSUE_ROLE for TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249
2. Issue 3,691,500 LDO tokens in favor of TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249
3. Assign vested 3,691,500 LDO tokens to 0xe15232f912d92077bf4fad50dd7bfb0347aef821 till Sun Dec 18 2022 00:00:00 +UTC
4. Revoke ISSUE_ROLE from Voting 0x2e59A20f205bB85a89C53f1936454680651E618e

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.permissions import encode_permission_revoke, encode_permission_create
from utils.evm_script import encode_call_script
from utils.config import get_deployer_account, contracts

from utils.brownie_prelude import *

def issue_ldo(
    amount: int,
) -> Tuple[str, str]:
    token_manager: interface.TokenManager = contracts.token_manager

    return (
        token_manager.address,
        token_manager.issue.encode_input(
            amount
        )
    )

def assign_vested(
    target_address: str,
    amount: int,
    start: int,
    cliff: int,
    vesting: int
) -> Tuple[str, str]:
    token_manager: interface.TokenManager = contracts.token_manager
    revokable: bool = False

    return (
        token_manager.address,
        token_manager.assignVested.encode_input(
            target_address,
            amount,
            start,
            cliff,
            vesting,
            revokable
        )
    )

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    token_manager: interface.TokenManager = contracts.token_manager
    voting: interface.Voting = contracts.voting

    ldo_amount: int = 3_691_500 * 10 ** 18
    destination_vesting_address: str = '0xe15232f912d92077bf4fad50dd7bfb0347aef821'

    # see also https://www.unixtimestamp.com/index.php for time conversions
    start: int = 1651852800   # Fri May 06 2022 16:00:00 GMT+0000
    cliff: int = 1651852800   # Fri May 06 2022 16:00:00 GMT+0000
    vesting: int = 1671321600 # Sun Dec 18 2022 00:00:00 GMT+0000 (in 7 months)

    encoded_call_script = encode_call_script([
        # 1. Create role ISSUE_ROLE for TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249
        encode_permission_create(entity=voting, target_app=token_manager, permission_name='ISSUE_ROLE', manager=voting),
        # 2. Issue 3,691,500 LDO tokens in favor of TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249
        issue_ldo(ldo_amount),
        # 3. Assign vested 3,691,500 LDO tokens to 0xe15232f912d92077bf4fad50dd7bfb0347aef821 till Sun Dec 18 2022 00:00:00 +UTC
        assign_vested(
            destination_vesting_address,
            ldo_amount,
            start=start,
            cliff=cliff,
            vesting=vesting
        ),
        # 4. Revoke ISSUE_ROLE from Voting 0x2e59A20f205bB85a89C53f1936454680651E618e
        encode_permission_revoke(target_app=token_manager, permission_name='ISSUE_ROLE', revoke_from=voting),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Create role ISSUE_ROLE for TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249;'
            '2) Issue 3,691,500 LDO tokens in favor of TokenManager 0xf73a1260d222f447210581DDf212D915c09a3249;'
            '3) Assign vested 3,691,500 LDO tokens to 0xe15232f912d92077bf4fad50dd7bfb0347aef821 till Sun Dec 18 2022 00:00:00 +UTC;'
            '4) Revoke ISSUE_ROLE from Voting 0x2e59A20f205bB85a89C53f1936454680651E618e.'
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
