"""
Voting 18/11/2021.

0. Use 7day lido-dao TWAP $4.033818

1. Burn X stETH shares on treasury address 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
   to compensate for Chorus validation penalties
2. Set lido.eth to resolve to Lido smart contract 0xae7ab96520de3a18e5e111b5eaab095312d7fe84
3. Allocate 4960 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 16,666 DAI
   Jacob Blish monthly comp (+20%)
4. Allocate 2980 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 10,000 DAI
   sign-in payment for Isidoros Passadis as Master of Validotors role (+20%)
5. Increase key limits for operators which submitted new ones
6. Increase NO limits to the max available keys
7. Top up 1inch LP reward program with 50,000 LDO to 0xf5436129Cf9d8fa2a1cb6e591347155276550635
"""

import time
from functools import partial
from typing import (
    Dict, Tuple,
    Optional
)
from brownie.network.transaction import TransactionReceipt
from ens.utils import (
    raw_name_to_hash,
)

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
    lido_dao_steth_address,
    lido_dao_node_operators_registry,
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

def burn_steth_treasury(
    amount_in_wei: 
    int,target_address: str, 
    lido=interface.Lido):
    return (
        lido.address,
        lido.burnShares.encode_input(target_address, amount_in_wei)
    )

def new_lido_eth_address(ens: interface.ENS, target_address: str, lido_domain: str, controller_address: str):
    return agent_forward([(
        controller_address,
        ens.setAddr.encode_input(raw_name_to_hash(lido_domain), target_address)
    )])

def start_vote(
        tx_params: Dict[str, str],
        silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    # Lido contracts and constants:
    lido = interface.Lido(lido_dao_steth_address)
    finance = interface.Finance(lido_dao_finance_address)
    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )
    registry = interface.NodeOperatorsRegistry(
        lido_dao_node_operators_registry
    )
    ens = interface.ENS('0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e')
    
    # 5. Increase the limit for #9 RockX to 2100
    rockx_limit = {
        'id': 9,
        'limit': 2100
    }

    _make_ldo_payout = partial(make_ldo_payout, finance=finance)

    _encode_set_node_operator_staking_limit = partial(
        encode_set_node_operator_staking_limit, registry=registry
    )

    encoded_call_script = encode_call_script([
        # 1. Burn X stETH shares on treasury address 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
        #    to compensate for Chorus validation penalties
        burn_steth_treasury(
            lido=lido, 
            target_address='0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c',
            amount_in_wei=500 * 10 ** 18),


        # 2. Set lido.eth to resolve to Lido smart contract 0xae7ab96520de3a18e5e111b5eaab095312d7fe84
        new_lido_eth_address(
            ens=ens,
            lido_domain='lido.eth',
            controller_address='0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41',
            target_address='0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
        ),

        # 3. Allocate 4219.7469 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 16,666 DAI
        #    Jacob Blish monthly comp
        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=4_219_7469 * (10 ** 14),
            reference='Jacob Blish monthly comp'
        ),

        # 4. Allocate 2531.9495 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 10,000 DAI
        #    sign-in payment for Isidoros Passadis as Master of Validotors role
        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=2_531_9495 * (10 ** 14),
            reference='Eighth period referral rewards'
        ),

        # 5. Increase key limits for operators which submitted new ones
        _encode_set_node_operator_staking_limit(**rockx_limit),

        # 6. Increase NO limits to the max available keys

        # 7. Top up 1inch LP reward program with 50,000 LDO to 0xf5436129Cf9d8fa2a1cb6e591347155276550635
        _make_ldo_payout(
            target_address='0xf5436129Cf9d8fa2a1cb6e591347155276550635',
            ldo_in_wei=50_000 * (10 ** 18),
            reference='1inch LP reward program'
        ),
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
            '1) Revoke ASSIGN_ROLE from the treasury diversification contract; '
            '2) Call unpauseDeposits() on the DepositSecurityModule; '
            '3) Allocate 200,000 LDO tokens to Sushi rewards distributor contract; '
            '4) Allocate 2531.9495 LDO to finance multisig for sign-in payment for Isidoros'
            '5) Increase the limit for #9 RockX to 2100'
            '6) Increase NO limits to the max available keys'
            '6) Top up 1inch LP reward program with 50,000 LDO'
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
