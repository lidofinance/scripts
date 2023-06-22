import pytest

from utils.import_current_votes import is_there_any_upgrade_scripts

@pytest.fixture(scope="function", autouse=True)
def skip_if_there_no_upgrade_scripts():
    if not is_there_any_upgrade_scripts():
        pytest.skip("No upgrade scripts detected")
