import pytest

from utils.config import contracts
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts())
def autoexecute_vote(helpers, vote_ids_from_env, accounts):
    if vote_ids_from_env:
        helpers.execute_vote(
            vote_id=vote_ids_from_env, accounts=accounts, dao_voting=contracts.voting, topup="0.5 ether"
        )
    else:
        start_and_execute_votes(contracts.voting, helpers)
