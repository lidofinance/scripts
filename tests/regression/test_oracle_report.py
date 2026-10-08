import pytest
from brownie import reverts

from utils.balance import set_balance_in_wei
from utils.config import contracts
from utils.evm_script import encode_error
from utils.test.helpers import ETH, GWEI, eth_balance
from utils.test.oracle_report_helpers import oracle_report


@pytest.mark.parametrize("cl_diff", [ETH(10), 0, -ETH(10)], ids=["rewards", "no-rewards", "slashing"])
def test_oracle_report_accounts_for_new_withdrawals(cl_diff):
    report = oracle_report(
        cl_diff=cl_diff, report_el_vault=False, sharesRequestedToBurn=0, skip_withdrawals=True, dry_run=True
    )
    pre_cl, pre_pending, _, deposits = contracts.lido.getBalanceStats()
    previous_vault_balance = contracts.oracle_report_sanity_checker.lastVaultBalanceAfterTransfer()
    new_withdrawals = report.withdrawalVaultBalance - previous_vault_balance
    assert new_withdrawals > 0
    assert report.clValidatorsBalanceGwei == (pre_cl + cl_diff - new_withdrawals) // GWEI
    assert report.clPendingBalanceGwei == (pre_pending + deposits) // GWEI
    assert report.stakingModuleIdsWithUpdatedBalance == list(contracts.staking_router.getStakingModuleIds())
    assert sum(report.validatorBalancesGweiByStakingModule) == report.clValidatorsBalanceGwei

    oracle_report(
        cl_diff=cl_diff,
        report_el_vault=False,
        sharesRequestedToBurn=0,
        skip_withdrawals=True,
        wait_to_next_report_time=False,
    )
    post_cl, post_pending, _, _ = contracts.lido.getBalanceStats()
    assert post_cl == report.clValidatorsBalanceGwei * GWEI
    assert post_pending == report.clPendingBalanceGwei * GWEI
    assert contracts.oracle_report_sanity_checker.lastVaultBalanceAfterTransfer() == eth_balance(
        contracts.withdrawal_vault.address
    )
    assert [
        contracts.staking_router.getModuleValidatorsBalance(module_id) // GWEI
        for module_id in report.stakingModuleIdsWithUpdatedBalance
    ] == report.validatorBalancesGweiByStakingModule


@pytest.mark.parametrize(
    "vault_options",
    [{}, {"report_withdrawals_vault": False}, {"exclude_vaults_balances": True}],
    ids=["report-vault", "exclude-withdrawals", "exclude-vaults"],
)
def test_oracle_report_does_not_deduct_previous_vault_residual(vault_options):
    vault = contracts.withdrawal_vault.address
    set_balance_in_wei(vault, eth_balance(vault) + ETH(10000))
    # The positive-rebase cap leaves some already-accounted withdrawals in the vault.
    internal_ether = contracts.lido.getTotalPooledEther() - contracts.lido.getExternalEther()
    rebase_limit = contracts.oracle_report_sanity_checker.getOracleReportLimits()["maxPositiveTokenRebase"]
    # PositiveTokenRebaseLimiter uses 1e9 precision. Leave enough for a second capped transfer.
    cl_rewards = 2 * (internal_ether * rebase_limit // 10**9) + ETH(32)
    oracle_report(cl_diff=cl_rewards, report_el_vault=False, sharesRequestedToBurn=0, skip_withdrawals=True)
    residual = contracts.oracle_report_sanity_checker.lastVaultBalanceAfterTransfer()
    assert residual > 0
    assert eth_balance(vault) == residual

    new_withdrawals = ETH(32)
    set_balance_in_wei(vault, residual + new_withdrawals)
    report = oracle_report(
        cl_diff=0,
        report_el_vault=False,
        sharesRequestedToBurn=0,
        skip_withdrawals=True,
        dry_run=True,
        **vault_options,
    )
    pre_cl = contracts.lido.getBalanceStats()[0]
    reported_withdrawals = 0 if vault_options else new_withdrawals
    assert report.withdrawalVaultBalance == residual + reported_withdrawals
    assert report.clValidatorsBalanceGwei == (pre_cl - reported_withdrawals) // GWEI
    assert sum(report.validatorBalancesGweiByStakingModule) == report.clValidatorsBalanceGwei

    oracle_report(
        cl_diff=0,
        report_el_vault=False,
        sharesRequestedToBurn=0,
        skip_withdrawals=True,
        wait_to_next_report_time=False,
        **vault_options,
    )
    assert contracts.lido.getBalanceStats()[0] == report.clValidatorsBalanceGwei * GWEI
    unreported_withdrawals = new_withdrawals - reported_withdrawals
    assert eth_balance(vault) == (
        contracts.oracle_report_sanity_checker.lastVaultBalanceAfterTransfer() + unreported_withdrawals
    )

    # Explicit invalid overrides must still be rejected by SRv3, not silently clamped.
    residual = contracts.oracle_report_sanity_checker.lastVaultBalanceAfterTransfer()
    assert residual > 0
    invalid_report = oracle_report(
        cl_diff=0,
        withdrawalVaultBalance=residual - 1,
        report_el_vault=False,
        sharesRequestedToBurn=0,
        skip_withdrawals=True,
        dry_run=True,
    )
    assert invalid_report.withdrawalVaultBalance == residual - 1
    pre_cl, pre_pending, _, deposits = contracts.lido.getBalanceStats()
    with reverts(encode_error("IncorrectCLWithdrawalsVaultBalance(uint256,uint256)", [residual - 1, residual])):
        contracts.oracle_report_sanity_checker.checkAccountingOracleReport.call(
            24 * 60 * 60,
            pre_cl,
            pre_pending,
            invalid_report.clValidatorsBalanceGwei * GWEI,
            invalid_report.clPendingBalanceGwei * GWEI,
            invalid_report.withdrawalVaultBalance,
            invalid_report.elRewardsVaultBalance,
            invalid_report.sharesRequestedToBurn,
            deposits,
            0,
            {"from": contracts.accounting.address},
        )


def test_oracle_report_uses_reported_withdrawal_vault_override():
    residual = contracts.oracle_report_sanity_checker.lastVaultBalanceAfterTransfer()
    set_balance_in_wei(contracts.withdrawal_vault.address, residual + ETH(64))
    reported_balance = residual + ETH(32)
    report = oracle_report(
        cl_diff=0,
        withdrawalVaultBalance=reported_balance,
        report_el_vault=False,
        sharesRequestedToBurn=0,
        skip_withdrawals=True,
        dry_run=True,
    )
    assert report.withdrawalVaultBalance == reported_balance
    assert report.clValidatorsBalanceGwei == (contracts.lido.getBalanceStats()[0] - ETH(32)) // GWEI
    oracle_report(
        cl_diff=0,
        withdrawalVaultBalance=reported_balance,
        report_el_vault=False,
        sharesRequestedToBurn=0,
        skip_withdrawals=True,
        wait_to_next_report_time=False,
    )
    assert contracts.lido.getBalanceStats()[0] == report.clValidatorsBalanceGwei * GWEI
