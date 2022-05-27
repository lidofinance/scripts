"""
Voting 31/05/2022.


1. Grant role RESUME_ROLE to Voting
2. Grant role STAKING_PAUSE_ROLE to Voting
3. Grant role SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE to Voting
4. Set Execution Layer rewards withdrawal limit to 2BP

Revoke DEPOSIT_ROLE from old DepositSecurityModule 0xDb149235B6F40dC08810AA69869783Be101790e7
Grant DEPOSIT_ROLE to new DepositSecurityModule 0x710B3303fB508a84F10793c1106e32bE873C24cd
Set lastDepositBlock of DepositSecurityModule to ???

Wrap stETH burner into the composite receiver
Attach composite receiver to lido oracle as beacon report callback
Revoke 'BURN_ROLE' permissions from Voting
Grant 'BURN_ROLE' constrained permissions to stETH burner

Grant role MANAGE_PROTOCOL_CONTRACTS_ROLE to voting
Revoke SET_TREASURY from Voting
Revoke SET_INSURANCE_FUND from Voting
Revoke SET_ORACLE from Voting


"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script

from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts, network_name
)
from utils.permissions import encode_permission_create, encode_permission_revoke
# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *



def encode_set_elrewards_withdrawal_limit(limit_bp: int) -> Tuple[str, str]:
    lido: interface.Lido = contracts.lido
    return lido.address, lido.setELRewardsWithdrawalLimit.encode_input(limit_bp)


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    voting: interface.Voting = contracts.voting
    lido: interface.Lido = contracts.lido

    encoded_call_script = encode_call_script([
        # 1. Grant role RESUME_ROLE to Voting 
        encode_permission_create(entity=voting, target_app=lido, permission_name='RESUME_ROLE',
                                 manager=voting),

        # 2. Grant role STAKING_PAUSE_ROLE to Voting
        encode_permission_create(entity=voting, target_app=lido, permission_name='STAKING_PAUSE_ROLE',
                                 manager=voting),

        # 3. Grant role SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE to Voting
        encode_permission_create(entity=voting, target_app=lido, permission_name='SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE',
                                 manager=voting),

        # # 4. Set Execution Layer rewards withdrawal limit to 2BP
        encode_set_elrewards_withdrawal_limit(2),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Grant role RESUME_ROLE to Voting; ',
            '2) Grant role STAKING_PAUSE_ROLE to Voting; ',
            '3) Grant role SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE to Voting; ',
            '4) Set Execution Layer rewards withdrawal limit to 2BP; ',
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
