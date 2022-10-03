from scripts.vote_2022_10_04 import start_vote
from utils.test.tx_tracing_helpers import *


INSURANCE_FUND_ADDRESS = "0x8B3f33234ABD88493c0Cd28De33D583B70beDe35"
INSURANCE_SHARES = 5466.46 * 10**18
LDO_PURCHASE_EXECUTOR = "0xA9b2F5ce3aAE7374a62313473a74C98baa7fa70E"


def test_vote(
    helpers,
    accounts,
    dao_agent,
    ldo_holder,
    dao_voting,
    acl,
    dao_token_manager,
    vote_id_from_env,
    bypass_events_decoding,
    lido,
):
    # test assumed initial state

    # insurance is the same as treasury
    assert lido.getInsuranceFund() == lido.getTreasury()
    # agent has sufficient shares
    assert lido.sharesOf(dao_agent.address) >= INSURANCE_SHARES
    # insurance fund has no shares
    assert lido.sharesOf(INSURANCE_FUND_ADDRESS) == 0
    # ldo purchase executor has ASSIGN ROLE
    assert acl.hasPermission(LDO_PURCHASE_EXECUTOR, dao_token_manager, dao_token_manager.ASSIGN_ROLE())

    # start vote
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    # enact vote
    tx: TransactionReceipt = helpers.execute_vote(accounts=accounts, vote_id=vote_id, dao_voting=dao_voting)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 3, "Incorrect voting items count"

    assert lido.getInsuranceFund() == INSURANCE_FUND_ADDRESS
    assert lido.sharesOf(INSURANCE_FUND_ADDRESS) == INSURANCE_SHARES
    assert not acl.hasPermission(LDO_PURCHASE_EXECUTOR, dao_token_manager, dao_token_manager.ASSIGN_ROLE())
