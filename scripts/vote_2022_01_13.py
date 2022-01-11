"""
Voting 13/01/2022.

1. Update Lido app IPFS hash to QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS #?
2. Update NOS app IPFS hash to Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G #?
3. Node Operators Registry:
   Add node operator named Stakin with reward address
   `0xf6b0a1B771633DB40A3e21Cc49fD2FE35669eF46`
   Add node operator named ChainLayer with reward address
   `0xd5aC23b1adE91A054C4974264C9dbdDD0E52BB05`
   Add node operator named Simply Staking with reward address
   `0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd`
   Add node operator named BridgeTower with reward address
   `0x40C20da8d0214A7eF33a84e287992858dB744e6d`
   Add node operator named Stakely with reward address
   `0x77d2CF58aa4da90b3AFCd283646568e4383193BF`
   Add node operator named InfStones with reward address
   `0x60bC65e1ccA448F98578F8d9f9AB64c3BA70a4c3`
   Add node operator named HashQuark with reward address
   `0x065dAAb531e7Cd50f900D644E8caE8A208eEa4E9`
   Add node operator named ConsenSys Codefi with reward address
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

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    voting = interface.Voting(
        lido_dao_voting_address
    )
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )
    registry = interface.NodeOperatorsRegistry(
        lido_dao_node_operators_registry
    )

    # Vote specific addresses and constants:
    # 1. Add eight new node operators (Wave 3).
    stakin_node_operator = {
        'name': 'Stakin',
        'address': '0xf6b0a1B771633DB40A3e21Cc49fD2FE35669eF46' #?
    } 
    chainlayer_node_operator = {
        'name': 'ChainLayer',
        'address': '0xd5aC23b1adE91A054C4974264C9dbdDD0E52BB05' #?
    } 
    simplystaking_node_operator = {
        'name': 'Simply Staking',
        'address': '0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd' #?
    } 
    bridgetower_node_operator = {
        'name': 'BridgeTower',
        'address': '0x40C20da8d0214A7eF33a84e287992858dB744e6d' #?
    } 
    stakely_node_operator = {
        'name': 'Stakely',
        'address': '0x77d2CF58aa4da90b3AFCd283646568e4383193BF' #?
    } 
    infstones_node_operator = {
        'name': 'InfStones',
        'address': '0x60bC65e1ccA448F98578F8d9f9AB64c3BA70a4c3' #?
    } 
    hashquark_node_operator = {
        'name': 'HashQuark',
        'address': '0x065dAAb531e7Cd50f900D644E8caE8A208eEa4E9' #?
    } 
    consensyscodefi_node_operator = {
        'name': 'ConsenSys Codefi',
        'address': '0x5Bc5ec5130f66f13d5C21ac6811A7e624ED3C7c6' #?
    } 

    _encode_add_operator = partial(encode_add_operator, registry=registry)

    encoded_call_script = encode_call_script([
        _encode_add_operator(**stakin_node_operator),
        _encode_add_operator(**chainlayer_node_operator),
        _encode_add_operator(**simplystaking_node_operator),
        _encode_add_operator(**bridgetower_node_operator),

        _encode_add_operator(**stakely_node_operator),
        _encode_add_operator(**infstones_node_operator),
        _encode_add_operator(**hashquark_node_operator),
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
            'TBD'
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
