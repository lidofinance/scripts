import pytest

from tests.conftest import without_balance_check_middleware
from utils.import_current_votes import is_there_any_upgrade_scripts


@pytest.fixture(scope="function", autouse=True)
def disable_balance_check_for_snapshot_tests():
    """Snapshot tests must retain the senders' real balances after each transaction."""
    with without_balance_check_middleware():
        yield


@pytest.fixture(scope="function", autouse=True)
def skip_if_there_no_upgrade_scripts():
    if not is_there_any_upgrade_scripts():
        pytest.skip("No upgrade scripts detected")
