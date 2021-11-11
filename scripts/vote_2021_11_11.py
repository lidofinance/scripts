"""
Voting 11/11/2021.

1. Revoke ASSIGN_ROLE from the 0x689E03565e36B034EcCf12d182c3DC38b2Bb7D33 token purchase contract
2. Unpause deposits in the protocol calling unpauseDeposits on 0xdb149235b6f40dc08810aa69869783be101790e7
   from Agent 0x3e40d73eb977dc6a537af587d48316fee66e9c8c
3. Continue Sushi LP rewards with 200,000 LDO to 0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4
4. Allocate 161984.4659 LDO tokens for the 8th (25.10.2021 - 08.11.2021) rewards referral period to finance multisig
   0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
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
    lido_dao_acl_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    finance_multisig_address,
    lido_dao_deposit_security_module_address,
)
from utils.permissions import encode_permission_revoke
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
    acl = interface.ACL(lido_dao_acl_address)
    finance = interface.Finance(lido_dao_finance_address)
    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )
    deposit_security_module = interface.DepositSecurityModule(lido_dao_deposit_security_module_address)

    _make_ldo_payout = partial(make_ldo_payout, finance=finance)

    encoded_call_script = encode_call_script([
        # 1. Revoke ASSIGN_ROLE from the 0x689E03565e36B034EcCf12d182c3DC38b2Bb7D33 token purchase contract
        encode_permission_revoke(
            acl=acl,
            target_app=token_manager,
            revoke_from='0x689E03565e36B034EcCf12d182c3DC38b2Bb7D33',
            permission_name='ASSIGN_ROLE'
        ),

        # 2. Unpause deposits in the protocol calling unpauseDeposits on 0xdb149235b6f40dc08810aa69869783be101790e7
        # from Agent 0x3e40d73eb977dc6a537af587d48316fee66e9c8c
        unpause_deposits(deposit_security_module),

        # 3. Continue Sushi LP rewards with 200,000 LDO to 0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4
        _make_ldo_payout(
            target_address='0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4',
            ldo_in_wei=200_000 * (10 ** 18),
            reference='Sushi pool LP rewards transfer'
        ),

        # 4. Allocate 161984.4659 LDO tokens for the 8th (25.10.2021 - 08.11.2021) referral period rewards
        # to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
        _make_ldo_payout(
            target_address=finance_multisig_address,
            ldo_in_wei=161_984_4659 * (10 ** 14),
            reference='Eighth period referral rewards'
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
            '4) Allocate 161,984.4659 LDO tokens for the 8th period referral rewards.'
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
