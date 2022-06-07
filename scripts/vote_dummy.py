"""
Just test voting
"""

import time

from typing import (Dict, Tuple, Optional, List)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script

from utils.config import (get_deployer_account, get_is_live, contracts)
from utils.permissions import encode_permission_create, encode_permission_grant_p, encode_permission_revoke
from utils.permission_parameters import Param, Op, ArgumentValue

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
    self_owned_steth_burner: interface.SelfOwnedStETHBurner = contracts.self_owned_steth_burner

    encoded_call_script = encode_call_script([
        # 4. Set Execution Layer rewards withdrawal limit to 2BP
        encode_set_elrewards_withdrawal_limit(2),

    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
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
