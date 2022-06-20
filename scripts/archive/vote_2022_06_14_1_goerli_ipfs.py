"""
Voting 14/06/2022-1 [patch for Goerli].

1. Set Lido app IPFS hash to QmURb5WALQG8b2iWuGmyGaQ7kY5q5vd4oNK5ZVDLjRjj2m

"""
# noinspection PyUnresolvedReferences

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.agent import agent_forward
from utils.repo import add_implementation_to_lido_app_repo
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts, network_name
)

from utils.brownie_prelude import *


def get_lido_app_address():
    if network_name() in ('goerli', 'goerli-fork'):
        return '0xb16876f11324Fbf02b9B294FBE307B3DB0C02DBB'
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return '0x47EbaB13B806773ec2A2d16873e2dF770D130b50'
    else:
        assert False, f'Unsupported network "{network_name()}"'


def get_lido_app_old_version():
    if network_name() in ('goerli', 'goerli-fork'):
        return (8, 0, 1)
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return (3, 0, 0)
    else:
        assert False, f'Unsupported network "{network_name()}"'


def get_new_lido_app_params():
    return {
        'address': get_lido_app_address(),
        'ipfsCid': 'QmURb5WALQG8b2iWuGmyGaQ7kY5q5vd4oNK5ZVDLjRjj2m',
        'content_uri': '0x697066733a516d5552623557414c5147386232695775476d79476151376b593571357664346f4e4b355a56444c6a526a6a326d',
        'version': (8, 0, 2)
    }


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    global last_deposit_block

    lido_app_update_params = get_new_lido_app_params()

    encoded_call_script = encode_call_script([
        # 1. Set Lido app IPFS hash to QmURb5WALQG8b2iWuGmyGaQ7kY5q5vd4oNK5ZVDLjRjj2m
        add_implementation_to_lido_app_repo(
            lido_app_update_params['version'],
            lido_app_update_params['address'],
            lido_app_update_params['content_uri'],
        )
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Set Lido app IPFS hash to QmURb5WALQG8b2iWuGmyGaQ7kY5q5vd4oNK5ZVDLjRjj2m.'
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
