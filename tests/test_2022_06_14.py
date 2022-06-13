"""
Tests for voting 14/06/2022.
"""
import pytest

from brownie import interface, web3

from scripts.vote_2022_06_14 import start_vote
from tx_tracing_helpers import *
from utils.config import (contracts, lido_dao_steth_address)
from event_validators.permission import (Permission, validate_permission_revoke_event, validate_permission_grant_event)
from event_validators.aragon import validate_push_to_repo_event
from utils.config import lido_dao_lido_repo

old_dsm_address: str = "0xDb149235B6F40dC08810AA69869783Be101790e7"
new_dsm_address: str = "0x710B3303fB508a84F10793c1106e32bE873C24cd"

# DEPOSIT_ROLE on old DepositSecurityModule
permission_old_deposit_role = Permission(
    entity=old_dsm_address,
    app=lido_dao_steth_address,  # Lido
    role='0x2561bf26f818282a3be40719542054d2173eb0d38539e8a8d3cff22f29fd2384')


# DEPOSIT_ROLE on new DepositSecurityModule
permission_new_deposit_role = Permission(
    entity=new_dsm_address,
    app=lido_dao_steth_address,  # Lido
    role='0x2561bf26f818282a3be40719542054d2173eb0d38539e8a8d3cff22f29fd2384')


lido_old_app = {
    'address': '0x47ebab13b806773ec2a2d16873e2df770d130b50',
    'ipfsCid': 'QmQkJMtvu4tyJvWrPXJfjLfyTWn959iayyNjp7YqNzX7pS',
    'content_uri': '0x697066733a516d516b4a4d7476753474794a76577250584a666a4c667954576e393539696179794e6a703759714e7a58377053',
    'version': (3, 0, 0),
}


lido_new_app = {
    'address': '0x47ebab13b806773ec2a2d16873e2df770d130b50',
    'ipfsCid': 'QmRjCTdRbjkGUa7t6H2PnswGZyecnNSg8osk4kY2i82xUn',
    'content_uri': '0x697066733a516d526a43546452626a6b4755613774364832506e7377475a7965636e4e5367386f736b346b593269383278556e',
    'version': (4, 0, 0),
}


def test_vote(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding,
    dao_agent, lido
):
    acl: interface.ACL = contracts.acl
    proposed_deposit_security_module: interface.DepositSecurityModule = interface.DepositSecurityModule(
        new_dsm_address
    )

    assert proposed_deposit_security_module.getOwner() == dao_agent.address
    assert acl.hasPermission(*permission_old_deposit_role)
    assert not acl.hasPermission(*permission_new_deposit_role)

    # Validate old Lido app
    lido_repo = interface.Repo(lido_dao_lido_repo)
    lido_old_app_from_chain = lido_repo.getLatest()

    # check old versions of lido app is correct
    assert lido_old_app['address'] == lido_old_app_from_chain[1]
    assert lido_old_app['version'] == lido_old_app_from_chain[0]
    assert lido_old_app['content_uri'] == lido_old_app_from_chain[2]

    # check old ipfs link
    bytes_object = lido_old_app_from_chain[2][:]
    lido_old_ipfs = bytes_object.decode("ASCII")
    lido_old_app_ipfs = f"ipfs:{lido_old_app['ipfsCid']}"
    assert lido_old_app_ipfs == lido_old_ipfs

    #FIXME
    last_deposited_block: int = web3.eth.block_number + (84 * 60 * 60)  // 13

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 4, 'Incorrect voting items count'

    # Validate vote items 1-3
    assert not acl.hasPermission(*permission_old_deposit_role)
    assert acl.hasPermission(*permission_new_deposit_role)
    assert proposed_deposit_security_module.getLastDepositBlock() == last_deposited_block

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

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    validate_permission_revoke_event(evs[0], permission_old_deposit_role)
    validate_permission_grant_event(evs[1], permission_new_deposit_role)
    # NB: for evs[2] (setLastDepositBlock) there is no event
    validate_push_to_repo_event(evs[3], lido_new_app['version'])
