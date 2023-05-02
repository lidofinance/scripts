import pytest

from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting


@pytest.fixture(scope="module")
def shapella_upgrade_template():
    upgrade_template = prepare_for_shapella_upgrade_voting(silent=True)
    return upgrade_template
