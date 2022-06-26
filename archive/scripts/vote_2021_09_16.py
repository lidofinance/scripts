"""
Voting 16/09/2021.

1. Increase Balancer reward program rate to 75000 LDO
2. Set Balancer reward program allocations to 75000 LDO
3. Raise key limit for Node Operator #7 (Everstake) to 3980
4. Raise key limit for Node Operator #9 (RockX) to 1150
5. Raise key limit for Node Operator #10 (Figment) to 1000
6. Raise key limit for Node Operator #11 (Allnodes) to 5000
7. Raise key limit for Node Operator #12 (Anyblock Analytics) to 1800
8. Transfer 200,000 LDO to 1inch reward program 0xf5436129Cf9d8fa2a1cb6e591347155276550635
9. Transfer 1,320,784 LDO for the fourth referral period rewards payout to 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

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
    lido_dao_agent_address,
    balancer_rewards_manager,
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


def encode_set_balancer_rewards_rate(rate):
    agent = interface.Agent(lido_dao_agent_address)
    balancerManager = interface.BalancerReawardsManager(balancer_rewards_manager)
    return (
      lido_dao_agent_address,
      agent.forward.encode_input(
        encode_call_script([(balancer_rewards_manager,
        balancerManager.set_rewards_limit_per_period.encode_input(
            rate
        ))])
      )
    )

def encode_set_balancer_allocations_amount(amount):
    agent = interface.Agent(lido_dao_agent_address)
    balancerManager = interface.BalancerReawardsManager(balancer_rewards_manager)
    return (
      lido_dao_agent_address,
      agent.forward.encode_input(
        encode_call_script([(balancer_rewards_manager,
        balancerManager.set_allocations_limit.encode_input(
            amount
        ))])
      )
    )

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
    # 1. Increase balancer reward program rate to 75000 LDO.
    balancer_rate = 75_000 * 10**18
    _set_allocations_rate_for_balancer_rewards_manager = encode_set_balancer_rewards_rate(
        balancer_rate,
    )
    # 2. Set balancer reward program allocations to 75000 LDO.
    balancer_allocations = 75_000 * 10**18
    _set_allocations_amount_for_balancer_rewards_manager = encode_set_balancer_allocations_amount(
        balancer_allocations,
    )

    # 3. Increase the limit for #7 Everstake to 3980.
    everstake_limit = {
        'id': 7,
        'limit': 3980
    }
    # 4. Increase the limit for #9 RockX to 1150.
    rockx_limit = {
        'id': 9,
        'limit': 1150
    }
    # 5. Increase the limit for #10 Figment to 600.
    figment_limit = {
        'id': 10,
        'limit': 1000
    }
    # 6. Increase the limit for #11 Allnodes to 5000.
    allnodes_limit = {
        'id': 11,
        'limit': 5000
    }
    # 7. Increase the limit for #12 Anyblock Analytics to 1800.
    anyblock_limit = {
        'id': 12,
        'limit': 1800
    }

    # 8. Transfer 200,000 LDO to 1inch rewards manager.
    payout_1inch_rewards = {
        'amount': 200_000 * (10 ** 18),
        'address': '0xf5436129Cf9d8fa2a1cb6e591347155276550635',
        'reference': '1inch pool LP rewards transfer',
    }
    # 9. Transfer 1,320,784 LDO to referral rewards.
    payout_referral_rewards = {
        'amount': 1_320_784 * (10 ** 18),
        'address': '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
        'reference': 'Referral program fourth period payout',
    }

    # Encoding vote scripts:
    encoded_call_script = encode_call_script([
        _set_allocations_rate_for_balancer_rewards_manager,
        _set_allocations_amount_for_balancer_rewards_manager,
        _encode_set_node_operator_staking_limit(**everstake_limit),
        _encode_set_node_operator_staking_limit(**rockx_limit),
        _encode_set_node_operator_staking_limit(**figment_limit),
        _encode_set_node_operator_staking_limit(**allnodes_limit),
        _encode_set_node_operator_staking_limit(**anyblock_limit),
        _make_ldo_payout(
            target_address=payout_1inch_rewards['address'],
            ldo_in_wei=payout_1inch_rewards['amount'],
            reference=payout_1inch_rewards['reference'],
        ),
        _make_ldo_payout(
            target_address=payout_referral_rewards['address'],
            ldo_in_wei=payout_referral_rewards['amount'],
            reference=payout_referral_rewards['reference'],
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
            '1) Increase balancer reward program rate to 75000 LDO, '
            '2) Set balancer reward program allocations to 75000 LDO, '
            '3) Increase staking limits for Node Operators, '
            '4) Allocate 200,000 LDO tokens to 1inch rewards distributor contract, '
            '5) Allocate 1,320,784 LDO tokens to 4th period referral rewards'
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
