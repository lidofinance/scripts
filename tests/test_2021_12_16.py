"""
Tests for voting 16/12/2021.
"""

from sys import version
from brownie.network.main import priority_fee
from scripts.vote_2021_12_16 import start_vote, burnSteth
from brownie import interface
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

def test_2021_12_16(
    helpers, accounts, ldo_holder, dao_voting, lido
):

    #set priority_fee for test on london hardfork
    #priority_fee("2 gwei")

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

    chorusAddr = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'

    totalSharesBefore = lido.getTotalShares()
    sharesChorusBefore = lido.sharesOf(chorusAddr)

    sharesToBurn = 32145684728326685744
    
    vote_id, _ = start_vote({ 'from': ldo_holder }, silent=True)
    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='5 ether'
    )

    display_voting_events(tx)

    ### validate vote events
    assert count_vote_items_by_events(tx) == 3, "Incorrect voting items count"

    #check burned shares
    totalSharesAfter = lido.getTotalShares()
    sharesChorusAfter = lido.sharesOf(chorusAddr)

    assert totalSharesBefore - totalSharesAfter == sharesToBurn
    assert sharesChorusBefore - sharesChorusAfter == sharesToBurn

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
