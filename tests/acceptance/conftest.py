import pytest

from utils.import_current_votes import is_there_any_vote_scripts, is_there_any_upgrade_scripts
from utils.test.governance_helpers import execute_vote_and_process_dg_proposals


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts() or is_there_any_upgrade_scripts())
def autoexecute_vote(request, module_isolation, helpers, vote_ids_from_env, proposal_ids_from_env, stranger):
    execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, proposal_ids_from_env, stranger)
