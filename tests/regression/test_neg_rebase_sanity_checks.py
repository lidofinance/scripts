import pytest
from brownie import Contract, web3, reverts, accounts, chain  # type: ignore
from utils.test.exit_bus_data import LidoValidator
from utils.test.extra_data import ExtraDataService
from utils.test.oracle_report_helpers import (
    oracle_report,
)

from utils.test.helpers import ETH
from utils.config import (
    contracts,
)

@pytest.fixture(scope="module")
def oracle_report_sanity_checker() -> Contract:
    return contracts.oracle_report_sanity_checker


def test_negative_rebase_correct_exited_validators_count(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    reported_validators_count = exited_validators_count() + 2
    print(f'reported_validators_count: {reported_validators_count}')

    oracle_report(cl_diff=-ETH(40000), stakingModuleIdsWithNewlyExitedValidators=[1],
                   numExitedValidatorsByStakingModule=[reported_validators_count])

    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, storedExitedValidators, _) = oracle_report_sanity_checker.reportData(count - 1)

    assert storedExitedValidators == reported_validators_count

def test_negative_rebase_more_than_54_reports(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    reported_validators_count = exited_validators_count() + 2
    print(f'reported_validators_count: {reported_validators_count}')

    for _ in range(58):
        reported_validators_count += 3
        oracle_report(cl_diff=-ETH(400), stakingModuleIdsWithNewlyExitedValidators=[1],
                       numExitedValidatorsByStakingModule=[reported_validators_count])

    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, storedExitedValidators, _) = oracle_report_sanity_checker.reportData(count - 1)

    assert storedExitedValidators == reported_validators_count


def exited_validators_count():
    ids = contracts.staking_router.getStakingModuleIds()
    exited = 0
    for id in ids:
        exited += contracts.staking_router.getStakingModule(id)["exitedValidatorsCount"]

    return exited
