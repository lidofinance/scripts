from typing import List
import os
import glob

from brownie import accounts
from brownie.network.transaction import TransactionReceipt

from utils.config import (
    ldo_holder_address_for_tests,
    ContractsLazyLoader,
    deployer_eoa,
    shapella_upgrade_template,
    get_is_live,
)
from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting


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

    if os.getenv("SKIP_SHAPELLA_PRELIMINARY_STEP"):
        assert (
            shapella_upgrade_template != ""
        ), "If SKIP_SHAPELLA_PRELIMINARY_STEP is set 'shapella_upgrade_template' must be specified in the config"
        ContractsLazyLoader.upgrade_template = shapella_upgrade_template
    else:
        assert (
            not get_is_live(),
            "ERROR: will not do preliminary actions on live network. run `preliminary_shapella...py` script manually",
        )
        ContractsLazyLoader.upgrade_template = prepare_for_shapella_upgrade_voting(deployer_eoa, silent=True)

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
        (tx,) = helpers.execute_votes_sequential(accounts, [vote_id], dao_voting, topup="0.5 ether")
        vote_ids.append(vote_id)
        vote_transactions.append(tx)
    return vote_ids, vote_transactions
