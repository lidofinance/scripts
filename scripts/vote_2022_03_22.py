"""
Voting 22/03/2022.

1. Create role BURN_ROLE for TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1
2. Create role ISSUE_ROLE for TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1
3. Burn X LDO tokens on 0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2
4. Issue X LDO tokens in favor of TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1
5. Assign vested X LDO tokens to 0x... till Sun Dec 18 2022 00:00:00 +UTC
6. Revoke BURN_ROLE from Voting 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db
7. Revoke ISSUE_ROLE from Voting 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.permissions import encode_permission_revoke, create_permission
from utils.evm_script import encode_call_script
from utils.config import get_deployer_account, contracts

from utils.brownie_prelude import *

def burn_ldo(
    target_address: str,
    amount: int,
) -> Tuple[str, str]:
    token_manager: interface.TokenManager = contracts.token_manager

    return (
        token_manager.address,
        token_manager.burn.encode_input(
            target_address, amount
        )
    )

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
    acl: interface.ACL = contracts.acl

    #FIXME!!! Update addrs and vals

    ldo_amount: int = 3_700_000 * 10 ** 18 # FIXME: Should be recalculated according to the execution time with additional margin

    source_address: str = '0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2'
    target_address: str = '0xb8FFC3Cd6e7Cf5a098A1c92F48009765B24088Dc' #FIXME: CHANGE IT

    # see also https://www.unixtimestamp.com/index.php for time conversions
    start: int = 1639785600   # Sat Dec 18 2021 00:00:00 GMT+0000 (3 months ago)
    cliff: int = 1639785600   # Sat Dec 18 2021 00:00:00 GMT+0000 (3 months ago)
    vesting: int = 1671321600 # Sun Dec 18 2022 00:00:00 GMT+0000 (in 9 months)

    encoded_call_script = encode_call_script([
        # 1. Create role BURN_ROLE for TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1
        create_permission(entity=voting, target_app=token_manager, permission_name='BURN_ROLE', manager=voting, acl=acl),
        # 2. Create role ISSUE_ROLE for TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1
        create_permission(entity=voting, target_app=token_manager, permission_name='ISSUE_ROLE', manager=voting, acl=acl),
        # 3. Burn X LDO tokens on 0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2
        burn_ldo(source_address, ldo_amount),
        # 4. Issue X LDO tokens in favor of TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1
        issue_ldo(ldo_amount),
        # 5. Assign vested X LDO tokens to 0x... till Sun Dec 18 2022 00:00:00 +UTC
        assign_vested(
            target_address,
            ldo_amount,
            start=start,
            cliff=cliff,
            vesting=vesting
        ),
        # 6. Revoke BURN_ROLE from Voting 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db
        encode_permission_revoke(target_app=token_manager, permission_name='BURN_ROLE', revoke_from=voting, acl=acl),
        # 7. Revoke ISSUE_ROLE from Voting 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db
        encode_permission_revoke(target_app=token_manager, permission_name='ISSUE_ROLE', revoke_from=voting, acl=acl)
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Create role BURN_ROLE for TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1;'
            '2) Create role ISSUE_ROLE for TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1;'
            '3) Burn X LDO tokens on 0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2;'
            '4) Issue X LDO tokens in favor of TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1;'
            '5) Assign vested X LDO tokens to 0x... till Sun Dec 18 2022 00:00:00 +UTC;'
            '6) Revoke BURN_ROLE from Voting 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db;'
            '7) Revoke ISSUE_ROLE from Voting 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db.'
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
