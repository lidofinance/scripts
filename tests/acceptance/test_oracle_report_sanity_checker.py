import pytest
from brownie import interface  # type: ignore

from utils.config import contracts, lido_dao_oracle_report_sanity_checker

# Source of truth: https://hackmd.io/pdix1r4yR46fXUqiHaNKyw?view
report_limits = {
    "churnValidatorsPerDayLimit": 40000,
    "oneOffCLBalanceDecreaseBPLimit": 500,
    "annualBalanceIncreaseBPLimit": 1000,
    "simulatedShareRateDeviationBPLimit": 50,
    "maxValidatorExitRequestsPerReport": 500,
    "maxAccountingExtraDataListItemsCount": 500,
    "maxNodeOperatorsPerExtraDataItemCount": 100,
    "requestTimestampMargin": 7680,
    "maxPositiveTokenRebase": 750000,
}


@pytest.fixture(scope="module")
def contract() -> interface.OracleReportSanityChecker:
    return interface.OracleReportSanityChecker(lido_dao_oracle_report_sanity_checker)


def test_links(contract):
    assert contract.getLidoLocator() == contracts.lido_locator


def test_limits(contract):
    assert contract.getMaxPositiveTokenRebase() == report_limits["maxPositiveTokenRebase"]

    assert dict(zip(report_limits.keys(), contract.getOracleReportLimits())) == report_limits
