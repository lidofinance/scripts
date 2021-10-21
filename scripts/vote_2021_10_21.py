"""
Voting 21/10/2021.

1. Transfer 200,000 LDO to 1inch reward program 0xf5436129cf9d8fa2a1cb6e591347155276550635
2. Transfer 5,500 LDO +20%  to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 16,666 DAI Jacob Blish monthly compensation

"""

import time
from functools import partial
from typing import (
    Dict, Tuple,
    Optional
)
from brownie.utils import color
from brownie.network.transaction import TransactionReceipt

from utils.voting import create_vote
from utils.finance import encode_token_transfer
from utils.evm_script import (
    decode_evm_script,
    encode_call_script,
    calls_info_pretty_print
)
from utils.config import (
    prompt_bool,
    get_deployer_account,
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
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


def pp(text, value):
    """Pretty print with colorized."""
    print(text, color.highlight(str(value)), end='')

def make_ldo_payout(
        *not_specified,
        target_address: str,
        ldo_in_wei: int,
        reference: str,
        finance: interface.Finance
) -> Tuple[str, str]:
    """Encode LDO payout."""
    if not_specified:
        raise ValueError(
            'Please, specify all arguments with keywords.'
        )

    return encode_token_transfer(
        token_address=ldo_token_address,
        recipient=target_address,
        amount=ldo_in_wei,
        reference=reference,
        finance=finance
    )

def start_vote(
        tx_params: Dict[str, str],
        silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    # Lido contracts and constants:
    finance = interface.Finance(lido_dao_finance_address)
    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    _make_ldo_payout = partial(make_ldo_payout, finance=finance)

    # 1. Transfer 200,000 LDO to 1Inch rewards manager
    payout_one_inch_rewards = {
        'amount': 200_000 * (10 ** 18),
        'address': '0xf5436129Cf9d8fa2a1cb6e591347155276550635',
        'reference': '1inch pool LP rewards transfer'
    }

    # 2. Transfer 5,500 LDO to finance multisig for 16,666 DAI Jacob Blish monthly compensation
    payout_referral = {
        'amount': 5_500 * (10 ** 18),
        'address': '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
        'reference': 'Jacob Blish Nov 2021 comp'
    }

    encoded_call_script = encode_call_script([
        _make_ldo_payout(
            target_address=payout_one_inch_rewards['address'],
            ldo_in_wei=payout_one_inch_rewards['amount'],
            reference=payout_one_inch_rewards['reference']
        ),
        _make_ldo_payout(
            target_address=payout_referral['address'],
            ldo_in_wei=payout_referral['amount'],
            reference=payout_referral['reference']
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
            '1) Allocate 200,000 LDO to 1inch reward program'
            '2) Allocate 5,500 LDO tokens to Jacob Blish Nov 2021 compensation'
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
