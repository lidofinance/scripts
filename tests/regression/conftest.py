import pytest

from utils.config import contracts
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes
from utils.test.helpers import ETH


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts())
def autoexecute_vote(helpers, vote_ids_from_env, accounts):
    if vote_ids_from_env:
        helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting, topup="0.5 ether")
    else:
        start_and_execute_votes(contracts.voting, helpers)


@pytest.fixture()
def steth_holder(accounts):
    whale = "0x176F3DAb24a159341c0509bB36B833E7fdd0a132"
    contracts.lido.transfer(accounts[0], ETH(101), {"from": whale})
    return accounts[0]
