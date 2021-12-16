"""
Voting 16/12/2021.

1. Burn 33.827287 stETH shares on treasury address 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to compensate for Chorus validation penalties


"""

import time
from typing import (
    Dict, Tuple,
    Optional
)
from brownie.network.transaction import TransactionReceipt

from utils.voting import create_vote
from utils.evm_script import (
    decode_evm_script,
    encode_call_script,
    calls_info_pretty_print
)
from utils.config import (
    prompt_bool,
    get_deployer_account,
    lido_dao_steth_address,
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

def set_console_globals(**kwargs):
    """Extract interface from brownie environment."""
    global interface
    interface = kwargs['interface']


def burn_shares(lido, burn_address):
    # Chorus sent 33.827287 stETH by two transactions:
    # 1. https://etherscan.io/tx/0xfb8da61b72ee87d862ffb12c6d453887120084749fcee1a718de42c2bc555ba3
    # 2. https://etherscan.io/tx/0xd715e946f51bd82d5a84d87bbc8469413b751fbeaa1eafb73e28be7ff1a86638
    #
    # we calculated shares on the latest block 13804410: 
    # stethAmount = 33.827287 * 10^18
    # lido.getSharesByPooledEth(stethAmount) = 32145684728326685744

    sharesToBurn = 32145684728326685744

    return (
        lido.address,
        lido.burnShares.encode_input(
            burn_address,
            sharesToBurn
        )
    )

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting = interface.Voting(lido_dao_voting_address)
    lido = interface.Lido(lido_dao_steth_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    encoded_call_script = encode_call_script([
        # 1. Burn 33.827287 stETH shares on treasury address 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c 
        #    to compensate for Chorus validation penalties
        burn_shares(
            lido,
            '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c',
        )
        

    ])
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
            '1) Burn 33.827287 stETH shares on treasury address 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c.'
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
    print(f'Vote created: {vote_id}.')
    time.sleep(5) # hack for waiting thread #2.
