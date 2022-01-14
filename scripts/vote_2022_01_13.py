"""
Voting 13/01/2022.

1. Update Lido app IPFS hash to `QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS`
2. Update NOS app IPFS hash to `Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G`
3. Add node operator named Stakin with reward address
   `0xf6b0a1B771633DB40A3e21Cc49fD2FE35669eF46`
4. Add node operator named ChainLayer with reward address
   `0xd5aC23b1adE91A054C4974264C9dbdDD0E52BB05`
5. Add node operator named Simply Staking with reward address
   `0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd`
6. Add node operator named BridgeTower with reward address
   `0x40C20da8d0214A7eF33a84e287992858dB744e6d`
7. Add node operator named Stakely with reward address
   `0x77d2CF58aa4da90b3AFCd283646568e4383193BF`
8. Add node operator named InfStones with reward address
   `0x60bC65e1ccA448F98578F8d9f9AB64c3BA70a4c3`
9. Add node operator named HashQuark with reward address
   `0x065dAAb531e7Cd50f900D644E8caE8A208eEa4E9`
10. Add node operator named ConsenSys Codefi with reward address
   `0x5Bc5ec5130f66f13d5C21ac6811A7e624ED3C7c6`

Vote passed & executed on Jan-14-2022 12:10:58 PM +UTC, block #14003547.
TX URL: https://etherscan.io/tx/0xd7b6f290f6f7447e12ba4a3781ea08ad7cb699924e7bf75cf808c79533f88969

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.node_operators import encode_add_operator_lido
from utils.config import get_deployer_account

from utils.repo import (
    add_implementation_to_lido_app_repo,
    add_implementation_to_nos_app_repo
)

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    # Vote specific addresses and constants:
    # 1. Update Lido app IPFS hash
    update_lido_app = {
        'address': '0xC7B5aF82B05Eb3b64F12241B04B2cF14469E39F7',
        'ipfsCid': 'QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS',
        'content_uri': '0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053',
        'version': (2, 0, 1),
    }
    # 2.  Update NOS app IPFS hash
    update_node_operators_registry_app = {
        'address': '0xec3567ae258639a0FF5A02F7eAF4E4aE4416C5fe',
        'ipfsCid': 'Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G',
        'content_uri': '0x697066733a516d61375058486d456a346a7332676a4d3976744850747176754b3832695335455950694a6d7a4b4c7a55353847',
        'version': (2, 0, 1),
    }
    # 3. Add node operator named Stakin
    stakin_node_operator = {
        'name': 'Stakin',
        'address': '0xf6b0a1B771633DB40A3e21Cc49fD2FE35669eF46'
    } 
    # 4. Add node operator named ChainLayer
    chainlayer_node_operator = {
        'name': 'ChainLayer',
        'address': '0xd5aC23b1adE91A054C4974264C9dbdDD0E52BB05'
    } 
    # 5. Add node operator named Simply Staking
    simplystaking_node_operator = {
        'name': 'Simply Staking',
        'address': '0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd'
    } 
    # 6. Add node operator named BridgeTower
    bridgetower_node_operator = {
        'name': 'BridgeTower',
        'address': '0x40C20da8d0214A7eF33a84e287992858dB744e6d'
    } 
    # 7. Add node operator named Stakely
    stakely_node_operator = {
        'name': 'Stakely',
        'address': '0x77d2CF58aa4da90b3AFCd283646568e4383193BF'
    } 
    # 8. Add node operator named InfStones
    infstones_node_operator = {
        'name': 'InfStones',
        'address': '0x60bC65e1ccA448F98578F8d9f9AB64c3BA70a4c3'
    } 
    # 9. Add node operator named HashQuark
    hashquark_node_operator = {
        'name': 'HashQuark',
        'address': '0x065dAAb531e7Cd50f900D644E8caE8A208eEa4E9'
    } 
    # 10. Add node operator named ConsenSys Codefi
    consensyscodefi_node_operator = {
        'name': 'ConsenSys Codefi',
        'address': '0x5Bc5ec5130f66f13d5C21ac6811A7e624ED3C7c6'
    } 

    encoded_call_script = encode_call_script([
        # 1. Update Lido app IPFS hash
        add_implementation_to_lido_app_repo(
            update_lido_app['version'],
            update_lido_app['address'],
            update_lido_app['content_uri'],
        ),
        # 2.  Update NOS app IPFS hash
        add_implementation_to_nos_app_repo(
            update_node_operators_registry_app['version'],
            update_node_operators_registry_app['address'],
            update_node_operators_registry_app['content_uri'],
        ),
        # 3. Add node operator named Stakin
        encode_add_operator_lido(**stakin_node_operator),
        # 4. Add node operator named ChainLayer
        encode_add_operator_lido(**chainlayer_node_operator),
        # 5. Add node operator named Simply Staking
        encode_add_operator_lido(**simplystaking_node_operator),
        # 6. Add node operator named BridgeTower
        encode_add_operator_lido(**bridgetower_node_operator),
        # 7. Add node operator named Stakely
        encode_add_operator_lido(**stakely_node_operator),
        # 8. Add node operator named InfStones
        encode_add_operator_lido(**infstones_node_operator),
        # 9. Add node operator named HashQuark
        encode_add_operator_lido(**hashquark_node_operator),
        # 10. Add node operator named ConsenSys Codefi
        encode_add_operator_lido(**consensyscodefi_node_operator),
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Update Lido app IPFS hash to QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS;'
            '2) Update NOs app IPFS hash to Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G;'
            '3) Add Stakin node operator;'
            '4) Add ChainLayer node operator;'
            '5) Add Simply Staking node operator;'
            '6) Add BridgeTower node operator;'
            '7) Add Stakely node operator;'
            '8) Add InfStones node operator;'
            '9) Add HashQuark node operator;'
            '10) Add ConsenSys Codefi node operator.'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )

def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'max_fee': '200 gwei',
        'priority_fee': '2 gwei'
    })

    vote_id >= 0 and print(f'Vote created: {vote_id}.')

    time.sleep(5) # hack for waiting thread #2.
