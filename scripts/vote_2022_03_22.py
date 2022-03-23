"""
Voting 22/03/2022.

1. Create role BURN_ROLE for TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1
2. Burn 3,691,500 LDO tokens on 0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2
3. Revoke BURN_ROLE from Voting 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db

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

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    token_manager: interface.TokenManager = contracts.token_manager
    voting: interface.Voting = contracts.voting
    acl: interface.ACL = contracts.acl

    ldo_amount: int = 3_691_500 * 10 ** 18

    source_address: str = '0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2'

    encoded_call_script = encode_call_script([
        # 1. Create role BURN_ROLE for TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1
        create_permission(entity=voting, target_app=token_manager, permission_name='BURN_ROLE', manager=voting, acl=acl),
        # 2. Burn 3,691,500 LDO tokens on 0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2
        burn_ldo(source_address, ldo_amount),
        # 3. Revoke BURN_ROLE from Voting 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db
        encode_permission_revoke(target_app=token_manager, permission_name='BURN_ROLE', revoke_from=voting, acl=acl),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Create role BURN_ROLE for TokenManager 0xDfe76d11b365f5e0023343A367f0b311701B3bc1;'
            '2) Burn 3,691,500 LDO tokens on 0x48Acf41D10a063f9A6B718B9AAd2e2fF5B319Ca2;'
            '3) Revoke BURN_ROLE from Voting 0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db.'
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
