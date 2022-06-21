"""
Voting for disabling NOs

"""

import time

from typing import (Dict, Tuple, Optional)

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote
from utils.evm_script import encode_call_script
from utils.repo import (
    add_implementation_to_lido_app_repo,
    add_implementation_to_nos_app_repo
)
from utils.kernel import update_app_implementation
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts, network_name
)
from utils.permissions import encode_permission_create
# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *

update_lido_app = {
    'new_address': '0x71c32292a11Dd350c833d6ef27D268a63a57D681',
    'old_address': '0xb16876f11324Fbf02b9B294FBE307B3DB0C02DBB',
    'content_uri': '0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053',
    'id': '0x79ac01111b462384f1b7fba84a17b9ec1f5d2fddcfcb99487d71b443832556ea',
    'version': (9, 0, 0),
}

update_nos_app = {
    'new_address': '0x68d31D8e70d914e4730922f62A3c3d36B80b6041',
    'old_address': '0xbb001978bD0d5b36D95c54025ac6a5822b2b1Aec',
    'content_uri': '0x697066733a516d61375058486d456a346a7332676a4d3976744850747176754b3832695335455950694a6d7a4b4c7a55353847',
    'id': '0x57384c8fcaf2c1c2144974769a6ea4e5cf69090d47f5327f8fc93827f8c0001a',
    'version': (7, 0, 0),
}

def get_beacon_validators():
    lido: interface.Lido = contracts.lido
    return

def disable_validator(id):
    nos: interface.NodeOperatorsRegistry = contracts.node_operators_registry
    return (
        nos.address,
        nos.disableNodeOperator.encode_input(id))

def decrease_validators_number(validators_number):
    lido: interface.Lido = contracts.lido
    current_validators = lido.getBeaconStat()
    return (
        lido.address,
        lido.setValidatorsNumber.encode_input(current_validators[1] - validators_number))


def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False,
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    print(disable_validator(20))

    encoded_call_script = encode_call_script([
        add_implementation_to_lido_app_repo(
            update_lido_app['version'],
            update_lido_app['new_address'],
            update_lido_app['content_uri']
        ),
        update_app_implementation(
            update_lido_app['id'],
            update_lido_app['new_address']
        ),
        add_implementation_to_nos_app_repo(
            update_nos_app['version'],
            update_nos_app['new_address'],
            update_nos_app['content_uri']
        ),
        update_app_implementation(
            update_nos_app['id'],
            update_nos_app['new_address']
        ),
        disable_validator(20),
        disable_validator(21),
        disable_validator(22),
        disable_validator(31),
        disable_validator(33),
        disable_validator(34),
        disable_validator(35),
        decrease_validators_number(193),
        update_app_implementation(
            update_lido_app['id'],
            update_lido_app['old_address']
        ),
        update_app_implementation(
            update_nos_app['id'],
            update_nos_app['old_address']
        )
    ])

    return confirm_vote_script(encoded_call_script, silent) and create_vote(
        vote_desc=(
            'Omnibus vote: '
            '1) Publish new implementation in Lido app APM repo; ',
            '2) Updating implementation of Lido app; ',
            '3) Publishing new implementation in Node Operators Registry app APM repo; ',
            '4) Updating implementation of Node Operators Registry app; ',
            '5-11) Stoping validator with ids 20, 21, 22, 31, 33, 34, 35; ',
            '12) Decreasing validators number by sum of disabled validators; ',
            '13) Updating implementation of Lido app to old one; ',
            '14) Updating implementation of Node Operators Registry app to old one; ',
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
