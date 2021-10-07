"""
Voting 07/10/2021.

1. Transfer 3,550,000 LDO to Curve reward program 0x753D5167C31fBEB5b49624314d74A957Eb271709
2. Transfer 300,000 LDO to Balancer reward program 0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8
3. Transfer 462,962.9629629634 LDO to the purchase contract 0x689E03565e36B034EcCf12d182c3DC38b2Bb7D33
    for the treasury diversification
4. Grant ASSIGN_ROLE to the purchase contract 0x689E03565e36B034EcCf12d182c3DC38b2Bb7D33
5. Transfer $100k +20% buffer (by voting creation time prices) in LDO to Finance Multisig
    0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb to pay 100k DAI bounty to a white hat
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
    lido_dao_acl_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
)

from utils.permissions import encode_permission_grant

PURCHASE_CONTRACT_PAYOUT_ADDRESS = '0x689E03565e36B034EcCf12d182c3DC38b2Bb7D33'

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
    acl = interface.ACL(lido_dao_acl_address)
    registry = interface.NodeOperatorsRegistry(
        lido_dao_node_operators_registry
    )
    finance = interface.Finance(lido_dao_finance_address)
    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )

    _make_ldo_payout = partial(make_ldo_payout, finance=finance)


    # 1. Transfer 3,550,000 LDO to Curve rewards manager
    payout_curve_rewards = {
        'amount': 3_550_000 * (10 ** 18),
        'address': '0x753D5167C31fBEB5b49624314d74A957Eb271709',
        'reference': 'Curve pool LP rewards transfer'
    }

    # 2. Transfer 300,000 LDO to Balancer rewards manager
    payout_balancer_rewards = {
        'amount': 300_000 * (10 ** 18),
        'address': '0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8',
        'reference': 'Balancer pool LP rewards transfer'
    }

    #3. Transfer 462,962.9629629634 LDO to the purchase contract for the treasury diversification
    payout_purchase_contract = {
        'amount': '462962962962963400000000', # 462,962.9629629634 * (10 ** 18)
        'address': PURCHASE_CONTRACT_PAYOUT_ADDRESS,
        'reference': 'Treasury diversification purchase contract transfer'
    }

    #4. Grant ASSIGN_ROLE to the purchase contract
    grant_role_purchase_contract = {
        'address': PURCHASE_CONTRACT_PAYOUT_ADDRESS,
        'permission_name': 'ASSIGN_ROLE'
    }

    #5. Transfer 28,500 LDO (~120k DAI) to finance multisig for $100k bounty to a white hat
    payout_finance_multisig = {
        'amount': 28_500 * (10 ** 18), # TODO: Check current rate on 1inch before run
        'address': '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
        'reference': 'Finance multisig transfer to pay a bug bounty'
    }

    encoded_call_script = encode_call_script([
        _make_ldo_payout(
            target_address=payout_curve_rewards['address'],
            ldo_in_wei=payout_curve_rewards['amount'],
            reference=payout_curve_rewards['reference']
        ),
        _make_ldo_payout(
            target_address=payout_balancer_rewards['address'],
            ldo_in_wei=payout_balancer_rewards['amount'],
            reference=payout_balancer_rewards['reference']
        ),
        _make_ldo_payout(
            target_address=payout_purchase_contract['address'],
            ldo_in_wei=payout_purchase_contract['amount'],
            reference=payout_purchase_contract['reference']
        ),
        encode_permission_grant(
            acl=acl,
            target_app=token_manager,
            grant_to=grant_role_purchase_contract['address'],
            permission_name=grant_role_purchase_contract['permission_name'],
        ),
        _make_ldo_payout(
            target_address=payout_finance_multisig['address'],
            ldo_in_wei=payout_finance_multisig['amount'],
            reference=payout_finance_multisig['reference']
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
