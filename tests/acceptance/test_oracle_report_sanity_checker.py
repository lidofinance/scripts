import pytest
from brownie import interface  # type: ignore

from utils.config import (
    contracts,
    ORACLE_REPORT_SANITY_CHECKER,
    EXITED_VALIDATORS_PER_DAY_LIMIT,
    APPEARED_VALIDATORS_PER_DAY_LIMIT,
    ANNUAL_BALANCE_INCREASE_BP_LIMIT,
    SIMULATED_SHARE_RATE_DEVIATION_BP_LIMIT,
    MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT,
    MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT,
    MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT,
    REQUEST_TIMESTAMP_MARGIN,
    MAX_POSITIVE_TOKEN_REBASE,
    INITIAL_SLASHING_AMOUNT_PWEI,
    INACTIVITY_PENALTIES_AMOUNT_PWEI,
    CL_BALANCE_ORACLES_ERROR_UPPER_BP_LIMIT
)

# Source of truth: https://hackmd.io/pdix1r4yR46fXUqiHaNKyw?view
expected_report_limits = {
    "exitedValidatorsPerDayLimit": EXITED_VALIDATORS_PER_DAY_LIMIT,
    "appearedValidatorsPerDayLimit": APPEARED_VALIDATORS_PER_DAY_LIMIT,
    "annualBalanceIncreaseBPLimit": ANNUAL_BALANCE_INCREASE_BP_LIMIT,
    "simulatedShareRateDeviationBPLimit": SIMULATED_SHARE_RATE_DEVIATION_BP_LIMIT,
    "maxValidatorExitRequestsPerReport": MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT,
    "maxAccountingExtraDataListItemsCount": MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT,
    "maxNodeOperatorsPerExtraDataItemCount": MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT,
    "requestTimestampMargin": REQUEST_TIMESTAMP_MARGIN,
    "maxPositiveTokenRebase": MAX_POSITIVE_TOKEN_REBASE,
    "initialSlashingAmountPWei": INITIAL_SLASHING_AMOUNT_PWEI,
    "inactivityPenaltiesAmountPWei": INACTIVITY_PENALTIES_AMOUNT_PWEI,
    "clBalanceOraclesErrorUpperBPLimit": CL_BALANCE_ORACLES_ERROR_UPPER_BP_LIMIT,
}


@pytest.fixture(scope="module")
def contract() -> interface.OracleReportSanityChecker:
    return interface.OracleReportSanityChecker(ORACLE_REPORT_SANITY_CHECKER)


def test_links(contract):
    assert contract.getLidoLocator() == contracts.lido_locator


def test_limits(contract):
    assert contract.getMaxPositiveTokenRebase() == expected_report_limits["maxPositiveTokenRebase"]
    limits =  contract.getOracleReportLimits()

    assert dict(zip(expected_report_limits.keys(), limits)) == expected_report_limits
