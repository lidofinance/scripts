"""
Creates voting with CALLDATA from DEPLOYER
"""

import time
import os
from typing import (
    Dict, Tuple,
    Optional
)
from brownie.utils import color
from brownie.network.transaction import TransactionReceipt

from utils.voting import create_vote
from utils.evm_script import (
    decode_evm_script,
    calls_info_pretty_print
)
from utils.config import (
    prompt_bool,
    get_deployer_account,
    lido_dao_voting_address,
    lido_dao_token_manager_address,
)

try:
    from brownie import interface
except ImportError:
    print(
        'You\'re probably running inside Brownie console. '
        'Please call:\n'
        'set_console_globals(interface=interface)'
    )


def start_vote(
        tx_params: Dict[str, str],
        silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    encoded_call_script = os.environ['CALLDATA']

    human_readable_script = decode_evm_script(
        encoded_call_script, verbose=False, specific_net='mainnet', repeat_is_error=True
    )

    # Show detailed description of prepared voting.
    if not silent:
        print('\nPoints of voting:')
        total = len(human_readable_script)
        print(human_readable_script)
        for ind, call in enumerate(human_readable_script):
            print(f'Point #{ind + 1}/{total}.')
            print(calls_info_pretty_print(call))
            print('---------------------------')

        print('Does it look good?')
        resume = prompt_bool()
        while resume is None:
            resume = prompt_bool()

        if not resume:
            print('Exit without running.')
            return -1, None

    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=(
            'Omnibus vote: '
            '1) Allocate 3,550,000 LDO tokens to Curve rewards distributor contract, '
            '2) Allocate 300,000 LDO tokens to Balancer rewards distributor contract, '
            '3) Allocate 462,962.9629629634 LDO tokens to the treasury diversification contract, '
            '4) Grant ASSIGN_ROLE to the treasury diversification contract, '
            '5) Transfer 28,500 LDO to Finance Multisig for bounty payout'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )

def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'gas_price': '100 gwei',
    })
    print(f'Vote created: {vote_id}.')
    time.sleep(5)  # hack for waiting thread #2.
