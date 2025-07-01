import pytest
from utils.import_current_votes import is_there_any_vote_scripts, is_there_any_upgrade_scripts
from utils.test.extra_data import ExtraDataService

from utils.test.governance_helpers import execute_vote_and_process_dg_proposals
from utils.dual_governance import is_there_any_proposals_from_env, process_pending_proposals


@pytest.fixture(scope="module", autouse=not is_there_any_proposals_from_env())
def autoexecute_dg_proposals():
    process_pending_proposals()


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts() or is_there_any_upgrade_scripts() or is_there_any_proposals_from_env())
def autoexecute_vote(module_isolation, helpers, vote_ids_from_env, dg_proposal_ids_from_env):
    execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, dg_proposal_ids_from_env)


@pytest.fixture()
def extra_data_service() -> ExtraDataService:
    return ExtraDataService()
