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
"""

import time
from typing import (
    Dict, Tuple,
    Optional
)
from brownie.network.transaction import TransactionReceipt
from functools import partial

from utils.voting import create_vote
from utils.evm_script import (
    decode_evm_script,
    encode_call_script,
    calls_info_pretty_print
)
from utils.node_operators import encode_add_operator
from utils.config import (
    prompt_bool,
    get_deployer_account,
    lido_dao_voting_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    lido_dao_lido_repo,
    lido_dao_node_operators_registry_repo,
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

def add_implementation_to_repo(repo, version, address, content_uri):
    return (
      repo.address,
      repo.newVersion.encode_input(
          version,
          address,
          content_uri
      )
    )

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    # Lido contracts
    voting = interface.Voting(
        lido_dao_voting_address
    )
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )
    registry = interface.NodeOperatorsRegistry(
        lido_dao_node_operators_registry
    )
    lido_repo = interface.Repo(
        lido_dao_lido_repo
    )
    nos_repo = interface.Repo(
        lido_dao_node_operators_registry_repo
    )

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

    _encode_add_operator = partial(encode_add_operator, registry=registry)

    encoded_call_script = encode_call_script([
        # 1. Update Lido app IPFS hash
        add_implementation_to_repo(
            lido_repo,
            update_lido_app['version'],
            update_lido_app['address'],
            update_lido_app['content_uri'],
        ),
        # 2.  Update NOS app IPFS hash
        add_implementation_to_repo(
            nos_repo,
            update_node_operators_registry_app['version'],
            update_node_operators_registry_app['address'],
            update_node_operators_registry_app['content_uri'],
        ),
        # 3. Add node operator named Stakin
        _encode_add_operator(**stakin_node_operator),
        # 4. Add node operator named ChainLayer
        _encode_add_operator(**chainlayer_node_operator),
        # 5. Add node operator named Simply Staking
        _encode_add_operator(**simplystaking_node_operator),
        # 6. Add node operator named BridgeTower
        _encode_add_operator(**bridgetower_node_operator),
        # 7. Add node operator named Stakely
        _encode_add_operator(**stakely_node_operator),
        # 8. Add node operator named InfStones
        _encode_add_operator(**infstones_node_operator),
        # 9. Add node operator named HashQuark
        _encode_add_operator(**hashquark_node_operator),
        # 10. Add node operator named ConsenSys Codefi
        _encode_add_operator(**consensyscodefi_node_operator),
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
            '1) Update Lido app IPFS hash to QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS;' #?
            '2) Update NOs app IPFS hash to Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G;' #?
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
        'max_fee': '100 gwei',
        'priority_fee': '2 gwei'
    })
    print(f'Vote created: {vote_id}.')
    time.sleep(5) # hack for waiting thread #2.
