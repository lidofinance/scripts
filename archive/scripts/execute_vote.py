"""
This script is used to execute vote in united CI if there is any vote or upgrade scripts.
"""

import os

from brownie import accounts

from tests.conftest import Helpers, ENV_OMNIBUS_VOTE_IDS
from utils.import_current_votes import is_there_any_vote_scripts, is_there_any_upgrade_scripts, start_and_execute_votes
from utils.config import contracts


def main():
    has_vote_scripts = is_there_any_vote_scripts()
    has_upgrade_scripts = is_there_any_upgrade_scripts()

    if not has_vote_scripts and not has_upgrade_scripts:
        print("No vote scripts or upgrade scripts found.")
        return

    helpers = Helpers()
    vote_ids_str = os.getenv(ENV_OMNIBUS_VOTE_IDS)
    vote_ids = [int(s) for s in vote_ids_str.split(",")] if vote_ids_str else []
    print(f"OMNIBUS_VOTE_IDS env var is set, using existing votes {vote_ids}")

    if vote_ids:
        helpers.execute_votes(accounts, vote_ids, contracts.voting, topup="0.5 ether")
    else:
        start_and_execute_votes(contracts.voting, helpers)
