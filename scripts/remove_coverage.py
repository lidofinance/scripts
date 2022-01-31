"""
Emergency vote script to remove coverage support from the protocol
"""

import time

from typing import (Dict, Tuple, Optional)
from brownie import ZERO_ADDRESS

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.config import get_deployer_account, contracts

from utils.permissions import encode_permission_revoke

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    lido = contracts.lido
    oracle = contracts.oracle
    steth_burner = contracts.self_owned_steth_burner

    encoded_call_script = encode_call_script([
        (
            oracle.address,
            oracle.setBeaconReportReceiver.encode_input(
                ZERO_ADDRESS
            )
        ),
        encode_permission_revoke(
            target_app=lido,
            permission_name="BURN_ROLE",
            revoke_from=steth_burner
        )
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Revoke `BURN_ROLE` from `SelfOwnedStETHBurner`;'
            '2) Reset LidoOracle`s beacon report callback to `ZERO_ADDRESS`.'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )

def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'max_fee': '100 gwei',
        'priority_fee': '2 gwei'
    })

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5) # hack for waiting thread #2.
