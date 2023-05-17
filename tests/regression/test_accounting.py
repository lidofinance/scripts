from typing import TypedDict, TypeVar, Any

import pytest
from brownie import Contract, accounts, chain, web3
from brownie.exceptions import brownie
from brownie.network.account import Account
from web3 import Web3

from tests.conftest import Helpers
from utils.config import contracts
from utils.test.helpers import ETH, GWEI, ZERO_ADDRESS, almostEqWithDiff, eth_balance
from utils.test.oracle_report_helpers import ONE_DAY, SHARE_RATE_PRECISION, oracle_report

LIMITER_PRECISION_BASE = 10**9
MAX_BASIS_POINTS = 10_000


@pytest.fixture(scope="module")
def accounting_oracle() -> Contract:
    return contracts.accounting_oracle


@pytest.fixture(scope="module")
def lido() -> Contract:
    return contracts.lido


@pytest.fixture(scope="module")
def withdrawal_queue() -> Contract:
    return contracts.withdrawal_queue


@pytest.fixture(scope="module")
def el_vault() -> Contract:
    return contracts.execution_layer_rewards_vault


@pytest.fixture(scope="module")
def burner() -> Contract:
    return contracts.burner


@pytest.fixture(scope="module")
def withdrawal_vault() -> Contract:
    return contracts.withdrawal_vault


def test_accounting_no_cl_rebase(
    accounting_oracle: Contract,
    lido: Contract,
    helpers: Helpers
):
    """Check Lido rebase after accounting report with no CL rebase"""

    block_before_report = chain.height
    tx, _ = oracle_report(cl_diff=0, exclude_vaults_balances=True)
    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther has changed"

    assert lido.getTotalShares(block_identifier=block_before_report) == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares has changed"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_before <= shares_rate_after, "Shares rate lowered"

    post_ttl_shares_event = _first_event(tx, PostTotalShares)
    assert (
        post_ttl_shares_event["preTotalPooledEther"] == post_ttl_shares_event["postTotalPooledEther"] + withdrawals_finalized["amountOfETHLocked"]
    ), "PostTotalShares preTotalPooledEther <> postTotalPooledEther"

    assert eth_balance(lido.address, block_before_report) == eth_balance(
        lido.address, block_after_report
    ) + withdrawals_finalized["amountOfETHLocked"], "Lido ETH balance has changed"


@pytest.mark.parametrize(
    "rebase_amount",
    [ETH(-1_000)],
)
def test_accounting_negative_cl_rebase(accounting_oracle: Contract, lido: Contract, rebase_amount: int):
    """Check Lido rebase after accounting report with negative CL rebase"""

    block_before_report = chain.height
    tx, _ = oracle_report(cl_diff=rebase_amount, exclude_vaults_balances=True)
    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) + rebase_amount == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther change mismatch"

    assert lido.getTotalShares(block_identifier=block_before_report) == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares has changed"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_after < shares_rate_before, "Shares rate has not decreased"

    eth_distributed_event = _first_event(tx, ETHDistributed)
    assert (
        eth_distributed_event["preCLBalance"] + rebase_amount == eth_distributed_event["postCLBalance"]
    ), "ETHDistributed: CL balance differs from expected"

    post_ttl_shares_event = _first_event(tx, PostTotalShares)
    assert (
        post_ttl_shares_event["preTotalPooledEther"] + rebase_amount
            == post_ttl_shares_event["postTotalPooledEther"] + withdrawals_finalized["amountOfETHLocked"]
    ), "PostTotalShares: TotalPooledEther differs from expected"


