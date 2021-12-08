"""
Voting 09/12/2021.

1. Top up Curve LP reward program with 3,550,000 LDO to 0x753D5167C31fBEB5b49624314d74A957Eb271709.
2. Top up Balancer LP reward program with 300,000 LDO to address 0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8 !!!! WRONG !!!!
3. Top up Sushi LP reward program with 50,000 LDO to 0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4
4. Referral program payout of 140,414 LDO to financial multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

"""

import time
from functools import partial
from typing import (
    Dict, Tuple,
    Optional
)
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
    lido_dao_token_manager_address,
    lido_dao_finance_address
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

    voting = interface.Voting(lido_dao_voting_address)
    finance = interface.Finance(lido_dao_finance_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    _make_ldo_payout = partial(make_ldo_payout, finance=finance)

    encoded_call_script = encode_call_script([
        # 1. Top up Curve LP reward program with 3,550,000 LDO to 0x753D5167C31fBEB5b49624314d74A957Eb271709

        _make_ldo_payout(
            target_address='0x753D5167C31fBEB5b49624314d74A957Eb271709',
            ldo_in_wei=3_550_000 * (10 ** 18),
            reference='Curve LP reward program'
        ),

        # 2. Top up Balancer LP reward program with 300,000 LDO to address to be announced

        _make_ldo_payout(
            target_address='0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8',
            ldo_in_wei=300_000 * (10 ** 18),
            reference="Balancer LP reward program"
        ),

        # 3. Top up Sushi LP reward program with 50,000 LDO to 0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4

        _make_ldo_payout(
            target_address='0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4',
            ldo_in_wei=50_000 * (10 ** 18),
            reference="Sushi LP reward program"
        ),

        # 4. Referral program payout of 140,414 LDO to financial multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=140_414 * (10 ** 18),
            reference="Tenth period referral rewards"
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
            '1) Top up Curve LP reward program with 3,550,000 LDO;'
            '2) Top up Balancer LP reward program with 300,000 LDO;'
            '3) Top up Sushi LP reward program with 50,000 LDO;'
            '4) Allocate 140414 LDO to the financial multisig for 10th period referral rewards.'
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
