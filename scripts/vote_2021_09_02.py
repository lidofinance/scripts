"""
Voting 02/09/2021.

1. Node Operators Registry:
   Add node operator named Blockdaemon with reward address
   `0x4f42A816dC2DBa82fF927b6996c14a741DCbD902`
2. Raise key limit for Node Operator #2 (p2p) to 4800
3. Raise key limit for Node Operator #4 (stakefish) to 6000
4. Raise key limit for Node Operator #5 (Blockscape) to 7000
5. Raise key limit for Node Operator #6 (DSRV) to 3700
6. Raise key limit for Node Operator #8 (SkillZ) to 7000
7. Raise key limit for Node Operator #9 (RockX) to 100
8. Raise key limit for Node Operator #10 (Figment) to 100
9. Raise key limit for Node Operator #11 (Allnodes) to 100
10. Raise key limit for Node Operator #12 (Anyblock) to 100
11. Allocate LDO tokens (3 523 767.186 LDO) for the third referral period
    rewards to finance
    address `0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb`
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
    encode_add_operator,
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


def make_ldo_referral_payout(
        *not_specified,
        target_address: str, ldo_in_wei: int,
        finance: interface.Finance
) -> Tuple[str, str]:
    """Encode referral payout."""
    if not_specified:
        raise ValueError(
            'Please, specify all arguments with keywords.'
        )

    return encode_token_transfer(
        token_address=ldo_token_address,
        recipient=target_address,
        amount=ldo_in_wei,
        reference='Referral program third period payout',
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
    # 1. Add Blockdaemon as a node operator.
    blockdaemon_node_operator = {
        'name': 'Blockdaemon',
        'address': '0x4f42A816dC2DBa82fF927b6996c14a741DCbD902'
    }
    # 2. Increase the limit for #2 P2P to 4800.
    p2p_limit = {
        'id': 2,
        'limit': 4800
    }
    # 3. Increase the limit for #4 Stakefish to 6000.
    stakefish_limit = {
        'id': 4,
        'limit': 6000,
    }
    # 4. Increase the limit for #5 Blockscape to 7000.
    blockscape_limit = {
        'id': 5,
        'limit': 7000,
    }
    # 5. Increase the limit for #6 DSRV to 3700.
    dsrv_limit = {
        'id': 6,
        'limit': 3700
    }
    # 6. Increase the limit for #8 SkillZ to 7000.
    skillz_limit = {
        'id': 8,
        'limit': 7000
    }
    # 7. Increase the limit for #9 RockX to 100.
    rockx_limit = {
        'id': 9,
        'limit': 100
    }
    # 8. Increase the limit for #10 Figment to 100.
    figment_limit = {
        'id': 10,
        'limit': 100
    }
    # 9. Increase the limit for #11 Allnodes to 100.
    allnodes_limit = {
        'id': 11,
        'limit': 100
    }
    # 10. Increase the limit for #12 Anyblock to 100.
    anyblock_limit = {
        'id': 12,
        'limit': 100
    }
    # 11. Allocate 3 523 767.186 LDO
    #     to 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
    payout_referral_rewards = {
        'amount': 3_523_767_186 * (10 ** 15),
        'address': '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    }

    # Set Lido contracts as parameters:
    _encode_add_operator = partial(encode_add_operator, registry=registry)
    _encode_set_node_operator_staking_limit = partial(
        encode_set_node_operator_staking_limit, registry=registry
    )
    _make_ldo_referral_payout = partial(
        make_ldo_referral_payout, finance=finance
    )

    # Encoding vote scripts:
    encoded_call_script = encode_call_script([
        _encode_add_operator(**blockdaemon_node_operator),
        _encode_set_node_operator_staking_limit(**p2p_limit),
        _encode_set_node_operator_staking_limit(**stakefish_limit),
        _encode_set_node_operator_staking_limit(**blockscape_limit),
        _encode_set_node_operator_staking_limit(**dsrv_limit),
        _encode_set_node_operator_staking_limit(**skillz_limit),
        _encode_set_node_operator_staking_limit(**rockx_limit),
        _encode_set_node_operator_staking_limit(**figment_limit),
        _encode_set_node_operator_staking_limit(**allnodes_limit),
        _encode_set_node_operator_staking_limit(**anyblock_limit),
        _make_ldo_referral_payout(
            target_address=payout_referral_rewards['address'],
            ldo_in_wei=payout_referral_rewards['amount'],
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
            '1) Add Blockdaemon node operator, '
            '2) Increase staking limits for Node Operators, '
            '3) Allocate LDO tokens (3 523 767.186 LDO) '
            'for the third referral '
            'period rewards to finance ops multisig.'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'gas_price': '50 gwei'
    })
    print(f'Vote created: {vote_id}.')
    time.sleep(5)  # hack for waiting thread #2.