def test_accounting_cl_rebase_at_limits(accounting_oracle: Contract, lido: Contract):
    """Check Lido rebase after accounting report with positive CL rebase close to the limits"""

    block_before_report = chain.height

    annual_increase_limit = contracts.oracle_report_sanity_checker.getOracleReportLimits()[2]
    pre_cl_balance = contracts.lido.getBeaconStat()[-1]

    rebase_amount = (annual_increase_limit * ONE_DAY + 1) * pre_cl_balance // (365 * ONE_DAY) // MAX_BASIS_POINTS
    rebase_amount = _round_to_gwei(rebase_amount)

    tx, _ = oracle_report(cl_diff=rebase_amount, exclude_vaults_balances=True)
    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) + rebase_amount == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther change mismatch"

    shares_as_fees_list = [e["sharesValue"] for e in _get_events(tx, TransferShares)]

    minted_shares_sum = 0

    if (withdrawals_finalized["amountOfETHLocked"] == 0): # no withdrawals processed
        assert len(shares_as_fees_list) == 2, "Expected transfer of shares to NodeOperatorsRegistry and DAO"
        assert almostEqWithDiff(
            shares_as_fees_list[0],
            shares_as_fees_list[1],
            1,
        ), "Shares minted to DAO and NodeOperatorsRegistry mismatch"

        minted_shares_sum = shares_as_fees_list[0] + shares_as_fees_list[1]
    else:
        assert len(shares_as_fees_list) == 3, "Expected transfer of shares to NodeOperatorsRegistry and DAO"
        assert almostEqWithDiff(
            shares_as_fees_list[1],
            shares_as_fees_list[2],
            1,
        ), "Shares minted to DAO and NodeOperatorsRegistry mismatch"

        minted_shares_sum = shares_as_fees_list[1] + shares_as_fees_list[2]

    token_rebased_event = _first_event(tx, TokenRebased)
    assert token_rebased_event["sharesMintedAsFees"] == minted_shares_sum, "TokenRebased: sharesMintedAsFee mismatch"

    assert lido.getTotalShares(block_identifier=block_before_report) + minted_shares_sum == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares change mismatch"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_after > shares_rate_before, "Shares rate has not increased"

    eth_distributed_event = _first_event(tx, ETHDistributed)
    assert (
        eth_distributed_event["preCLBalance"] + rebase_amount == eth_distributed_event["postCLBalance"]
    ), "ETHDistributed: CL balance has not increased"

    post_ttl_shares_event = _first_event(tx, PostTotalShares)
    assert (
        post_ttl_shares_event["preTotalPooledEther"] + rebase_amount == post_ttl_shares_event["postTotalPooledEther"]
    ) + withdrawals_finalized["amountOfETHLocked"], "PostTotalShares: TotalPooledEther has not increased"


def test_accounting_cl_rebase_above_limits():
    """Check that report reverts on sanity checks"""

    block_before_report = chain.height

    max_cl_rebase_via_limiter = _rebase_limit_wei(block_identifier=block_before_report)
    annual_increase_limit = contracts.oracle_report_sanity_checker.getOracleReportLimits()[2]
    pre_cl_balance = contracts.lido.getBeaconStat()[-1]

    rebase_amount = ((annual_increase_limit + 1) * ONE_DAY + 1) * pre_cl_balance // (365 * ONE_DAY) // MAX_BASIS_POINTS
    assert max_cl_rebase_via_limiter > rebase_amount, "Expected annual limit to shot first"

    error_hash = Web3.keccak(text="IncorrectCLBalanceIncrease(uint256)")[:4]
    with brownie.reverts(revert_pattern=f"typed error: {error_hash.hex()}[0-9a-f]+"):  # type: ignore
        oracle_report(cl_diff=rebase_amount, exclude_vaults_balances=True)


def test_accounting_no_el_rewards(accounting_oracle: Contract, lido: Contract, helpers: Helpers):
    """Test rebase with no EL rewards"""

    block_before_report = chain.height
    tx, _ = oracle_report(cl_diff=0, exclude_vaults_balances=True)
    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther has changed"

    assert lido.getTotalShares(block_identifier=block_before_report) == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares has changed"

    assert eth_balance(lido.address, block_before_report) == eth_balance(
        lido.address, block_after_report
    ) + withdrawals_finalized["amountOfETHLocked"], "Lido ETH balance has changed"

    helpers.assert_event_not_emitted(WithdrawalsReceived.__name__, tx)
    helpers.assert_event_not_emitted(ELRewardsReceived.__name__, tx)


