import pytest
from brownie import Contract, web3, reverts, accounts, chain  # type: ignore
from utils.evm_script import encode_error
from utils.test.exit_bus_data import LidoValidator
from utils.test.extra_data import ExtraDataService
from utils.test.oracle_report_helpers import (
    oracle_report,
)

from utils.test.helpers import ETH
from utils.config import (
    contracts,
)

INITIAL_SLASHING_AMOUNT_PWEI = 1000
INACTIVITY_PENALTIES_AMOUNT_PWEI = 101
ONE_PWEI = ETH(0.001)


@pytest.fixture(scope="module")
def oracle_report_sanity_checker() -> Contract:
    return contracts.oracle_report_sanity_checker


def test_negative_rebase_correct_exited_validators_count_pos_rebase(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    reported_validators = exited_validators_count()

    reported_validators_values = [value + 2 for value in reported_validators.values()]
    oracle_report(
        cl_diff=ETH(300),
        stakingModuleIdsWithNewlyExitedValidators=list(reported_validators.keys()),
        numExitedValidatorsByStakingModule=reported_validators_values,
    )

    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, stored_exited_validators, _) = oracle_report_sanity_checker.reportData(count - 1)

    assert stored_exited_validators == sum(reported_validators_values)


def test_negative_rebase_correct_exited_validators_count_neg_rebase(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    reported_validators = exited_validators_count()

    reported_validators_values = [value + 3 for value in reported_validators.values()]
    oracle_report(
        cl_diff=-ETH(40000),
        stakingModuleIdsWithNewlyExitedValidators=list(reported_validators.keys()),
        numExitedValidatorsByStakingModule=reported_validators_values,
    )

    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, stored_exited_validators, _) = oracle_report_sanity_checker.reportData(count - 1)

    assert stored_exited_validators == sum(reported_validators_values)


def test_negative_rebase_correct_balance_neg_rebase(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    cl_decrease = ETH(40000)
    oracle_report(cl_diff=-cl_decrease, exclude_vaults_balances=True)

    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, _, cl_balance) = oracle_report_sanity_checker.reportData(count - 1)
    assert cl_balance == cl_decrease

    cl_decrease2 = ETH(30000)
    oracle_report(cl_diff=-cl_decrease2, exclude_vaults_balances=True)
    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, _, cl_balance) = oracle_report_sanity_checker.reportData(count - 1)

    assert cl_balance == cl_decrease2


def test_blocked_huge_negative_rebase(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    # Advance the chain 60 days more without accounting oracle reports
    # The idea is to simplify the calculation of the exited validators for 18 and 54 days ago
    chain.sleep(60 * 24 * 60 * 60)
    chain.mine(1)

    (_, cl_validators, cl_balance) = contracts.lido.getBeaconStat()
    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, stored_exited_validators, _) = oracle_report_sanity_checker.reportData(count - 1)

    max_cl_balance = (
        (INITIAL_SLASHING_AMOUNT_PWEI + INACTIVITY_PENALTIES_AMOUNT_PWEI)
        * ONE_PWEI
        * (cl_validators - stored_exited_validators)
    )
    error_cl_decrease = cl_balance // 10  # 10% of current balance will lead to error

    print(encode_error("IncorrectCLBalanceDecrease(uint256, uint256)", [error_cl_decrease, max_cl_balance]))
    with reverts(encode_error("IncorrectCLBalanceDecrease(uint256, uint256)", [error_cl_decrease, max_cl_balance])):
        oracle_report(
            cl_diff=-error_cl_decrease,
            exclude_vaults_balances=True,
            simulation_block_identifier=chain.height,
            silent=True,
        )


def test_negative_rebase_more_than_54_reports(oracle_report_sanity_checker):
    locator = contracts.lido_locator
    assert oracle_report_sanity_checker.address == locator.oracleReportSanityChecker()

    reported_validators_values = exited_validators_count().values()
    for _ in range(58):
        reported_validators_values = [value + 3 for value in reported_validators_values]
        oracle_report(
            cl_diff=-ETH(400),
            stakingModuleIdsWithNewlyExitedValidators=exited_validators_count().keys(),
            numExitedValidatorsByStakingModule=reported_validators_values,
        )

    count = oracle_report_sanity_checker.getReportDataCount()
    assert count > 0
    (_, stored_exited_validators, _) = oracle_report_sanity_checker.reportData(count - 1)

    assert stored_exited_validators == sum(reported_validators_values)


def exited_validators_count():
    assert contracts.lido_locator.stakingRouter() == contracts.staking_router
    ids = contracts.staking_router.getStakingModuleIds()
    exited = {}
    for id in ids:
        exited_validators = contracts.staking_router.getStakingModule(id)["exitedValidatorsCount"]
        # It's possible to report only non-zero values for exited validators
        if exited_validators > 0:
            exited[id] = exited_validators

    return exited
