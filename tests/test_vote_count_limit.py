from brownie import accounts, interface
from brownie.network.transaction import TransactionReceipt
from utils.test.tx_tracing_helpers import *
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.config import (
    get_deployer_account,
)

vote_item_count = 14


def generate_and_start_vote():
    reward_programs_registry = interface.RewardProgramsRegistry(
        "0xfCaD241D9D2A2766979A2de208E8210eDf7b7D4F"
    )
    call_script_items = []
    vote_desc_items = []

    for index in range(vote_item_count):
        call_script_items.append(
            add_evmscript_factory(
                factory=accounts[index].address,
                permissions=create_permissions(
                    reward_programs_registry,
                    "addRewardProgram" if ((index % 2) == 0) else "removeRewardProgram",
                ),
            )
        )
        vote_desc_items.append(index)

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, True) and create_vote(
        vote_items, {"from": get_deployer_account()}
    )


def test_vote_count_limit(dao_voting, helpers, bypass_events_decoding):
    (vote_id, _) = generate_and_start_vote()

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    if not bypass_events_decoding:
        assert (
            count_vote_items_by_events(tx, dao_voting) == vote_item_count
        ), "Incorrect voting items count"

    pass
