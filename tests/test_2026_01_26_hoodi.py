from brownie import interface, web3, reverts
from brownie.network.transaction import TransactionReceipt
from utils.evm_script import encode_call_script
from utils.ipfs import get_lido_vote_cid_from_str
from utils.permission_parameters import Param, Op, ArgumentValue
from utils.test.event_validators.permission import Permission, validate_permission_grantp_event
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.test.tx_tracing_helpers import (
    count_vote_items_by_events,
    display_voting_events,
    group_voting_events_from_receipt,
)
from utils.balance import set_balance
from utils.voting import find_metadata_by_vote_id

from scripts.vote_2026_01_26_hoodi import (
    start_vote,
    get_vote_items,
)


VOTING = "0x49B3512c44891bef83F8967d075121Bd1b07a01B"
TARGET_NO_REGISTRY = "0x682E94d2630846a503BDeE8b6810DF71C9806891"
ACL = "0x78780e70Eae33e2935814a327f7dB6c01136cc62"
NEW_MANAGER_ADDRESS = "0xc8195bb2851d7129D9100af9d65Bd448A6dE11eF"
MANAGE_SIGNING_KEYS = web3.keccak(text="MANAGE_SIGNING_KEYS").hex()
OPERATOR_ID = 1
EXPECTED_REWARD_ADDRESS = "0x031624fAD4E9BFC2524e7a87336C4b190E70BCA8"

EXPECTED_VOTE_ID = 56
EXPECTED_VOTE_EVENTS_COUNT = 1
IPFS_DESCRIPTION_HASH = "bafkreies4yycczkmfgwexirpnogbzlo7j262svtrwcj5k2x7ashyvhnaqm"


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env):
    voting = interface.Voting(VOTING)
    no = interface.NodeOperatorsRegistry(TARGET_NO_REGISTRY)
    perm_param = Param(0, Op.EQ, ArgumentValue(OPERATOR_ID))
    perm_param_uint = perm_param.to_uint256()

    # =========================================================================
    # ======================== Identify or Create vote ========================
    # =========================================================================
    if vote_ids_from_env:
        vote_id = vote_ids_from_env[0]
        assert vote_id == EXPECTED_VOTE_ID
    elif voting.votesLength() > EXPECTED_VOTE_ID:
        vote_id = EXPECTED_VOTE_ID
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    _, call_script_items = get_vote_items()
    onchain_script = voting.getVote(vote_id)["script"]
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()

    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =====================================================================
        # ========================= Before voting checks ======================
        # =====================================================================
        
        # Item 1
        assert no.getNodeOperator(OPERATOR_ID, True)["rewardAddress"] == EXPECTED_REWARD_ADDRESS
        assert not no.canPerform(NEW_MANAGER_ADDRESS, MANAGE_SIGNING_KEYS, [perm_param_uint])
        # scenario test
        add_signing_keys_fails_before_vote(accounts)

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =====================================================================
        # ========================= After voting checks =======================
        # =====================================================================
        
        # Item 1
        assert no.canPerform(NEW_MANAGER_ADDRESS, MANAGE_SIGNING_KEYS, [perm_param_uint])

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        # events check
        permission = Permission(entity=NEW_MANAGER_ADDRESS, app=no, role=MANAGE_SIGNING_KEYS)
        validate_permission_grantp_event(vote_events[0], permission, [perm_param], emitted_by=ACL)

        # scenario tests
        manager_adds_signing_keys(accounts)
        add_signing_keys_to_notallowed_operator_fails(accounts)


def add_signing_keys_fails_before_vote(accounts):
    no = interface.SimpleDVT(TARGET_NO_REGISTRY)

    manager = accounts.at(NEW_MANAGER_ADDRESS, force=True)
    set_balance(manager, 10)

    pubkeys = random_pubkeys_batch(1)
    signatures = random_signatures_batch(1)

    with reverts():
        no.addSigningKeys(
            OPERATOR_ID,
            1,
            pubkeys,
            signatures,
            {"from": manager},
        )


def manager_adds_signing_keys(accounts):
    no = interface.SimpleDVT(TARGET_NO_REGISTRY)

    manager = accounts.at(NEW_MANAGER_ADDRESS, force=True)
    set_balance(manager, 10)

    total_keys_before = no.getTotalSigningKeyCount(OPERATOR_ID)
    pubkeys = random_pubkeys_batch(1)
    signatures = random_signatures_batch(1)

    no.addSigningKeys(
        OPERATOR_ID,
        1,
        pubkeys,
        signatures,
        {"from": manager},
    )

    total_keys_after = no.getTotalSigningKeyCount(OPERATOR_ID)
    assert total_keys_after == total_keys_before + 1


def add_signing_keys_to_notallowed_operator_fails(accounts):
    no = interface.SimpleDVT(TARGET_NO_REGISTRY)

    manager = accounts.at(NEW_MANAGER_ADDRESS, force=True)
    set_balance(manager, 10)

    pubkeys = random_pubkeys_batch(1)
    signatures = random_signatures_batch(1)

    with reverts():
        no.addSigningKeys(
            2, # NO id 2 - not allowed
            1,
            pubkeys,
            signatures,
            {"from": manager},
        )
