import pytest
from brownie import interface, chain  # type: ignore

from utils.config import (
    contracts,
    lido_dao_legacy_oracle,
)

implementation = "0x599E51510719e94525eF406d4519949eca4242ac"
app_id = "0x8b47ba2a8454ec799cd91646e7ec47168e91fd139b23f017455f3e5898aaba93"
lastSeenTotalPooledEther = 5879742251110033487920093

beacon_spec = {
    "slotsPerEpoch": 32,
    "secondsPerSlot": 12,
    "genesisTime": 1606824023,
}


@pytest.fixture(scope="module")
def contract() -> interface.LegacyOracle:
    return interface.LegacyOracle(lido_dao_legacy_oracle)


def test_links(contract):
    assert contract.getLido() == contracts.lido
    assert contract.getAccountingOracle() == contracts.accounting_oracle
    assert contract.getEVMScriptRegistry() == "0x853cc0D5917f49B57B8e9F89e491F5E18919093A"


def test_aragon(contract):
    proxy = interface.AppProxyUpgradeable(contract)
    assert proxy.implementation() == implementation
    assert contract.kernel() == contracts.kernel
    assert contract.appId() == app_id
    assert contract.hasInitialized() == True
    assert contract.isPetrified() == False


def test_versioned(contract):
    assert contract.getContractVersion() == 4


def test_recoverability(contract):
    assert contract.getRecoveryVault() == contracts.agent
    assert contract.allowRecoverability(contracts.ldo_token) == True


def test_legacy_oracle_state(contract):
    reported_delta = contract.getLastCompletedReportDelta()
    assert reported_delta["postTotalPooledEther"] > lastSeenTotalPooledEther
    assert reported_delta["preTotalPooledEther"] >= lastSeenTotalPooledEther
    assert reported_delta["timeElapsed"] == 86400

    current_frame = contract.getCurrentFrame()
    assert current_frame["frameEpochId"] > 0
    assert current_frame["frameStartTime"] > 0
    assert current_frame["frameEndTime"] > 0

    assert contract.getLastCompletedEpochId() > 0

    assert contract.getInitializationBlock() > 0
    assert contract.getInitializationBlock() <= chain.height

    oracle_beacon_spec = contracts.legacy_oracle.getBeaconSpec()

    assert oracle_beacon_spec["epochsPerFrame"] == 225
    assert oracle_beacon_spec["slotsPerEpoch"] == beacon_spec["slotsPerEpoch"]
    assert oracle_beacon_spec["secondsPerSlot"] == beacon_spec["secondsPerSlot"]
    assert oracle_beacon_spec["genesisTime"] == beacon_spec["genesisTime"]
