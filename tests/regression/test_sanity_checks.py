import pytest
from brownie import web3, reverts, accounts  # type: ignore
from utils.test.oracle_report_helpers import oracle_report, wait_to_next_available_report_time
from utils.evm_script import encode_error

from utils.test.helpers import ETH, eth_balance
from utils.config import (
    contracts,
    CHURN_VALIDATORS_PER_DAY_LIMIT,
    ONE_OFF_CL_BALANCE_DECREASE_BP_LIMIT,
    ANNUAL_BALANCE_INCREASE_BP_LIMIT,
    SIMULATED_SHARE_RATE_DEVIATION_BP_LIMIT,
    MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT,
    MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT,
    MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT,
    REQUEST_TIMESTAMP_MARGIN,
    MAX_POSITIVE_TOKEN_REBASE,
)

ONE_DAY = 1 * 24 * 60 * 60
ONE_YEAR = 365 * ONE_DAY
MAX_BASIS_POINTS = 10000


@pytest.fixture(scope="module")
def eth_whale(accounts):
    return accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)


@pytest.fixture(scope="module")
def pre_cl_balance():
    (_, _, pre_cl_balance) = contracts.lido.getBeaconStat()
    return pre_cl_balance


@pytest.fixture(scope="module", autouse=True)
def first_report():
    oracle_report(silent=True)


def test_cant_report_more_validators_than_deposited():
    with reverts("REPORTED_MORE_DEPOSITED"):
        oracle_report(cl_diff=ETH(100), cl_appeared_validators=1000, skip_withdrawals=True, silent=True)


def test_validators_cant_decrease():
    with reverts("REPORTED_LESS_VALIDATORS"):
        oracle_report(cl_diff=ETH(100), cl_appeared_validators=-1, skip_withdrawals=True, silent=True)


def test_too_large_cl_increase(pre_cl_balance):
    #   uint256 annualBalanceIncrease = ((365 days * MAX_BASIS_POINTS * balanceIncrease) /
    #         _preCLBalance) /
    #         _timeElapsed;
    max_balance_increase = ANNUAL_BALANCE_INCREASE_BP_LIMIT * ONE_DAY * pre_cl_balance // ONE_YEAR // MAX_BASIS_POINTS

    error_balance_increase = max_balance_increase + ETH(100)
    error_annual_balance_increase = (ONE_YEAR * MAX_BASIS_POINTS * error_balance_increase) // pre_cl_balance // ONE_DAY
    with reverts(encode_error("IncorrectCLBalanceIncrease(uint256)", [error_annual_balance_increase])):
        oracle_report(cl_diff=error_balance_increase, skip_withdrawals=True, silent=True)


def test_too_large_cl_increase_with_appeared_validator(pre_cl_balance):
    max_balance_increase = ANNUAL_BALANCE_INCREASE_BP_LIMIT * ONE_DAY * pre_cl_balance // ONE_YEAR // MAX_BASIS_POINTS
    error_balance_increase = max_balance_increase + ETH(100)
    error_annual_balance_increase = (ONE_YEAR * MAX_BASIS_POINTS * error_balance_increase) // pre_cl_balance // ONE_DAY

    with_appeared_validator = error_balance_increase + ETH(32)
    fake_deposited_validators_increase(1)

    with reverts(encode_error("IncorrectCLBalanceIncrease(uint256)", [error_annual_balance_increase])):
        oracle_report(cl_diff=with_appeared_validator, cl_appeared_validators=1, skip_withdrawals=True, silent=True)


def test_too_much_validators_appeared():
    deposited_validators = CHURN_VALIDATORS_PER_DAY_LIMIT + 1
    fake_deposited_validators_increase(deposited_validators)

    with reverts(encode_error("IncorrectAppearedValidators(uint256)", [deposited_validators])):
        oracle_report(
            cl_diff=ETH(32) * deposited_validators,
            cl_appeared_validators=deposited_validators,
            skip_withdrawals=True,
            silent=True,
        )


