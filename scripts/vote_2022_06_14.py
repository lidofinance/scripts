"""
Voting 14/06/2022.

1. Revoke DEPOSIT_ROLE from old DepositSecurityModule 0xDb149235B6F40dC08810AA69869783Be101790e7
2. Grant DEPOSIT_ROLE to new DepositSecurityModule 0x710B3303fB508a84F10793c1106e32bE873C24cd
3. Set lastDepositBlock of DepositSecurityModule to {{TODO block number}}
4. Set Lido app IPFS hash to QmcweCCxtTGubHuJVwDcTwikUevuvmAJJ7S5uoRicBxvxM

"""
# noinspection PyUnresolvedReferences

import time

from typing import (Dict, Tuple, Optional, List)

from brownie.network.transaction import TransactionReceipt
from brownie import web3

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.agent import agent_forward
from utils.repo import add_implementation_to_lido_app_repo
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts, network_name,
    lido_dao_deposit_security_module_address
)
from utils.permissions import encode_permission_grant, encode_permission_revoke
from utils.brownie_prelude import *


def get_proposed_deposit_security_module_address():
    if network_name() in ('goerli', 'goerli-fork'):
        return '0x7DC1C1ff64078f73C98338e2f17D1996ffBb2eDe'
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return '0x710B3303fB508a84F10793c1106e32bE873C24cd'
    else:
        assert False, f'Unsupported network "{network_name()}"'


def calc_last_deposit_block():
    if network_name() in ('goerli', 'goerli-fork'):
        return 123  # just an arbitrary block number less then the current one
    elif network_name() in ('mainnet', 'mainnet-fork'):
        # TODO: specify the period more accurate
        # 84 hours period and 13 seconds per block
        return web3.eth.block_number + (84 * 60 * 60)  // 13
    else:
        assert False, f'Unsupported network "{network_name()}"'


def get_lido_app_address():
    if network_name() in ('goerli', 'goerli-fork'):
        return '0xb16876f11324Fbf02b9B294FBE307B3DB0C02DBB'
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return '0x47EbaB13B806773ec2A2d16873e2dF770D130b50'
    else:
        assert False, f'Unsupported network "{network_name()}"'


def encode_set_last_deposit_block(last_deposit_block: int) -> Tuple[str, str]:
    deposit_security_module = interface.DepositSecurityModule(
        get_proposed_deposit_security_module_address())

    return agent_forward([(
        deposit_security_module.address,
        deposit_security_module.setLastDepositBlock.encode_input(last_deposit_block)
    )])


def get_new_lido_app_params():
    return {
        'address': get_lido_app_address(),
        'ipfsCid': 'QmcweCCxtTGubHuJVwDcTwikUevuvmAJJ7S5uoRicBxvxM',
        'content_uri': '0x697066733a516d637765434378745447756248754a567744635477696b55657675766d414a4a375335756f526963427876784d',
        'version': (3, 0, 1),
    }


last_deposit_block = None


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    global last_deposit_block

    lido: interface.Lido = contracts.lido

    proposed_deposit_security_module_address = get_proposed_deposit_security_module_address()
    last_deposit_block = calc_last_deposit_block()
    lido_app_update_params = get_new_lido_app_params()

    encoded_call_script = encode_call_script([
        # 1. Revoke DEPOSIT_ROLE from the old DepositSecurityModule
        encode_permission_revoke(target_app=lido, permission_name='DEPOSIT_ROLE',
                                 revoke_from=lido_dao_deposit_security_module_address),

        # 2. Grant DEPOSIT_ROLE to the new DepositSecurityModule
        encode_permission_grant(target_app=lido, permission_name='DEPOSIT_ROLE',
                                grant_to=proposed_deposit_security_module_address),

        # 3. Set lastDepositBlock of DepositSecurityModule to {{TODO}}
        encode_set_last_deposit_block(last_deposit_block),

        # 4. Set Lido app IPFS hash to QmcweCCxtTGubHuJVwDcTwikUevuvmAJJ7S5uoRicBxvxM
        add_implementation_to_lido_app_repo(
            lido_app_update_params['version'],
            lido_app_update_params['address'],
            lido_app_update_params['content_uri'],
        ),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Revoke DEPOSIT_ROLE from the old DepositSecurityModule; ',
            '2) Grant DEPOSIT_ROLE to the new DepositSecurityModule; ',
            '3) Set lastDepositBlock of DepositSecurityModule to {{TBD}}; ',
            '4) Set Lido app IPFS hash to QmcweCCxtTGubHuJVwDcTwikUevuvmAJJ7S5uoRicBxvxM. '
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
