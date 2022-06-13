"""
Voting 14/06/2022.

1. Revoke DEPOSIT_ROLE from old DepositSecurityModule 0xDb149235B6F40dC08810AA69869783Be101790e7
2. Grant DEPOSIT_ROLE to new DepositSecurityModule 0x710B3303fB508a84F10793c1106e32bE873C24cd
3. Set lastDepositBlock of DepositSecurityModule to {{TODO block number}}
4. Set Lido app IPFS hash to QmRjCTdRbjkGUa7t6H2PnswGZyecnNSg8osk4kY2i82xUn

"""
# noinspection PyUnresolvedReferences

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt
from brownie import web3

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.agent import agent_forward
from utils.repo import add_implementation_to_lido_app_repo
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts
)
from utils.permissions import encode_permission_grant, encode_permission_revoke
from utils.brownie_prelude import *


def encode_set_last_deposit_block(new_dsm_address: str, last_deposit_block: int) -> Tuple[str, str]:
    deposit_security_module = interface.DepositSecurityModule(new_dsm_address)

    return agent_forward([(
        deposit_security_module.address,
        deposit_security_module.setLastDepositBlock.encode_input(last_deposit_block)
    )])


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    lido: interface.Lido = contracts.lido

    current_deposit_security_module_address = '0xDb149235B6F40dC08810AA69869783Be101790e7'
    proposed_deposit_security_module_address = '0x710B3303fB508a84F10793c1106e32bE873C24cd'
    last_deposit_block: int = web3.eth.block_number + (84 * 60 * 60)  // 13

    lido_app_update_params = {
        'address': '0x47EbaB13B806773ec2A2d16873e2dF770D130b50',
        'ipfsCid': 'QmRjCTdRbjkGUa7t6H2PnswGZyecnNSg8osk4kY2i82xUn',
        'content_uri': '0x697066733a516d526a43546452626a6b4755613774364832506e7377475a7965636e4e5367386f736b346b593269383278556e',
        'version': (4, 0, 0)
    }

    call_script_items = [
        # 1. Revoke DEPOSIT_ROLE from the old DepositSecurityModule
        encode_permission_revoke(target_app=lido, permission_name='DEPOSIT_ROLE',
                                 revoke_from=current_deposit_security_module_address),

        # 2. Grant DEPOSIT_ROLE to the new DepositSecurityModule
        encode_permission_grant(target_app=lido, permission_name='DEPOSIT_ROLE',
                                grant_to=proposed_deposit_security_module_address),

        # 3. Set lastDepositBlock of DepositSecurityModule to {{TODO}}
        encode_set_last_deposit_block(proposed_deposit_security_module_address, last_deposit_block),

        # 4. Set Lido app IPFS hash to QmRjCTdRbjkGUa7t6H2PnswGZyecnNSg8osk4kY2i82xUn
        add_implementation_to_lido_app_repo(
            lido_app_update_params['version'],
            lido_app_update_params['address'],
            lido_app_update_params['content_uri'],
        )
    ]

    vote_desc_items = [
        '1) Revoke DEPOSIT_ROLE from the old DepositSecurityModule',
        '2) Grant DEPOSIT_ROLE to the new DepositSecurityModule',
        '3) Set lastDepositBlock of DepositSecurityModule to {{TBD}}',
        '4) Set Lido app IPFS hash to QmRjCTdRbjkGUa7t6H2PnswGZyecnNSg8osk4kY2i82xUn'
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)

def main():
    tx_params = {'from': get_deployer_account()}

    if get_is_live():
        tx_params['max_fee'] = '300 gwei'
        tx_params['priority_fee'] = '2 gwei'

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5)  # hack for waiting thread #2.