def test_too_much_validators_exited():
    with reverts(
        encode_error(
            "ExitedValidatorsLimitExceeded(uint256,uint256)",
            [CHURN_VALIDATORS_PER_DAY_LIMIT, CHURN_VALIDATORS_PER_DAY_LIMIT + 1],
        )
    ):
        oracle_report(
            numExitedValidatorsByStakingModule=[CHURN_VALIDATORS_PER_DAY_LIMIT + 1],
            stakingModuleIdsWithNewlyExitedValidators=[1],
            skip_withdrawals=True,
            silent=True,
        )


def test_too_large_cl_decrease(pre_cl_balance):
    #  uint256 oneOffCLBalanceDecreaseBP = (MAX_BASIS_POINTS * (_preCLBalance - _unifiedPostCLBalance)) /
    #         _preCLBalance;

    withdrawal_vault_balance = eth_balance(contracts.withdrawal_vault.address)
    max_cl_decrease = (
        ONE_OFF_CL_BALANCE_DECREASE_BP_LIMIT * pre_cl_balance // MAX_BASIS_POINTS + withdrawal_vault_balance
    )

    error_cl_decrease = max_cl_decrease + ETH(1000)
    error_one_off_cl_decrease_bp = (MAX_BASIS_POINTS * (error_cl_decrease - withdrawal_vault_balance)) // pre_cl_balance
    with reverts(encode_error("IncorrectCLBalanceDecrease(uint256)", [error_one_off_cl_decrease_bp])):
        oracle_report(cl_diff=-error_cl_decrease, skip_withdrawals=True, silent=True)


def test_withdrawal_vault_report_more():
    withdrawal_vault_balance = eth_balance(contracts.withdrawal_vault.address)
    with reverts(encode_error("IncorrectWithdrawalsVaultBalance(uint256)", [withdrawal_vault_balance])):
        oracle_report(withdrawalVaultBalance=withdrawal_vault_balance + 1, skip_withdrawals=True, silent=True)


def test_el_vault_report_more():
    el_vault_balance = eth_balance(contracts.execution_layer_rewards_vault.address)
    with reverts(encode_error("IncorrectELRewardsVaultBalance(uint256)", [el_vault_balance])):
        oracle_report(elRewardsVaultBalance=el_vault_balance + 1, skip_withdrawals=True, silent=True)


def test_shares_on_burner_report_more():
    (cover_shares, non_cover_shares) = contracts.burner.getSharesRequestedToBurn()
    shares_requested_to_burn = cover_shares + non_cover_shares
    with reverts(encode_error("IncorrectSharesRequestedToBurn(uint256)", [shares_requested_to_burn])):
        oracle_report(sharesRequestedToBurn=shares_requested_to_burn + 1, skip_withdrawals=True, silent=True)


def test_withdrawal_queue_timestamp(steth_holder):
    wait_to_next_available_report_time(contracts.hash_consensus_for_accounting_oracle)

    request_id = create_withdrawal_request(steth_holder)
    request_timestamp = contracts.withdrawal_queue.getWithdrawalStatus([request_id])[0][3]

    with reverts(encode_error("IncorrectRequestFinalization(uint256)", [request_timestamp])):
        oracle_report(withdrawalFinalizationBatches=[request_id], silent=True, wait_to_next_report_time=False)


def fake_deposited_validators_increase(cl_validators_diff):
    (deposited, _, _) = contracts.lido.getBeaconStat()

    voting = accounts.at(contracts.voting.address, force=True)
    contracts.acl.createPermission(
        voting,
        contracts.lido,
        web3.keccak(text="UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE"),
        voting,
        {"from": voting},
    )

    contracts.lido.unsafeChangeDepositedValidators(deposited + cl_validators_diff, {"from": voting})


def create_withdrawal_request(steth_holder):
    contracts.lido.approve(contracts.withdrawal_queue.address, ETH(1), {"from": steth_holder})
    contracts.withdrawal_queue.requestWithdrawals([ETH(1)], steth_holder, {"from": steth_holder})

    return contracts.withdrawal_queue.getLastRequestId()
