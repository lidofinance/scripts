import pytest
import os

from utils.config import contracts
from utils.import_current_votes import is_there_any_vote_scripts, is_there_any_upgrade_scripts, start_and_execute_votes

from utils.test.helpers import ETH
from utils.test.oracle_report_helpers import oracle_report
from utils.test.simple_dvt_helpers import fill_simple_dvt_ops_vetted_keys

ENV_REPORT_AFTER_VOTE = "REPORT_AFTER_VOTE"
ENV_FILL_SIMPLE_DVT = "FILL_SIMPLE_DVT"


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts() or is_there_any_upgrade_scripts())
def autoexecute_vote(helpers, vote_ids_from_env, accounts, stranger, module_isolation):
    if vote_ids_from_env:
        helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting)
    else:
        start_and_execute_votes(contracts.voting, helpers)
    if os.getenv(ENV_FILL_SIMPLE_DVT):
        print(f"Prefilling SimpleDVT...")
        fill_simple_dvt_ops_vetted_keys(stranger)

    if os.getenv(ENV_REPORT_AFTER_VOTE):
        oracle_report(cl_diff=ETH(523), exclude_vaults_balances=False)
