"""
Voting 21/06/2022.
1. Add node operator named 'RockLogic GmbH' with reward address `0x49df3cca2670eb0d591146b16359fe336e476f29`
2. Add node operator named 'CryptoManufaktur' with reward address `0x59eCf48345A221E0731E785ED79eD40d0A94E2A5`
3. Add node operator named 'Kukis Global' with reward address `0x8845D7F2Bbfe82249c3B95e378A6eD039Dd953F5`
4. Add node operator named 'Nethermind' with reward address `0x237DeE529A47750bEcdFa8A59a1D766e3e7B5F91`
"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote, bake_vote_items
from utils.node_operators import encode_add_operator_lido
from utils.config import get_deployer_account

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    
    # Vote specific addresses and constants:
    # 1. Add node operator named RockLogic GmbH
    rocklogic_node_operator = {
        'name': 'RockLogic GmbH',
        'address': '0x49df3cca2670eb0d591146b16359fe336e476f29'
    } 
    # 2. Add node operator named CryptoManufaktur
    cryptomanufaktur_node_operator = {
        'name': 'CryptoManufaktur',
        'address': '0x59eCf48345A221E0731E785ED79eD40d0A94E2A5'
    } 
    # 3. Add node operator named Kukis Global
    kukisglobal_node_operator = {
        'name': 'Kukis Global',
        'address': '0x8845D7F2Bbfe82249c3B95e378A6eD039Dd953F5'
    } 
    # 4. Add node operator named Nethermind
    nethermind_node_operator = {
        'name': 'Nethermind',
        'address': '0x237DeE529A47750bEcdFa8A59a1D766e3e7B5F91'
    } 

    vote_items = bake_vote_items(
        vote_desc_items=[
            '1) Add RockLogic GmbH node operator; ',
            '2) Add CryptoManufaktur node operator; ',
            '3) Add Kukis Global node operator; ',
            '4) Add Nethermind node operator; ',
        ],
        call_script_items=[
            # 1. Add node operator named RockLogic GmbH
            encode_add_operator_lido(**rocklogic_node_operator),
            # 2. Add node operator named CryptoManufaktur
            encode_add_operator_lido(**cryptomanufaktur_node_operator),
            # 3. Add node operator named Kukis Global
            encode_add_operator_lido(**kukisglobal_node_operator),
            # 4. Add node operator named Nethermind
            encode_add_operator_lido(**nethermind_node_operator)
        ]
    )
    
    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'max_fee': '200 gwei',
        'priority_fee': '2 gwei'
    })

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5) # hack for waiting thread #2.
    

