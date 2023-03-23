
import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt

from utils.voting import confirm_vote_script, create_vote, bake_vote_items
from utils.permissions import encode_permission_grant, encode_permission_revoke
from utils.repo import (
    add_implementation_to_lido_app_repo,
    add_implementation_to_nos_app_repo,
)
from utils.kernel import update_app_implementation
from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    lido_dao_voting_address,
    ldo_vote_executors_for_tests
)

from brownie import chain, accounts, interface
from utils.evm_script import EMPTY_CALLSCRIPT


update_lido_app = {
    "id": "0x79ac01111b462384f1b7fba84a17b9ec1f5d2fddcfcb99487d71b443832556ea",
    "new_address": "0xf798159E0908FB988220eFbab94985De68F4FB55",
    "content_uri": "0x697066733a516d63354a64475a3576326844466d64516844535a70514a6554394a55364e34386d5678546474685667677a766d",
    "version": (10, 0, 0),
}

update_nor_app = {
    "id": "0x57384c8fcaf2c1c2144974769a6ea4e5cf69090d47f5327f8fc93827f8c0001a",
    "new_address": "0x1fE9E1015DBa106B4dc9d6B7C206aA66129b0a9f",
    "content_uri": "0x697066733a516d5342796b4e4a61363734547146334b7366677642666444315a545158794c4a6e707064776b36477463534c4d",
    "version": (8, 0, 0),
}


def execute_vote(accounts, vote_id, dao_voting, topup="0.1 ether", skip_time=3 * 60 * 60 * 24):
    OBJECTION_PHASE_ID = 1
    if dao_voting.canVote(vote_id, ldo_vote_executors_for_tests[0]) and (
        dao_voting.getVotePhase(vote_id) != OBJECTION_PHASE_ID
    ):
        for holder_addr in ldo_vote_executors_for_tests:
            print("voting from acct:", holder_addr)
            if accounts.at(holder_addr, force=True).balance() < topup:
                accounts[0].transfer(holder_addr, topup)
            account = accounts.at(holder_addr, force=True)
            dao_voting.vote(vote_id, True, False, {"from": account})

    # wait for the vote to end
    chain.sleep(skip_time)
    chain.mine()

    assert dao_voting.canExecute(vote_id)

    # try to instantiate script executor
    # to deal with events parsing properly
    # on fresh brownie setup cases (mostly for CI)
    executor_addr = dao_voting.getEVMScriptExecutor(EMPTY_CALLSCRIPT)
    try:
        _ = interface.CallsScript(executor_addr)
    except:
        print("Unable to instantiate CallsScript")
        print("Trying to proceed further as is...")

    tx = dao_voting.executeVote(vote_id, {"from": accounts[0]})

    print(f"vote #{vote_id} executed")
    return tx

def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting: interface.Voting = contracts.voting

    vote_items = bake_vote_items(
        vote_desc_items=[
            "1) Push new Lido app version to Lido Repo",
            "2) Upgrade the Lido contract implementation",
            "3) Push new NOR app version to Lido Repo",
            "4) Upgrade the NOR contract implementation",
        ],
        call_script_items=[
            # 1. Push new Lido app version to Lido Repo 0xF5Dc67E54FC96F993CD06073f71ca732C1E654B1
            add_implementation_to_lido_app_repo(
                update_lido_app["version"],
                update_lido_app["new_address"],
                update_lido_app["content_uri"],
            ),
            # 2. Upgrade the Lido contract implementation 0xf798159E0908FB988220eFbab94985De68F4FB55.
            update_app_implementation(update_lido_app["id"], update_lido_app["new_address"]),
            # 3. Push new NOR app version to NOR Repo 0x5F867429616b380f1Ca7a7283Ff18C53a0033073
            add_implementation_to_nos_app_repo(
                update_nor_app["version"],
                update_nor_app["new_address"],
                update_nor_app["content_uri"],
            ),
            # 4. Upgrade the NOR contract implementation 0x1fE9E1015DBa106B4dc9d6B7C206aA66129b0a9f.
            update_app_implementation(update_nor_app["id"], update_nor_app["new_address"]),
        ],
    )

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = "2 gwei"

    vote_id, _ = start_vote(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    dao_voting = interface.Voting(lido_dao_voting_address)
    tx: TransactionReceipt = execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    time.sleep(5)  # hack for waiting thread #2.
