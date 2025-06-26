from brownie import chain, interface
from scripts.<vote_2025_MM_DD> import start_vote
from brownie.network.transaction import TransactionReceipt
from utils.test.tx_tracing_helpers import *

<list all contract addresses used in tests>
DUAL_GOVERNANCE = "0xcdF49b058D606AD34c5789FD8c3BF8B3E54bA2db"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"

def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):

    <arrange all variables neccessary for the test>
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    vote_events_count = <# of events emitted by the vote>
    dg_prposal_id = <order # of a dg proposal>

    <run asserts that checks the "before" vote state>

    # START VOTE
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]
    vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)

    <run asserts that checks the "after" vote state>

    chain.sleep(timelock.getAfterSubmitDelay() + 1)
    dual_governance.scheduleProposal(dg_prposal_id, {"from": stranger})
    chain.sleep(timelock.getAfterScheduleDelay() + 1)
    dg_tx: TransactionReceipt = timelock.execute(dg_prposal_id, {"from": stranger})

    <run asserts that checks the "after" DG proposals execution state>

    <run acceptance/happy path tests>

    evs = group_voting_events_from_receipt(vote_tx)
    assert len(evs) == vote_events_count

    metadata = find_metadata_by_vote_id(vote_id)
    assert get_lido_vote_cid_from_str(metadata) == "<expected_ipfs_hash>"

    assert count_vote_items_by_events(vote_tx, voting) == vote_events_count, "Incorrect voting items count"

    <validate all events emitted during the vote>

    dg_evs = group_dg_events_from_receipt(dg_tx, timelock=EMERGENCY_PROTECTED_TIMELOCK, admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR)
    <validate all events emitted during the DG execution>
