"""
Voting 28/10/2021.

1. Unpause deposits in the protocol
2. Transfer 138,162.5642 LDO to `0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb` for referral rewards seventh period

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

def unpause_deposits(deposit_security_module) -> Tuple[str, str]:
    return agent_forward([(
        deposit_security_module.address,
        deposit_security_module.unpauseDeposits.encode_input()
    )])

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

    # 2. Transfer 138,162.5642 LDO to `0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb` for referral rewards seventh period
    payout_referral = {
        'amount': 138_162_5642 * (10 ** 14),
        'address': finance_multisig_address,
        'reference': 'Seventh period referral rewards'
    }

    encoded_call_script = encode_call_script([
        unpause_deposits(deposit_security_module),
        _make_ldo_payout(
            target_address=payout_referral['address'],
            ldo_in_wei=payout_referral['amount'],
            reference=payout_referral['reference']
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
            'Omnibus vote: \n'
            '1) Unpause deposits in the protocol \n'
            '2) Allocate 138,162.5642 LDO tokens to 6th period referral rewards'
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
