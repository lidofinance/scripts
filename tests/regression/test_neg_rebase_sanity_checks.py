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

    ids = contracts.staking_router.getStakingModuleIds()
    exited = 0
    for id in ids:
        exited += contracts.staking_router.getStakingModule(id)["exitedValidatorsCount"]

    reported_validators_count = exited + 2
    print(f'reported_validators_count: {reported_validators_count}')

    oracle_report(cl_diff=-ETH(40000), stakingModuleIdsWithNewlyExitedValidators=[1],
                   numExitedValidatorsByStakingModule=[reported_validators_count])

    count = oracle_report_sanity_checker.getReportDataCount()
    print(f'count: {count}')
    assert count > 0
    (_, storedExitedValidators, _) = oracle_report_sanity_checker.reportData(count - 1)

    assert storedExitedValidators == reported_validators_count