def test_accounting_normal_el_rewards(accounting_oracle: Contract, lido: Contract, el_vault: Contract):
    """Test rebase with normal EL rewards"""

    block_before_report = chain.height

    el_rewards = eth_balance(el_vault.address, block_before_report)
    assert el_rewards > 0, "Expected EL vault to be non-empty"

    tx, _ = oracle_report(
        cl_diff=0,
        report_el_vault=True,
        report_withdrawals_vault=False,
    )

    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(
        block_identifier=block_before_report
    ) + el_rewards == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected change mismatch"

    assert _first_event(tx, ELRewardsReceived)["amount"] == el_rewards, "ELRewardsReceived: amount mismatch"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) + el_rewards == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther change mismatch"

    assert lido.getTotalShares(block_identifier=block_before_report) == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares has changed"

    assert eth_balance(lido.address, block_before_report) + el_rewards == eth_balance(
        lido.address, block_after_report
    ) + withdrawals_finalized["amountOfETHLocked"], "Lido ETH balance change mismatch"

    assert eth_balance(el_vault.address, block_after_report) == 0, "Expected EL vault to be empty"


def test_accounting_el_rewards_at_limits(
    accounting_oracle: Contract,
    lido: Contract,
    el_vault: Contract,
    eth_whale: Account,
):
    """Test rebase with EL rewards at limits"""

    block_before_report = chain.height
    el_rewards = _rebase_limit_wei(block_identifier=block_before_report)

    _drain_eth(el_vault.address)
    eth_whale.transfer(
        Account(el_vault.address),
        el_rewards,
        silent=True,
    )

    tx, _ = oracle_report(
        cl_diff=0,
        report_el_vault=True,
        report_withdrawals_vault=False,
    )

    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(
        block_identifier=block_before_report
    ) + el_rewards == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected change mismatch"

    assert _first_event(tx, ELRewardsReceived)["amount"] == el_rewards, "ELRewardsReceived: amount mismatch"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) + el_rewards == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther change mismatch"

    assert lido.getTotalShares(block_identifier=block_before_report) == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares has changed"

    assert eth_balance(lido.address, block_before_report) + el_rewards == eth_balance(
        lido.address, block_after_report
    ) + withdrawals_finalized["amountOfETHLocked"], "Lido ETH balance change mismatch"

    assert (
        eth_balance(contracts.execution_layer_rewards_vault.address, block_after_report) == 0
    ), "Expected EL vault to be empty"


def test_accounting_el_rewards_above_limits(
    accounting_oracle: Contract,
    lido: Contract,
    el_vault: Contract,
    eth_whale: Account,
):
    """Test rebase with EL rewards above limits"""

    block_before_report = chain.height

    rewards_excess = ETH(10)
    expected_rewards = _rebase_limit_wei(block_identifier=block_before_report)
    el_rewards = expected_rewards + rewards_excess

    _drain_eth(el_vault.address)
    eth_whale.transfer(
        Account(el_vault.address),
        el_rewards,
        silent=True,
    )

    tx, _ = oracle_report(
        cl_diff=0,
        report_el_vault=True,
        report_withdrawals_vault=False,
    )

    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(
        block_identifier=block_before_report
    ) + expected_rewards == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected change mismatch"

    assert _first_event(tx, ELRewardsReceived)["amount"] == expected_rewards, "ELRewardsReceived: amount mismatch"

    assert lido.getTotalPooledEther(
        block_identifier=block_before_report
    ) + expected_rewards == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther change mismatch"

    assert lido.getTotalShares(block_identifier=block_before_report) == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares has changed"

    assert eth_balance(lido.address, block_before_report) + expected_rewards == eth_balance(
        lido.address, block_after_report
    ) + withdrawals_finalized["amountOfETHLocked"], "Lido ETH balance change mismatch"

    assert (
        eth_balance(contracts.execution_layer_rewards_vault.address, block_after_report) == rewards_excess
    ), "Expected EL vault to be filled with excess rewards"


