import pytest
from brownie import interface  # type: ignore

from utils.config import contracts, lido_dao_oracle_report_sanity_checker

report_limits = {
    "churnValidatorsPerDayLimit": 12375,
    "oneOffCLBalanceDecreaseBPLimit": 500,
    "annualBalanceIncreaseBPLimit": 1000,
    "simulatedShareRateDeviationBPLimit": 10,
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

    limits = contract.getOracleReportLimits()

    assert limits["churnValidatorsPerDayLimit"] == report_limits["churnValidatorsPerDayLimit"]
    assert limits["oneOffCLBalanceDecreaseBPLimit"] == report_limits["oneOffCLBalanceDecreaseBPLimit"]
    assert limits["annualBalanceIncreaseBPLimit"] == report_limits["annualBalanceIncreaseBPLimit"]
    assert limits["simulatedShareRateDeviationBPLimit"] == report_limits["simulatedShareRateDeviationBPLimit"]
    assert limits["maxValidatorExitRequestsPerReport"] == report_limits["maxValidatorExitRequestsPerReport"]
    assert limits["maxAccountingExtraDataListItemsCount"] == report_limits["maxAccountingExtraDataListItemsCount"]
    assert limits["maxNodeOperatorsPerExtraDataItemCount"] == report_limits["maxNodeOperatorsPerExtraDataItemCount"]
    assert limits["requestTimestampMargin"] == report_limits["requestTimestampMargin"]
    assert limits["maxPositiveTokenRebase"] == report_limits["maxPositiveTokenRebase"]
