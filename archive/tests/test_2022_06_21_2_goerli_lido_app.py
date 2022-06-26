"""
Tests for Voting 21/06/2022 [Lido app for Goerli].
"""
import pytest

from brownie import interface

from scripts.vote_2022_06_21_goerli_lido_app import (
    start_vote,
    get_lido_app_address,
    get_lido_app_old_version,
)
from utils.test.tx_tracing_helpers import *
from utils.config import network_name
from utils.config import lido_dao_lido_repo


def get_lido_app_old_content_uri():
    if network_name() in ("goerli", "goerli-fork"):
        return (
            "0x697066733a516d526a43546452626a6b4755613774364832506e7377475a7965636e4e5367386f736b346b593269383278556e"
        )
    elif network_name() in ("mainnet", "mainnet-fork"):
        return (
            "0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053"
        )
    else:
        assert False, f'Unsupported network "{network_name()}"'


def get_lido_app_old_ipfs_cid():
    if network_name() in ("goerli", "goerli-fork"):
        return "QmRjCTdRbjkGUa7t6H2PnswGZyecnNSg8osk4kY2i82xUn"
    elif network_name() in ("mainnet", "mainnet-fork"):
        return "QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS"
    else:
        assert False, f'Unsupported network "{network_name()}"'


lido_old_app = {
    "address": get_lido_app_address(),
    "ipfsCid": get_lido_app_old_ipfs_cid(),
    "content_uri": get_lido_app_old_content_uri(),
    "version": get_lido_app_old_version(),
}


lido_new_app = {
    "address": get_lido_app_address(),
    "ipfsCid": "QmScYxzmmrAV1cDBjL3i7jzaZuiJ76UqdaFZiMgsxoFGzC",
    "content_uri": "0x697066733a516d536359787a6d6d724156316344426a4c3369376a7a615a75694a373655716461465a694d6773786f46477a43",
    "version": (8, 0, 4),
}


def test_vote(helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, bypass_events_decoding, dao_agent, lido):
    # Validate old Lido app
    lido_repo = interface.Repo(lido_dao_lido_repo)
    lido_old_app_from_chain = lido_repo.getLatest()

    print(lido_old_app_from_chain)

    # check old versions of lido app is correct
    assert lido_old_app["address"] == lido_old_app_from_chain[1]
    assert lido_old_app["version"] == lido_old_app_from_chain[0]
    assert lido_old_app["content_uri"] == lido_old_app_from_chain[2]

    # check old ipfs link
    bytes_object = lido_old_app_from_chain[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    lido_old_app_ipfs = f"ipfs:{lido_old_app['ipfsCid']}"
    assert lido_old_app_ipfs == lido_old_ipfs

    # START VOTE
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    # Validate vote items 4: new lido app
    ## check only version and ipfs was changed
    lido_new_app_from_chain = lido_repo.getLatest()
    assert lido_new_app["address"] == lido_new_app_from_chain[1]
    assert lido_new_app["version"] == lido_new_app_from_chain[0]
    assert lido_new_app["content_uri"] == lido_new_app_from_chain[2]

    ## check new ipfs link
    bytes_object = lido_new_app_from_chain[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    lido_new_app_ipfs = f"ipfs:{lido_new_app['ipfsCid']}"
    assert lido_new_app_ipfs == lido_old_ipfs

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return