def test_accounting_no_withdrawals(accounting_oracle: Contract, lido: Contract, helpers: Helpers):
    """Test rebase with no withdrawals"""

    block_before_report = chain.height
    tx, _ = oracle_report(cl_diff=0, exclude_vaults_balances=True)
    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther has changed"

    assert lido.getTotalShares(block_identifier=block_before_report) == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares has changed"

    assert eth_balance(lido.address, block_before_report) == eth_balance(
        lido.address, block_after_report
    ) + withdrawals_finalized["amountOfETHLocked"], "Lido ETH balance has changed"

    helpers.assert_event_not_emitted(WithdrawalsReceived.__name__, tx)
    helpers.assert_event_not_emitted(ELRewardsReceived.__name__, tx)


def test_accounting_withdrawals_at_limits(
    accounting_oracle: Contract,
    lido: Contract,
    withdrawal_vault: Contract,
):
    """Test rebase with normal withdrawals amount"""

    block_before_report = chain.height

    withdrawals = _rebase_limit_wei(block_identifier=block_before_report)

    web3.manager.request_blocking(
        "evm_setAccountBalance",  # type: ignore
        [
            withdrawal_vault.address,
            Web3.toHex(withdrawals),
        ],
    )

    tx, _ = oracle_report(
        cl_diff=0,
        report_el_vault=False,
        report_withdrawals_vault=True,
    )

    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(block_identifier=block_before_report) + withdrawals == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther change mismatch"

    shares_as_fees_list = [e["sharesValue"] for e in _get_events(tx, TransferShares)]

    minted_shares_sum = 0

    if (withdrawals_finalized["amountOfETHLocked"] == 0): # no withdrawals processed
        assert len(shares_as_fees_list) == 2, "Expected transfer of shares to NodeOperatorsRegistry and DAO"
        assert almostEqWithDiff(
            shares_as_fees_list[0],
            shares_as_fees_list[1],
            1,
        ), "Shares minted to DAO and NodeOperatorsRegistry mismatch"

        minted_shares_sum = shares_as_fees_list[0] + shares_as_fees_list[1]
    else:
        assert len(shares_as_fees_list) == 3, "Expected transfer of shares to NodeOperatorsRegistry and DAO"
        assert almostEqWithDiff(
            shares_as_fees_list[1],
            shares_as_fees_list[2],
            1,
        ), "Shares minted to DAO and NodeOperatorsRegistry mismatch"

        minted_shares_sum = shares_as_fees_list[1] + shares_as_fees_list[2]

    token_rebased_event = _first_event(tx, TokenRebased)
    assert token_rebased_event["sharesMintedAsFees"] == minted_shares_sum, "TokenRebased: sharesMintedAsFee mismatch"

    assert lido.getTotalShares(block_identifier=block_before_report) + minted_shares_sum == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares change mismatch"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_after > shares_rate_before, "Shares rate has not increased"

    assert _first_event(tx, WithdrawalsReceived)["amount"] == withdrawals, "WithdrawalsReceived: amount mismatch"

    assert eth_balance(withdrawal_vault.address, block_after_report) == 0, "Expected withdrawals vault to be empty"


