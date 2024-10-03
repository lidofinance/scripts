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


def test_negative_rebase_correct_exited_validators_count_pos_rebase(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    reported_validators = exited_validators_count()

    reported_validators_values = [value + 2 for value in reported_validators.values()]
    oracle_report(cl_diff=ETH(300), stakingModuleIdsWithNewlyExitedValidators=list(reported_validators.keys()),
                   numExitedValidatorsByStakingModule=reported_validators_values)

    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, storedExitedValidators, _) = oracle_report_sanity_checker.reportData(count - 1)

    assert storedExitedValidators == sum(reported_validators_values)

def test_negative_rebase_correct_exited_validators_count_neg_rebase(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    reported_validators = exited_validators_count()

    reported_validators_values = [value + 3 for value in reported_validators.values()]
    oracle_report(cl_diff=-ETH(40000), stakingModuleIdsWithNewlyExitedValidators=list(reported_validators.keys()),
                   numExitedValidatorsByStakingModule=reported_validators_values)

    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, storedExitedValidators, _) = oracle_report_sanity_checker.reportData(count - 1)

    assert storedExitedValidators == sum(reported_validators_values)

def test_negative_rebase_more_than_54_reports(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    reported_validators_values = exited_validators_count().values()
    for _ in range(58):
        reported_validators_values = [value + 3 for value in reported_validators_values]
        oracle_report(cl_diff=-ETH(400), stakingModuleIdsWithNewlyExitedValidators=exited_validators_count().keys(),
                       numExitedValidatorsByStakingModule=reported_validators_values)

    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, storedExitedValidators, _) = oracle_report_sanity_checker.reportData(count - 1)

    assert storedExitedValidators == sum(reported_validators_values)


def exited_validators_count():
    assert contracts.lido_locator.stakingRouter() == contracts.staking_router
    ids = contracts.staking_router.getStakingModuleIds()
    print(f'ids: {ids}')
    exited = {}
    for id in ids:
        exited[id] = contracts.staking_router.getStakingModule(id)["exitedValidatorsCount"]

    return exited
