import math
from scripts.vote_2022_10_04 import start_vote
from utils.test.event_validators.lido import validate_set_protocol_contracts, validate_transfer_shares
from utils.test.event_validators.permission import Permission, validate_permission_revoke_event
from utils.test.tx_tracing_helpers import *


INSURANCE_FUND_ADDRESS = "0x8B3f33234ABD88493c0Cd28De33D583B70beDe35"
INSURANCE_SHARES = 5466.46 * 10**18
LDO_PURCHASE_EXECUTOR = "0xA9b2F5ce3aAE7374a62313473a74C98baa7fa70E"


permission = Permission(
    entity=LDO_PURCHASE_EXECUTOR,
    app="0xf73a1260d222f447210581DDf212D915c09a3249",  # dao token manager,
    role="0xf5a08927c847d7a29dc35e105208dbde5ce951392105d712761cc5d17440e2ff",  # ASSIGN_ROLE
)


def test_vote(
    helpers,
    accounts,
    dao_agent,
    ldo_holder,
    dao_voting,
    acl,
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
    assert acl.hasPermission(permission.entity, permission.app, permission.role)

    # start vote
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    # enact vote
    tx: TransactionReceipt = helpers.execute_vote(accounts=accounts, vote_id=vote_id, dao_voting=dao_voting)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 3, "Incorrect voting items count"

    assert lido.getInsuranceFund() == INSURANCE_FUND_ADDRESS
    assert lido.sharesOf(INSURANCE_FUND_ADDRESS) == INSURANCE_SHARES
    assert not acl.hasPermission(permission.entity, permission.app, permission.role)

    # Check events if their decoding is available
    if bypass_events_decoding:
        return

    display_voting_events(tx)

    evs = group_voting_events(tx)
    validate_set_protocol_contracts(evs[0], lido.getOracle(), lido.getTreasury(), INSURANCE_FUND_ADDRESS)
    validate_transfer_shares(evs[1], dao_agent.address, INSURANCE_FUND_ADDRESS, INSURANCE_SHARES)
    validate_permission_revoke_event(evs[2], permission)

# due to integer division, steth may lose 1-2 units in transfer
# may change in future :X
STETH_ERROR_MARGIN = 2


def test_recover_steth_from_insurance_fund_as_agent(helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, insurance_fund, lido):
    # enact vote
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(accounts=accounts, vote_id=vote_id, dao_voting=dao_voting)

    # take over dao agent
    agent_account = accounts.at(insurance_fund.owner(), True)

    prev_insurance_fund_balance = lido.balanceOf(insurance_fund.address)
    prev_agent_balance = lido.balanceOf(agent_account.address)

    recover_amount = prev_insurance_fund_balance

    tx: TransactionReceipt = insurance_fund.transferERC20(
        lido.address, agent_account.address, recover_amount, {"from": agent_account}
    )


    assert math.isclose(
        lido.balanceOf(agent_account.address), prev_agent_balance + recover_amount, abs_tol=STETH_ERROR_MARGIN
    )

    assert math.isclose(
        lido.balanceOf(insurance_fund.address), prev_insurance_fund_balance - recover_amount, abs_tol=STETH_ERROR_MARGIN
    )

    display_voting_events(tx)

    assert "ERC20Transferred" in tx.events
    assert tx.events["ERC20Transferred"]["_token"] == lido.address
    assert tx.events["ERC20Transferred"]["_recipient"] == agent_account.address
    assert tx.events["ERC20Transferred"]["_amount"] == recover_amount