"""
Vote script for the coverage setup
"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.config import get_deployer_account, contracts

from utils.permissions import (
    encode_permission_revoke,
    encode_permission_grant_granular,
    require_first_param_is_addr
)

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    lido = contracts.lido
    oracle = contracts.oracle
    voting = contracts.voting
    anchor_vault = contracts.anchor_vault
    anchor_insurance_connector = contracts.anchor_insurance_connector
    composite_receiver = contracts.composite_post_rebase_beacon_receiver
    steth_burner = contracts.self_owned_steth_burner

    encoded_call_script = encode_call_script([
        (
            composite_receiver.address,
            composite_receiver.addCallback.encode_input(
                steth_burner.address
            )
        ),
        (
            oracle.address,
            oracle.setBeaconReportReceiver.encode_input(
                composite_receiver.address
            )
        ),
        encode_permission_revoke(
            target_app=lido,
            permission_name="BURN_ROLE",
            revoke_from=voting
        ),
        encode_permission_grant_granular(
            target_app=lido,
            permission_name="BURN_ROLE",
            grant_to=steth_burner,
            acl_param=require_first_param_is_addr(steth_burner.address)
        ),
        (
            anchor_vault.address,
            anchor_vault.set_insurance_connector.encode_input(
                anchor_insurance_connector.address
            )
        )
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Wrap stETH burner into a composite receiver;'
            '2) Attach the composite receiver to the Lido oracle as a beacon report callback;'
            '3) Revoke `BURN_ROLE` permissions from Voting;'
            '4) Grant `BURN_ROLE` constrained permissions to the stETH burner;'
            '5) Set new InsuranceConnector to AnchorVault.'
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
