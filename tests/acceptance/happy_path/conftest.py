import pytest
from utils.config import (
    contracts,
)

from utils.test.helpers import ETH


@pytest.fixture(scope="module")
def steth_holder(accounts):
    whale = "0x41318419CFa25396b47A94896FfA2C77c6434040"
    contracts.lido.transfer(accounts[0], ETH(101), {"from": whale})
    return accounts[0]
