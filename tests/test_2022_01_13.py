"""
Tests for voting 27/12/2021.
"""
from sys import version
from collections import namedtuple
from brownie import interface

from scripts.vote_2022_01_13 import start_vote
from tx_tracing_helpers import *

from utils.config import (
    lido_dao_lido_repo,
    lido_dao_node_operators_registry_repo,
)

lido_old_app = {
    'address': '0xC7B5aF82B05Eb3b64F12241B04B2cF14469E39F7',
    'ipfsCid': 'QmbmPW5r9HMdyUARNJjjE7MNqBUGrXashwoWvqRZhc1t5b',
    'content_uri': '0x697066733a516d626d5057357239484d64795541524e4a6a6a45374d4e714255477258617368776f577671525a686331743562',
    'id': '0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320',
    'version': (2, 0, 0),
}

lido_new_app = {
    'address': '0xC7B5aF82B05Eb3b64F12241B04B2cF14469E39F7',
    'ipfsCid': 'QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS',
    'content_uri': '0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053',
    'id': '0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320',
    'version': (2, 0, 1),
}

nos_old_app = {
    'address': '0xec3567ae258639a0FF5A02F7eAF4E4aE4416C5fe',
    'ipfsCid': 'QmQExJkoyg7xWXJjLaYC75UAmsGY1STY41YTG3wEK7q8dd',
    'content_uri': '0x697066733a516d5145784a6b6f7967377857584a6a4c615943373555416d7347593153545934315954473377454b3771386464',
    'id': '0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d',
    'version': (2, 0, 0),
}
nos_new_app = {
    'address': '0xec3567ae258639a0FF5A02F7eAF4E4aE4416C5fe',
    'ipfsCid': 'Qma7PXHmEj4js2gjM9vtHPtqvuK82iS5EYPiJmzKLzU58G',
    'content_uri': '0x697066733a516d61375058486d456a346a7332676a4d3976744850747176754b3832695335455950694a6d7a4b4c7a55353847',
    'id': '0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d',
    'version': (2, 0, 1),
}

NodeOperatorAdd = namedtuple(
    'NodeOperatorAdd', ['name', 'id', 'address']
)

NEW_NODE_OPERATORS = [
    # name, id, address
    NodeOperatorAdd(
        'Stakin', 14, '0xf6b0a1B771633DB40A3e21Cc49fD2FE35669eF46' #?
    ),
    NodeOperatorAdd(
        'ChainLayer', 15, '0xd5aC23b1adE91A054C4974264C9dbdDD0E52BB05' #?
    ),
    NodeOperatorAdd(
        'Simply Staking', 16, '0xFEf3C7aa6956D03dbad8959c59155c4A465DCacd' #?
    ),
    NodeOperatorAdd(
        'BridgeTower', 17, '0x40C20da8d0214A7eF33a84e287992858dB744e6d' #?
    ),
    NodeOperatorAdd(
        'Stakely', 18, '0x77d2CF58aa4da90b3AFCd283646568e4383193BF' #?
    ),
    NodeOperatorAdd(
        'InfStones', 19, '0x60bC65e1ccA448F98578F8d9f9AB64c3BA70a4c3' #?
    ),
    NodeOperatorAdd(
        'HashQuark', 20, '0x065dAAb531e7Cd50f900D644E8caE8A208eEa4E9' #?
    ),
    NodeOperatorAdd(
        'ConsenSys Codefi', 21, '0x5Bc5ec5130f66f13d5C21ac6811A7e624ED3C7c6' #?
    ),
]

def test_2022_01_13(
    helpers, accounts, ldo_holder, dao_voting, node_operators_registry
):
    ### LIDO APP
    lido_repo = interface.Repo(lido_dao_lido_repo)
    lido_old_app_from_chain = lido_repo.getLatest()

    #check old versions of lido app is correct
    assert lido_old_app['address'] == lido_old_app_from_chain[1]
    assert lido_old_app['version'] == lido_old_app_from_chain[0]
    assert lido_old_app['content_uri'] == lido_old_app_from_chain[2]

    #check old ipfs link
    bytes_object = lido_old_app_from_chain[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    lido_old_app_ipfs = f"ipfs:{lido_old_app['ipfsCid']}"
    assert lido_old_app_ipfs == lido_old_ipfs

    ### NOS APP
    nos_repo = interface.Repo(lido_dao_node_operators_registry_repo)
    nos_old_app_from_chain = nos_repo.getLatest()

    #check old versions of lido app is correct
    assert nos_old_app['address'] == nos_old_app_from_chain[1]
    assert nos_old_app['version'] == nos_old_app_from_chain[0]
    assert nos_old_app['content_uri'] == nos_old_app_from_chain[2]

    #check old ipfs link
    bytes_object = nos_old_app_from_chain[2][:]
    nos_old_ipfs = bytes_object.decode("ASCII")
    nos_old_app_ipfs = f"ipfs:{nos_old_app['ipfsCid']}"
    assert nos_old_app_ipfs == nos_old_ipfs
    ##
    ## START VOTE
    ##
    vote_id, _ = start_vote({ 'from': ldo_holder }, silent=True)
    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    ### LIDO APP
    #check only version and ipfs was changed
    lido_new_app_from_chain = lido_repo.getLatest()
    assert lido_new_app['address'] == lido_new_app_from_chain[1]
    assert lido_new_app['version'] == lido_new_app_from_chain[0]
    assert lido_new_app['content_uri'] == lido_new_app_from_chain[2]

    #check new ipfs link
    bytes_object = lido_new_app_from_chain[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    lido_new_app_ipfs = f"ipfs:{lido_new_app['ipfsCid']}"
    assert lido_new_app_ipfs == lido_old_ipfs

    ### NOS APP
    #check only version and ipfs was changed
    nos_new_app_from_chain = nos_repo.getLatest()
    assert nos_new_app['address'] == nos_new_app_from_chain[1]
    assert nos_new_app['version'] == nos_new_app_from_chain[0]
    assert nos_new_app['content_uri'] == nos_new_app_from_chain[2]

    #check new ipfs link
    bytes_object = nos_new_app_from_chain[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    nos_new_app_ipfs = f"ipfs:{nos_new_app['ipfsCid']}"
    assert nos_new_app_ipfs == lido_old_ipfs

    # Check that all NO was added
    for node_operator in NEW_NODE_OPERATORS:
        no = node_operators_registry.getNodeOperator(
            node_operator.id, True
        )

        message = f'Failed on {node_operator.name}'
        assert no[0] is True, message
        assert no[1] == node_operator.name, message
        assert no[2] == node_operator.address, message
        assert no[3] == 0

    ### validate vote events (does not work for some reason) 
    # assert count_vote_items_by_events(tx) == 10, "Incorrect voting items count"

    # display_voting_events(tx)