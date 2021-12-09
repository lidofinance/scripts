"""
test for app upgrades
"""

from sys import version
from scripts.upgrade_apps import start_vote
from brownie.network import priority_fee
from brownie import interface
from brownie.convert import to_bytes

from utils.config import (
    prompt_bool,
    get_deployer_account,
    lido_dao_voting_address,
    lido_dao_token_manager_address,
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
    'ipfsCid': 'QmPR28q1qWFDcd1aYjnwqpFQYkUofoyBzQ6KCHE6PSQY6P',
    'content_uri': '0x697066733a516d5052323871317157464463643161596a6e7771704651596b556f666f79427a51364b43484536505351593650',
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
    'ipfsCid': 'QmavVvQ1owa14nvpiwHa2WowAjGv5qt93itQoQxFzHi7se',
    'content_uri': '0x697066733a516d6176567651316f776131346e76706977486132576f77416a477635717439336974516f5178467a4869377365',
    'id': '0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d',
    'version': (2, 0, 1),
}

def test_2021_12_02(
    helpers, accounts, ldo_holder, dao_voting
):
    priority_fee("2 gwei")

    accounts[0].transfer(ldo_holder, "5 ether")

    ### LIDO APP
    lido_repo = interface.Repo(lido_dao_lido_repo)
    repoLidoOldVersion = lido_repo.getLatest();

    #check old versions of lido app is correct
    assert lido_old_app['address'] == repoLidoOldVersion[1]
    assert lido_old_app['version'] == repoLidoOldVersion[0]
    assert lido_old_app['content_uri'] == repoLidoOldVersion[2]

    #check old ipfs link
    bytes_object = repoLidoOldVersion[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    lido_old_app_ipfs = f"ipfs:{lido_old_app['ipfsCid']}"
    assert lido_old_app_ipfs == lido_old_ipfs

    ### NOS APP
    nos_repo = interface.Repo(lido_dao_node_operators_registry_repo)
    repoNosOldVersion = nos_repo.getLatest();

    #check old versions of lido app is correct
    assert nos_old_app['address'] == repoNosOldVersion[1]
    assert nos_old_app['version'] == repoNosOldVersion[0]
    assert nos_old_app['content_uri'] == repoNosOldVersion[2]

    #check old ipfs link
    bytes_object = repoNosOldVersion[2][:]
    nos_old_ipfs = bytes_object.decode("ASCII")
    nos_old_app_ipfs = f"ipfs:{nos_old_app['ipfsCid']}"
    assert nos_old_app_ipfs == nos_old_ipfs
    
    vote_id, _ = start_vote({ 'from': ldo_holder }, silent=True)
    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='5 ether')

    ### LIDO APP
    #check only version and ipfs was changed
    repoNewVersion = lido_repo.getLatest();
    assert lido_new_app['address'] == repoNewVersion[1]
    assert lido_new_app['version'] == repoNewVersion[0]
    assert lido_new_app['content_uri'] == repoNewVersion[2]

    #check new ipfs link
    bytes_object = repoNewVersion[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    lido_new_app_ipfs = f"ipfs:{lido_new_app['ipfsCid']}"
    assert lido_new_app_ipfs == lido_old_ipfs

    ### NOS APP
    #check only version and ipfs was changed
    repoNosNewVersion = nos_repo.getLatest();
    assert nos_new_app['address'] == repoNosNewVersion[1]
    assert nos_new_app['version'] == repoNosNewVersion[0]
    assert nos_new_app['content_uri'] == repoNosNewVersion[2]

    #check new ipfs link
    bytes_object = repoNosNewVersion[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    nos_new_app_ipfs = f"ipfs:{nos_new_app['ipfsCid']}"
    assert nos_new_app_ipfs == lido_old_ipfs
