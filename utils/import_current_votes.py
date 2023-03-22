from typing import List
import os
import glob

from brownie import accounts
from brownie.network.transaction import TransactionReceipt

from utils.config import ldo_holder_address_for_tests, ContractsLazyLoader, deployer_eoa
from utils.shapella_upgrade import prepare_for_voting


def get_vote_script_files() -> List[str]:
    """Return List of abs paths to vote scripts"""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.join(os.path.split(dir_path)[0], "scripts")
    vote_files = glob.glob(os.path.join(dir_path, "upgrade_*.py"))
    return vote_files


def is_there_any_vote_scripts() -> bool:
    return len(get_vote_script_files()) > 0


def start_and_execute_votes(dao_voting, helpers) -> tuple[List[str], List[TransactionReceipt]]:
    vote_files = get_vote_script_files()
    assert len(vote_files) > 0

    ContractsLazyLoader.upgrade_template = prepare_for_voting(deployer_eoa)

    vote_ids = []
    vote_transactions = []
    for vote_file in sorted(vote_files):
        script_name = os.path.splitext(os.path.basename(vote_file))[0]
        print(f"Starting voting from script '{script_name}'...")
        name_for_import = "scripts." + script_name
        start_vote_name = f"start_vote_{script_name}"
        exec(f"from {name_for_import} import start_vote as {start_vote_name}")
        start_vote = locals()[start_vote_name]

        vote_id, _ = start_vote({"from": ldo_holder_address_for_tests}, silent=True)
        tx = helpers.execute_vote(
            vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether", skip_time=3 * 60 * 60 * 24
        )
        vote_ids.append(vote_id)
        vote_transactions.append(tx)
    return vote_ids, vote_transactions
