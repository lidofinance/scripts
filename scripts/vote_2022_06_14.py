"""
Voting 14/06/2022.

1. Revoke DEPOSIT_ROLE from old DepositSecurityModule 0xDb149235B6F40dC08810AA69869783Be101790e7
2. Grant DEPOSIT_ROLE to new DepositSecurityModule 0x710B3303fB508a84F10793c1106e32bE873C24cd
3. Set lastDepositBlock of DepositSecurityModule to {{??? block number TBD}}

"""

import time

from typing import (Dict, Tuple, Optional, List)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.agent import agent_forward

from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts, network_name,
    lido_dao_deposit_security_module_address
)
from utils.permissions import encode_permission_grant, encode_permission_revoke
# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


def get_proposed_deposit_security_module_address():
    if network_name() in ('goerli', 'goerli-fork'):
        return '0x7DC1C1ff64078f73C98338e2f17D1996ffBb2eDe'
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return '0x710B3303fB508a84F10793c1106e32bE873C24cd'
    else:
        assert False, f'Unsupported network "{network_name()}"'


def get_last_deposit_block():
    if network_name() in ('goerli', 'goerli-fork'):
        return 123
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return 456  # TODO
    else:
        assert False, f'Unsupported network "{network_name()}"'


def encode_set_last_deposit_block(last_deposit_block: int) -> Tuple[str, str]:
    deposit_security_module = interface.DepositSecurityModule(
        get_proposed_deposit_security_module_address())
    # deposit_security_module: interface.DepositSecurityModule = contracts.deposit_security_module

    # return agent_forward([(
    #     deposit_security_module.address,
    #     deposit_security_module.unpauseDeposits.encode_input()
    # )])

    return agent_forward([(
    # return (
        deposit_security_module.address,
        deposit_security_module.setLastDepositBlock.encode_input(last_deposit_block)
    # )
    )])


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    lido: interface.Lido = contracts.lido

    proposed_deposit_security_module_address = get_proposed_deposit_security_module_address()
    last_deposit_block = get_last_deposit_block()

    encoded_call_script = encode_call_script([
        # 1. Revoke DEPOSIT_ROLE from the old DepositSecurityModule
        encode_permission_revoke(target_app=lido, permission_name='DEPOSIT_ROLE',
                                 revoke_from=lido_dao_deposit_security_module_address),

        # 2. Grant DEPOSIT_ROLE to the new DepositSecurityModule
        encode_permission_grant(target_app=lido, permission_name='DEPOSIT_ROLE',
                                grant_to=proposed_deposit_security_module_address),

        # 3. Set lastDepositBlock of DepositSecurityModule to ???
        encode_set_last_deposit_block(last_deposit_block),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Revoke DEPOSIT_ROLE from the old DepositSecurityModule; ',
            '2) Grant DEPOSIT_ROLE to the new DepositSecurityModule; ',
            '3) Set lastDepositBlock of DepositSecurityModule to ???. ',
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )


def main():
    tx_params = {'from': get_deployer_account()}

    if get_is_live():
        tx_params['max_fee'] = '300 gwei'
        tx_params['priority_fee'] = '2 gwei'

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5)  # hack for waiting thread #2.
