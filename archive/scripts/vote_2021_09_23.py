"""
Voting 23/09/2021.

1. Transfer 400,000 LDO to `0xaE49a2C1e2CD3D8f2679a4A49db58983B8de343E` for stSOL incentives
2. Transfer 3,500 LDO to `0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb` for Jacob Blish Sept compenstaion
3. Raise key limit for Node Operator #7 (Everstake) to 5000
4. Raise key limit for Node Operator #13 (Blockdaemon) to 200

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
from utils.node_operators import (
    encode_set_node_operator_staking_limit
)
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
    lido_dao_node_operators_registry,
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
    registry = interface.NodeOperatorsRegistry(
        lido_dao_node_operators_registry
    )
    finance = interface.Finance(lido_dao_finance_address)
    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    # Set Lido contracts as parameters:
    _encode_set_node_operator_staking_limit = partial(
        encode_set_node_operator_staking_limit, registry=registry
    )
    _make_ldo_payout = partial(make_ldo_payout, finance=finance)

    # Vote-specific addresses and constants:
    # 1. Increase the limit for #7 Everstake to 5000.
    everstake_limit = {
        'id': 7,
        'limit': 5000
    }
    # 2. Increase the limit for #13 Blockdaemon to 200.
    blockdaemon_limit = {
        'id': 13,
        'limit': 200
    }

    # 3. Transfer 400,000 LDO to stSOL incentives
    payout_stsol_incentives = {
        'amount': 400_000 * (10 ** 18),
        'address': '0xaE49a2C1e2CD3D8f2679a4A49db58983B8de343E',
        'reference': 'stSOL pools rewards transfer',
    }
    # 4. Transfer 3,500 LDO to Jacob Blish comp.
    payout_jacob_comp = {
        'amount': 3_500 * (10 ** 18),
        'address': '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
        'reference': 'Jacob Blish Sept 2021 comp',
    }

    # Encoding vote scripts:
    encoded_call_script = encode_call_script([
        _encode_set_node_operator_staking_limit(**everstake_limit),
        _encode_set_node_operator_staking_limit(**blockdaemon_limit),
        _make_ldo_payout(
            target_address=payout_stsol_incentives['address'],
            ldo_in_wei=payout_stsol_incentives['amount'],
            reference=payout_stsol_incentives['reference'],
        ),
        _make_ldo_payout(
            target_address=payout_jacob_comp['address'],
            ldo_in_wei=payout_jacob_comp['amount'],
            reference=payout_jacob_comp['reference'],
        ),
    ])
    human_readable_script = decode_evm_script(
        encoded_call_script, verbose=False,
        specific_net='mainnet', repeat_is_error=True
    )

    # Show detailed description of prepared voting.
    if not silent:
        print(f'\n{__doc__}\n')

        pp('Lido finance contract at:', finance.address)
        pp('Lido node operator registry at:', registry.address)
        pp('Lido voting contract at:', voting.address)
        pp('Lido token manager at:', token_manager.address)
        pp('LDO token at:', ldo_token_address)

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
        vote_desc=(
            'Omnibus vote: '
            '1) Increase staking limits for Node Operators, '
            '2) Allocate 400,000 LDO tokens to stSOL pools incentives, '
            '3) Allocate 3,500 LDO tokens to Jacob Blish Sept 2021 compensation'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'gas_price': '60 gwei'
    })
    print(f'Vote created: {vote_id}.')
    time.sleep(5)  # hack for waiting thread #2.
