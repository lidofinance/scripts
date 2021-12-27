"""
Voting 27/12/2021.

1. Send 4,700 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 10,000 DAI Master of Validators Dec comp
2. Send 7,800 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 16,666 DAI BizDev Leader Dec comp
3. Referral program payout of 235,290 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb



"""

import time
from typing import (
    Dict, Tuple,
    Optional
)
from brownie.network.transaction import TransactionReceipt
from functools import partial

from utils.finance import encode_token_transfer
from utils.voting import create_vote
from utils.evm_script import (
    decode_evm_script,
    encode_call_script,
    calls_info_pretty_print
)
from utils.config import (
    prompt_bool,
    get_deployer_account,
    ldo_token_address,
    lido_dao_steth_address,
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
        # 1. Send 4,700 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 10,000 DAI Isidoros Passadis Dec comp

        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=4_700 * (10 ** 18),
            reference='Master of Validators Dec comp'
        ),

        # 2. Send 7,800 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 16,666 DAI Jacob Blish Dec comp

        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=7_800 * (10 ** 18),
            reference='BizDev Leader Dec comp'
        ),

        # 3. Referral program payout of 235,290 LDO to financial multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=235_290 * (10 ** 18),
            reference="11th period referral rewards"
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
            '1) Allocate 4,700 LDO tokens to Master of Validators Dec 2021 compensation;'
            '2) Allocate 7,800 LDO tokens to BizDev Leader Dec 2021 compensation;'
            '3) Allocate 235,290 LDO tokens for the 11th period referral rewards.'
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
