"""
Voting 04/11/2021.

1. Continue Curve LP rewards with 3,550,000 LDO to 0x753D5167C31fBEB5b49624314d74A957Eb271709
2. Continue Balancer LP rewards with 300,000 LDO to 0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8
3. Transfer 400,000 LDO to `0xaE49a2C1e2CD3D8f2679a4A49db58983B8de343E` for stSOL incentives

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
    chain_network,
    prompt_bool,
    get_deployer_account,
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    finance_multisig_address,
    lido_dao_deposit_security_module_address,
)

from utils.agent import agent_forward

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
    token_manager = interface.TokenManager(lido_dao_token_manager_address)
    deposit_security_module = interface.DepositSecurityModule(lido_dao_deposit_security_module_address)

    _make_ldo_payout = partial(make_ldo_payout, finance=finance)

    # 1. Continue Curve LP rewards with 3,550,000 LDO to 0x753D5167C31fBEB5b49624314d74A957Eb271709
    payout_curve = {
        'amount': 3_550_000 * (10 ** 18),
        'address': '0x753D5167C31fBEB5b49624314d74A957Eb271709',
        'reference': 'Curve pool LP rewards transfer'
    }

    # 2. Continue Balancer LP rewards with 300,000 LDO to 0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8

    payout_balancer = {
        'amount': 300_000 * (10 ** 18),
        'address': '0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8',
        'reference': 'Balancer pool LP rewards transfer'
    }

    # 3. Transfer 400,000 LDO to `0xaE49a2C1e2CD3D8f2679a4A49db58983B8de343E` for stSOL incentives

    payout_stsol = {
        'amount': 400_000 * (10 ** 18),
        'address': '0xaE49a2C1e2CD3D8f2679a4A49db58983B8de343E',
        'reference': 'stSOL pools rewards transfer'
    }

    encoded_call_script = encode_call_script([
        _make_ldo_payout(
            target_address=payout_curve['address'],
            ldo_in_wei=payout_curve['amount'],
            reference=payout_curve['reference']
        ),
        _make_ldo_payout(
            target_address=payout_balancer['address'],
            ldo_in_wei=payout_balancer['amount'],
            reference=payout_balancer['reference']
        ),
        _make_ldo_payout(
            target_address=payout_stsol['address'],
            ldo_in_wei=payout_stsol['amount'],
            reference=payout_stsol['reference']
        )
    ])

    # Show detailed description of prepared voting.
    if not silent:
        human_readable_script = decode_evm_script(
            encoded_call_script, verbose=False, specific_net=chain_network, repeat_is_error=True
        )

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
            '3) Allocate 400,000 LDO tokens to stSOL pools incentives'
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
