"""
Tests for Voting 14/06/2022-1 [patch for Goerli].
"""
import pytest

from brownie import interface

from scripts.vote_2022_06_14_1_goerli_ipfs import (
    start_vote,
    get_lido_app_address,
    get_lido_app_old_version,
)
from tx_tracing_helpers import *
from utils.config import network_name
from utils.config import lido_dao_lido_repo

def get_lido_app_old_content_uri():
    if network_name() in ('goerli', 'goerli-fork'):
        return '0x697066733a516d637765434378745447756248754a567744635477696b55657675766d414a4a375335756f526963427876784d'
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return '0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053'
    else:
        assert False, f'Unsupported network "{network_name()}"'


def get_lido_app_old_ipfs_cid():
    if network_name() in ('goerli', 'goerli-fork'):
        return 'QmcweCCxtTGubHuJVwDcTwikUevuvmAJJ7S5uoRicBxvxM'
    elif network_name() in ('mainnet', 'mainnet-fork'):
        return 'QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS'
    else:
        assert False, f'Unsupported network "{network_name()}"'


lido_old_app = {
    'address': get_lido_app_address(),
    'ipfsCid': get_lido_app_old_ipfs_cid(),
    'content_uri': get_lido_app_old_content_uri(),
    'version': get_lido_app_old_version(),
}


lido_new_app = {
    'address': get_lido_app_address(),
    'ipfsCid': 'QmURb5WALQG8b2iWuGmyGaQ7kY5q5vd4oNK5ZVDLjRjj2m',
    'content_uri': '0x697066733a516d5552623557414c5147386232695775476d79476151376b593571357664346f4e4b355a56444c6a526a6a326d',
    'version': (8, 0, 2)
}



def test_vote(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding,
    dao_agent, lido
):
    # Validate old Lido app
    lido_repo = interface.Repo(lido_dao_lido_repo)
    lido_old_app_from_chain = lido_repo.getLatest()

    print(lido_old_app_from_chain)

    # check old versions of lido app is correct
    assert lido_old_app['address'] == lido_old_app_from_chain[1]
    assert lido_old_app['version'] == lido_old_app_from_chain[0]
    assert lido_old_app['content_uri'] == lido_old_app_from_chain[2]

    # check old ipfs link
    bytes_object = lido_old_app_from_chain[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    lido_old_app_ipfs = f"ipfs:{lido_old_app['ipfsCid']}"
    assert lido_old_app_ipfs == lido_old_ipfs


    # START VOTE
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, 'Incorrect voting items count'

    # Validate vote items 4: new lido app
    ## check only version and ipfs was changed
    lido_new_app_from_chain = lido_repo.getLatest()
    assert lido_new_app['address'] == lido_new_app_from_chain[1]
    assert lido_new_app['version'] == lido_new_app_from_chain[0]
    assert lido_new_app['content_uri'] == lido_new_app_from_chain[2]

    ## check new ipfs link
    bytes_object = lido_new_app_from_chain[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    lido_new_app_ipfs = f"ipfs:{lido_new_app['ipfsCid']}"
    assert lido_new_app_ipfs == lido_old_ipfs

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ('goerli', 'goerli-fork'):
        return
