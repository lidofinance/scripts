"""
Voting 09/09/2021.

1. Raise key limit for Node Operator #2 (P2P) to 7800
2. Raise key limit for Node Operator #6 (DSRV) to 4000
3. Raise key limit for Node Operator #13 (Blockdaemon) to 100
4. Continue curve rewards 3,550,000 LDO to `0x753D5167C31fBEB5b49624314d74A957Eb271709`
5. Top up Balancer reward program - 300,000 LDO to `0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8`
6. Top up Sushi reward program - 200,000 LDO to `0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4`
7. Send $250k +10% buffer (by voting creation time prices) in LDO to Finance Multisig `0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb` to pay to ETH1 Execution Client Teams
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

    # Vote specific addresses and constants:
    # 1. Increase the limit for #2 P2P to 4800.
    p2p_limit = {
        'id': 2,
        'limit': 7800
    }
    # 2. Increase the limit for #6 DSRV to 4000.
    dsrv_limit = {
        'id': 6,
        'limit': 4000
    }
    # 3. Increase the limit for #14 Blockdaemon to 100.
    blockdaemon_limit = {
        'id': 13,
        'limit': 100
    }
    # 4. Allocate 3 550 000 LDO
    #     to Curve reward manager 0x753D5167C31fBEB5b49624314d74A957Eb271709
    payout_curve_rewards = {
        'amount': 3_550_000 * (10 ** 18),
        'address': '0x753D5167C31fBEB5b49624314d74A957Eb271709',
        'reference': 'Curve pool LP rewards transfer',
    }
    # 5. Allocate 300 000 LDO
    #     to Balancer reward manager 0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8
    payout_balancer_rewards = {
        'amount': 300_000 * (10 ** 18),
        'address': '0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8',
        'reference': 'Balancer pool LP rewards transfer',
    }
    # 6. Allocate 200 000 LDO
    #     to Sushi reward manager 0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4
    payout_sushi_rewards = {
        'amount': 200_000 * (10 ** 18),
        'address': '0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4',
        'reference': 'Sushi pool LP rewards transfer',
    }
    # 7. Allocate 54_000 LDO
    #     to finance ops multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
    payout_grant = {
        'amount': 54_000 * (10 ** 18),
        'address': '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
        'reference': 'ETH1 Execution Client Teams LEGO Grant',
    }

    # Set Lido contracts as parameters:
    _encode_set_node_operator_staking_limit = partial(
        encode_set_node_operator_staking_limit, registry=registry
    )
    _make_ldo_payout = partial(
        make_ldo_payout, finance=finance
    )

    # Encoding vote scripts:
    encoded_call_script = encode_call_script([
        _encode_set_node_operator_staking_limit(**p2p_limit),
        _encode_set_node_operator_staking_limit(**dsrv_limit),
        _encode_set_node_operator_staking_limit(**blockdaemon_limit),
        _make_ldo_payout(
            target_address=payout_curve_rewards['address'],
            ldo_in_wei=payout_curve_rewards['amount'],
            reference=payout_curve_rewards['reference'],
        ),
        _make_ldo_payout(
            target_address=payout_balancer_rewards['address'],
            ldo_in_wei=payout_balancer_rewards['amount'],
            reference=payout_balancer_rewards['reference'],
        ),
        _make_ldo_payout(
            target_address=payout_sushi_rewards['address'],
            ldo_in_wei=payout_sushi_rewards['amount'],
            reference=payout_sushi_rewards['reference'],
        ),
        _make_ldo_payout(
            target_address=payout_grant['address'],
            ldo_in_wei=payout_grant['amount'],
            reference=payout_grant['reference'],
        )
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
            '1) Increase staking limits for Node Operators, '
            '2) Allocate 3,550,000 LDO tokens to Curve rewards distributor contract, '
            '3) Allocate 300,000 LDO tokens to Balancer rewards distributor contract, '
            '4) Allocate 200,000 LDO tokens to Sushi rewards distributor contract, '
            '5) Allocate 54,000 LDO tokens to fund ETH1 Execution Client Teams'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'gas_price': '100 gwei'
    })
    print(f'Vote created: {vote_id}.')
    time.sleep(5)  # hack for waiting thread #2.