def test_accounting_withdrawals_above_limits(
    accounting_oracle: Contract,
    lido: Contract,
    withdrawal_vault: Contract,
):
    """Test rebase with excess withdrawals amount"""

    block_before_report = chain.height

    expected_withdrawals = _rebase_limit_wei(block_identifier=block_before_report)
    withdrawals_excess = ETH(10)
    withdrawals = expected_withdrawals + withdrawals_excess

    web3.manager.request_blocking(
        "evm_setAccountBalance",  # type: ignore
        [
            withdrawal_vault.address,
            Web3.toHex(withdrawals),
        ],
    )

    tx, _ = oracle_report(
        cl_diff=0,
        report_el_vault=False,
        report_withdrawals_vault=True,
    )

    block_after_report = chain.height

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)
    shares_burnt = _try_get_shares_burnt(tx)

    assert accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_before_report
    ) < accounting_oracle.getLastProcessingRefSlot(
        block_identifier=block_after_report,
    ), "LastProcessingRefSlot should be updated"

    assert lido.getTotalELRewardsCollected(block_identifier=block_before_report) == lido.getTotalELRewardsCollected(
        block_identifier=block_after_report
    ), "TotalELRewardsCollected has changed"

    assert lido.getTotalPooledEther(
        block_identifier=block_before_report
    ) + expected_withdrawals == lido.getTotalPooledEther(
        block_identifier=block_after_report,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther change mismatch"

    shares_as_fees_list = [e["sharesValue"] for e in _get_events(tx, TransferShares)]

    minted_shares_sum = 0

    if (withdrawals_finalized["amountOfETHLocked"] == 0): # no withdrawals processed
        assert len(shares_as_fees_list) == 2, "Expected transfer of shares to NodeOperatorsRegistry and DAO"
        assert almostEqWithDiff(
            shares_as_fees_list[0],
            shares_as_fees_list[1],
            1,
        ), "Shares minted to DAO and NodeOperatorsRegistry mismatch"

        minted_shares_sum = shares_as_fees_list[0] + shares_as_fees_list[1]
    else:
        assert len(shares_as_fees_list) == 3, "Expected transfer of shares to NodeOperatorsRegistry and DAO"
        assert almostEqWithDiff(
            shares_as_fees_list[1],
            shares_as_fees_list[2],
            1,
        ), "Shares minted to DAO and NodeOperatorsRegistry mismatch"

        minted_shares_sum = shares_as_fees_list[1] + shares_as_fees_list[2]

    token_rebased_event = _first_event(tx, TokenRebased)
    assert token_rebased_event["sharesMintedAsFees"] == minted_shares_sum, "TokenRebased: sharesMintedAsFee mismatch"

    assert lido.getTotalShares(block_identifier=block_before_report) + minted_shares_sum == lido.getTotalShares(
        block_identifier=block_after_report,
    ) + shares_burnt["sharesAmount"], "TotalShares change mismatch"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_after > shares_rate_before, "Shares rate has not increased"

    assert (
        _first_event(tx, WithdrawalsReceived)["amount"] == expected_withdrawals
    ), "WithdrawalsReceived: amount mismatch"

    assert (
        eth_balance(withdrawal_vault.address, block_after_report) == withdrawals_excess
    ), "Expected withdrawal vault to be filled with excess rewards"


def test_accounting_shares_burn_at_limits(burner: Contract, lido: Contract, steth_whale: Account):
    """Test shares burnt with amount at the limit"""

    shares_limit = _shares_burn_limit_no_pooled_ether_changes()
    initial_burner_balance = lido.sharesOf(burner.address)

    #assert initial_burner_balance == 0, "Expected burner to have no shares"
    assert lido.sharesOf(steth_whale.address) > shares_limit, "Not enough shares on whale account"
    steth_of_shares = lido.getPooledEthByShares(shares_limit)
    lido.approve(burner.address, steth_of_shares, {"from": steth_whale.address})

    cover_shares, no_cover_shares = shares_limit // 3, shares_limit - shares_limit // 3

    tx = burner.requestBurnShares(steth_whale.address, no_cover_shares, {"from": lido.address})
    shares_burn_request_event = _first_event(tx, StETHBurnRequested)
    assert shares_burn_request_event["amountOfShares"] == no_cover_shares, "StETHBurnRequested: amountOfShares mismatch"
    assert shares_burn_request_event["isCover"] is False, "StETHBurnRequested: isCover mismatch"
    assert lido.sharesOf(burner.address) == no_cover_shares + initial_burner_balance, "Burner shares mismatch"

    tx = burner.requestBurnSharesForCover(steth_whale.address, cover_shares, {"from": lido.address})
    shares_burn_request_event = _first_event(tx, StETHBurnRequested)
    assert shares_burn_request_event["amountOfShares"] == cover_shares, "StETHBurnRequested: amountOfShares mismatch"
    assert shares_burn_request_event["isCover"] is True, "StETHBurnRequested: isCover mismatch"
    assert lido.sharesOf(burner.address) == shares_limit + initial_burner_balance, "Burner shares mismatch"

    block_before_report = chain.height
    tx, _ = oracle_report(cl_diff=0, exclude_vaults_balances=True)
    block_after_report = chain.height

    finalized_withdrawals = _try_get_withdrawals_finalized(tx)
    shares_burned_event = _try_get_shares_burnt(tx)

    burnt_due_to_withdrawals = (
        finalized_withdrawals["sharesToBurn"] - lido.sharesOf(burner.address) + initial_burner_balance
    )

    assert burnt_due_to_withdrawals >= 0
    assert (
        shares_burned_event["sharesAmount"] - burnt_due_to_withdrawals == shares_limit
    ), "SharesBurnt: sharesAmount mismatch"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_after > shares_rate_before, "Shares rate has not increased"

    assert lido.getTotalShares(block_identifier=block_before_report) - shares_limit == lido.getTotalShares(
        block_identifier=block_after_report
    ) + burnt_due_to_withdrawals, "TotalShares change mismatch"

def test_accounting_shares_burn_above_limits(burner: Contract, lido: Contract, steth_whale: Account):
    """Test shares burnt with amount above the limit"""

    shares_limit = _shares_burn_limit_no_pooled_ether_changes()
    excess_amount = 42

    initial_burner_balance = lido.sharesOf(burner.address)
    #assert initial_burner_balance == 0, "Expected burner to have no shares"

    assert lido.sharesOf(steth_whale.address) > shares_limit + excess_amount, "Not enough shares on whale account"
    steth_of_shares = lido.getPooledEthByShares(shares_limit + excess_amount)
    lido.approve(burner.address, steth_of_shares, {"from": steth_whale.address})

    cover_shares, no_cover_shares = shares_limit // 3, shares_limit - shares_limit // 3 + excess_amount

    tx = burner.requestBurnShares(steth_whale.address, no_cover_shares, {"from": lido.address})
    shares_burn_request_event = _first_event(tx, StETHBurnRequested)
    assert shares_burn_request_event["amountOfShares"] == no_cover_shares, "StETHBurnRequested: amountOfShares mismatch"
    assert shares_burn_request_event["isCover"] is False, "StETHBurnRequested: isCover mismatch"
    assert lido.sharesOf(burner.address) == no_cover_shares + initial_burner_balance, "Burner shares mismatch"

    tx = burner.requestBurnSharesForCover(steth_whale.address, cover_shares, {"from": lido.address})
    shares_burn_request_event = _first_event(tx, StETHBurnRequested)
    assert shares_burn_request_event["amountOfShares"] == cover_shares, "StETHBurnRequested: amountOfShares mismatch"
    assert shares_burn_request_event["isCover"] is True, "StETHBurnRequested: isCover mismatch"
    assert lido.sharesOf(burner.address) == shares_limit + excess_amount + initial_burner_balance, "Burner shares mismatch"

    block_before_report = chain.height
    tx, _ = oracle_report(cl_diff=0, exclude_vaults_balances=True)
    block_after_report = chain.height

    finalized_withdrawals = _try_get_withdrawals_finalized(tx)
    shares_burned_event = _try_get_shares_burnt(tx)

    burnt_due_to_withdrawals = (
        finalized_withdrawals["sharesToBurn"] - lido.sharesOf(burner.address) + initial_burner_balance + excess_amount
    )
    assert burnt_due_to_withdrawals >= 0

    assert (
        shares_burned_event["sharesAmount"] - burnt_due_to_withdrawals == shares_limit
    ), "SharesBurnt: sharesAmount mismatch"

    shares_rate_before, shares_rate_after = _shares_rate_from_event(tx)
    assert shares_rate_after > shares_rate_before, "Shares rate has not increased"

    assert lido.getTotalShares(block_identifier=block_before_report) - shares_limit == lido.getTotalShares(
        block_identifier=block_after_report
    ) + burnt_due_to_withdrawals, "TotalShares change mismatch"

    extra_shares = lido.sharesOf(burner.address)
    assert extra_shares >= excess_amount, "Expected burner to have excess shares"

    tx, _ = oracle_report(cl_diff=0, exclude_vaults_balances=True)
    shares_burned_event = _first_event(tx, SharesBurnt)
    assert shares_burned_event["sharesAmount"] == extra_shares, "SharesBurnt: sharesAmount mismatch"
    assert lido.sharesOf(burner.address) == 0, "Expected burner to have no shares"


def test_accounting_overfill_both_vaults(
    lido: Contract,
    withdrawal_vault: Contract,
    el_vault: Contract,
    helpers: Helpers,
):
    """Test rebase with excess ETH amount on both vaults"""

    limit = _rebase_limit_wei(block_identifier=chain.height)
    excess = ETH(10)

    web3.manager.request_blocking(
        "evm_setAccountBalance",  # type: ignore
        [
            withdrawal_vault.address,
            Web3.toHex(limit + excess),
        ],
    )
    web3.manager.request_blocking(
        "evm_setAccountBalance",  # type: ignore
        [
            el_vault.address,
            Web3.toHex(limit + excess),
        ],
    )

    initial_block = chain.height

    tx, _ = oracle_report(cl_diff=0, report_el_vault=True, report_withdrawals_vault=True)
    updated_limit = _rebase_limit_wei(block_identifier=chain.height)
    el_vault_excess = (limit + excess) - (updated_limit - excess)

    withdrawals_finalized = _try_get_withdrawals_finalized(tx)

    assert (
        eth_balance(withdrawal_vault.address) == excess
    ), "Expected withdrawals vault to be filled with excess rewards"
    assert _first_event(tx, WithdrawalsReceived)["amount"] == limit, "WithdrawalsReceived: amount mismatch"

    assert eth_balance(el_vault.address) == eth_balance(
        el_vault.address, block_identifier=initial_block
    ), "Expected EL vault to be kept unchanged"
    helpers.assert_event_not_emitted(ELRewardsReceived.__name__, tx)

    tx, _ = oracle_report(cl_diff=0, report_el_vault=True, report_withdrawals_vault=True)

    assert eth_balance(withdrawal_vault.address) == 0, "Expected withdrawals vault to be emptied"
    assert _first_event(tx, WithdrawalsReceived)["amount"] == excess, "WithdrawalsReceived: amount mismatch"

    assert eth_balance(el_vault.address) == el_vault_excess, "Expected EL vault to be filled with excess rewards"
    assert _first_event(tx, ELRewardsReceived)["amount"] == updated_limit - excess, "ELRewardsReceived: amount mismatch"

    tx, _ = oracle_report(cl_diff=0, report_el_vault=True, report_withdrawals_vault=True)

    helpers.assert_event_not_emitted(WithdrawalsReceived.__name__, tx)
    assert eth_balance(el_vault.address) == 0, "Expected EL vault to be emptied"
    assert _first_event(tx, ELRewardsReceived)["amount"] == el_vault_excess, "ELRewardsReceived: amount mismatch"

    assert lido.getTotalELRewardsCollected(
        block_identifier=initial_block
    ) + limit + excess == lido.getTotalELRewardsCollected(
        block_identifier=chain.height
    ), "TotalELRewardsCollected change mismatch"

    assert lido.getTotalPooledEther(block_identifier=initial_block) + (limit + excess) * 2 == lido.getTotalPooledEther(
        block_identifier=chain.height,
    ) + withdrawals_finalized["amountOfETHLocked"], "TotalPooledEther change mismatch"

    assert eth_balance(lido.address, initial_block) + (limit + excess) * 2 == eth_balance(
        lido.address, chain.height
    ) + withdrawals_finalized["amountOfETHLocked"], "Lido ETH balance change mismatch"


class ETHDistributed(TypedDict):
    """ETHDistributed event definition"""

    reportTimestamp: int
    preCLBalance: int
    postCLBalance: int
    withdrawalsWithdrawn: int
    executionLayerRewardsWithdrawn: int
    postBufferedEther: int


class PostTotalShares(TypedDict):
    """PostTotalShares event definition"""

    postTotalPooledEther: int
    preTotalPooledEther: int
    timeElapsed: int
    totalShare: int


class TokenRebased(TypedDict):
    """TokenRebased event definition"""

    reportTimestamp: int
    timeElapsed: int
    preTotalShares: int
    preTotalEther: int
    postTotalShares: int
    postTotalEther: int
    sharesMintedAsFees: int


class ELRewardsReceived(TypedDict):
    """ELRewardsReceived event definition"""

    amount: int


class WithdrawalsReceived(TypedDict):
    """WithdrawalsReceived event definition"""

    amount: int


TransferShares = TypedDict(
    "TransferShares",
    {"from": str, "to": str, "sharesValue": int},
)


class SharesBurnt(TypedDict):
    """SharesBurnt event definition"""

    account: str
    preRebaseTokenAmount: int
    postRebaseTokenAmount: int
    sharesAmount: int

WithdrawalsFinalized = TypedDict(
    "WithdrawalsFinalized",
    { "from": str, "to": str, "amountOfETHLocked": int, "sharesToBurn": int, "timestamp": int },
)

class StETHBurnRequested(TypedDict):
    """StETHBurnRequested event definition"""

    isCover: bool
    requestedBy: str
    amountOfStETH: int
    amountOfShares: int


T = TypeVar("T")


def _first_event(tx, event: type[T]) -> T:
    """Get first event of type T from transaction"""

    events = _get_events(tx, event)
    assert len(events) == 1, f"Event {event.__name__} was found more than once in the transaction"
    return events[0]


def _get_events(tx, event: type[T]) -> list[T]:
    """Get event of type T from transaction"""

    assert event.__name__ in tx.events, f"Event {event.__name__} was not found in the transaction"
    return tx.events[event.__name__]


def _shares_rate_from_event(tx) -> tuple[int, int]:
    """Get shares rate from TokenRebased event"""

    token_rebased_event = _first_event(tx, TokenRebased)
    return (
        token_rebased_event["preTotalEther"] * SHARE_RATE_PRECISION // token_rebased_event["preTotalShares"],
        token_rebased_event["postTotalEther"] * SHARE_RATE_PRECISION // token_rebased_event["postTotalShares"],
    )


def _round_to_gwei(amount: int) -> int:
    """Round amount to gwei"""

    return amount // GWEI * GWEI


def _drain_eth(address: str):
    """Drain ETH from address"""

    accounts.at(address, force=True).transfer(
        Account(ZERO_ADDRESS),
        eth_balance(address),
        silent=True,
    )
    assert eth_balance(address) == 0, f"Expected account {address} to be empty"


def _rebase_limit_wei(block_identifier: int) -> int:
    """Get positive rebase limit from oracle report sanity checker contract"""

    return (
        contracts.oracle_report_sanity_checker.getMaxPositiveTokenRebase(block_identifier=block_identifier)
        * contracts.lido.getTotalPooledEther(block_identifier=block_identifier)
        // LIMITER_PRECISION_BASE
    )


def _shares_burn_limit_no_pooled_ether_changes(block_identifier: int | str = "latest") -> int:
    """Get shares burn limit from oracle report sanity checker contract when NO changes in pooled Ether are expected"""

    rebase_limit = contracts.oracle_report_sanity_checker.getMaxPositiveTokenRebase(block_identifier=block_identifier)
    rebase_limit_plus_1 = rebase_limit + LIMITER_PRECISION_BASE

    return contracts.lido.getTotalShares(block_identifier=block_identifier) * rebase_limit // rebase_limit_plus_1

def _try_get_withdrawals_finalized(tx: Any) -> WithdrawalsFinalized:
    if WithdrawalsFinalized.__name__ in tx.events:
        return _first_event(tx, WithdrawalsFinalized)
    else:
        return {
            "from": ZERO_ADDRESS, "to": ZERO_ADDRESS, "amountOfETHLocked": 0, "sharesToBurn": 0, "timestamp": 0
        }

def _try_get_shares_burnt(tx: Any) -> SharesBurnt:
    if SharesBurnt.__name__ in tx.events:
        return _first_event(tx, SharesBurnt)
    else:
        return SharesBurnt(account=ZERO_ADDRESS, preRebaseTokenAmount=0, postRebaseTokenAmount=0, sharesAmount=0)
