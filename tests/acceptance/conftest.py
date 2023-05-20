import pytest

from brownie import chain, ZERO_ADDRESS

from utils.config import contracts
from utils.test.oracle_report_helpers import ONE_DAY, SHARE_RATE_PRECISION, oracle_report
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes

from utils.test.extra_data import (
    ExtraDataService,
)


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts())
def autoexecute_vote(helpers, vote_ids_from_env, accounts):
    if vote_ids_from_env:
        helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting, topup="0.5 ether")
    else:
        start_and_execute_votes(contracts.voting, helpers)
