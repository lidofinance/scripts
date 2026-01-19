import pytest
from brownie import Contract, accounts, chain, interface, OpStackTokenRatePusherWithSomeErrorStub, web3, reverts
from utils.test.oracle_report_helpers import oracle_report
from utils.config import (
    contracts,
    get_deployer_account,
    network_name,
    L1_TOKEN_RATE_NOTIFIER,
    WSTETH_TOKEN,
    ACCOUNTING_ORACLE,
    L1_OPTIMISM_CROSS_DOMAIN_MESSENGER,
)
from utils.test.helpers import ZERO_ADDRESS, eth_balance
from utils.evm_script import encode_error
from typing import TypedDict, TypeVar, Any

# Use as mock for L2 TokenRateOracle
L2_TOKEN_RATE_ORACLE = WSTETH_TOKEN


@pytest.fixture(scope="module")
def accounting_oracle() -> Contract:
    return contracts.accounting_oracle


@pytest.fixture(scope="module")
def lido() -> Contract:
    return contracts.lido


@pytest.fixture(scope="module")
def el_vault() -> Contract:
    return contracts.execution_layer_rewards_vault


@pytest.fixture(scope="module")
def withdrawal_queue() -> Contract:
    return contracts.withdrawal_queue


def test_oracle_report_revert():
    """Test oracle report reverts when messenger is empty"""
    interface.TokenRateNotifier(L1_TOKEN_RATE_NOTIFIER)  # load TokenRateNotifier contract ABI to catch correct error

    web3.provider.make_request("hardhat_setCode", [L1_OPTIMISM_CROSS_DOMAIN_MESSENGER, "0x"])
    web3.provider.make_request("evm_setAccountCode", [L1_OPTIMISM_CROSS_DOMAIN_MESSENGER, "0x"])

    with reverts(encode_error("ErrorTokenRateNotifierRevertedWithNoData()")):
        oracle_report(cl_diff=0, report_el_vault=True, report_withdrawals_vault=False)


def test_only_accounting_can_call_handle_post_token_rebase():
    """Test that only Accounting can call TokenRateNotifier.handlePostTokenRebase"""

    # Any non-Accounting address should not be allowed to call handlePostTokenRebase
    # Use some sane values for the call; the exact numbers are irrelevant, it should revert on caller
    with reverts(encode_error("ErrorNotAuthorizedRebaseCaller()")):
        contracts.token_rate_notifier.handlePostTokenRebase(
            0, # report_timestamp,
            0, # time_elapsed,
            0, # pre_total_shares,
            0, # pre_total_ether,
            0, # post_total_shares,
            0, # post_total_ether,
            0, # shares_minted_as_fees,
            {"from": accounts[0]},
        )


def test_oracle_report_pushes_rate():
    """Test oracle report emits cross domain messenger event"""

    # Load OpCrossDomainMessenger interface to register SentMessage event
    interface.OpCrossDomainMessenger(L1_OPTIMISM_CROSS_DOMAIN_MESSENGER)

    tx, _ = oracle_report(
        cl_diff=0,
        report_el_vault=True,
        report_withdrawals_vault=False,
    )

    tokenRateOracle = interface.ITokenRateUpdatable(L2_TOKEN_RATE_ORACLE)

    wstETH = interface.WstETH(WSTETH_TOKEN)
    accountingOracle = interface.AccountingOracle(ACCOUNTING_ORACLE)

    tokenRate = wstETH.getStETHByWstETH(10**27)

    genesisTime = accountingOracle.GENESIS_TIME()
    secondsPerSlot = accountingOracle.SECONDS_PER_SLOT()
    lastProcessingRefSlot = accountingOracle.getLastProcessingRefSlot()
    updateTimestamp = genesisTime + secondsPerSlot * lastProcessingRefSlot

    updateRateCalldata = tokenRateOracle.updateRate.encode_input(tokenRate, updateTimestamp)

    assert updateRateCalldata == tx.events["SentMessage"]["message"]


def test_oracle_report_success_when_observer_reverts(accounting_oracle: Contract, lido: Contract, el_vault: Contract):
    """Test oracle report works when token rate observer reverts"""

    opStackTokenRatePusher = OpStackTokenRatePusherWithSomeErrorStub.deploy({"from": get_deployer_account()})

    tokenRateNotifier = interface.TokenRateNotifier(L1_TOKEN_RATE_NOTIFIER)
    tokenRateNotifierOwner = tokenRateNotifier.owner()
    tokenRateNotifier.addObserver(opStackTokenRatePusher, {"from": tokenRateNotifierOwner})

    accounts[0].transfer(el_vault.address, 10**18)
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

    pre_total_pooled = lido.getTotalPooledEther(block_identifier=block_before_report)
    pre_external_ether = lido.getExternalEther(block_identifier=block_before_report)
    pre_internal_ether = pre_total_pooled - pre_external_ether

    post_total_shares = lido.getTotalShares(block_identifier=block_after_report)
    post_external_shares = lido.getExternalShares(block_identifier=block_after_report)
    post_internal_shares = post_total_shares - post_external_shares

    expected_post_internal_ether = (
        pre_internal_ether + el_rewards - withdrawals_finalized["amountOfETHLocked"]
    )
    expected_post_total_pooled = expected_post_internal_ether + (
        post_external_shares * expected_post_internal_ether // post_internal_shares
    )

    assert (
        lido.getTotalPooledEther(block_identifier=block_after_report)
        == expected_post_total_pooled
    ), "TotalPooledEther change mismatch"

    assert (
        lido.getTotalShares(block_identifier=block_before_report)
        == lido.getTotalShares(
            block_identifier=block_after_report,
        )
        + shares_burnt["sharesAmount"]
    ), "TotalShares has changed"

    assert (
        eth_balance(lido.address, block_before_report) + el_rewards
        == eth_balance(lido.address, block_after_report) + withdrawals_finalized["amountOfETHLocked"]
    ), "Lido ETH balance change mismatch"

    assert eth_balance(el_vault.address, block_after_report) == 0, "Expected EL vault to be empty"

    assert tx.events["PushTokenRateFailed"]["observer"] == opStackTokenRatePusher
    assert tx.events["PushTokenRateFailed"]["lowLevelRevertData"] == "0x332e27d2"


T = TypeVar("T")

WithdrawalsFinalized = TypedDict(
    "WithdrawalsFinalized",
    {"from": str, "to": str, "amountOfETHLocked": int, "sharesToBurn": int, "timestamp": int},
)


class ELRewardsReceived(TypedDict):
    """ELRewardsReceived event definition"""

    amount: int


class SharesBurnt(TypedDict):
    """SharesBurnt event definition"""

    account: str
    preRebaseTokenAmount: int
    postRebaseTokenAmount: int
    sharesAmount: int


def _get_events(tx, event: type[T]) -> list[T]:
    """Get event of type T from transaction"""

    assert event.__name__ in tx.events, f"Event {event.__name__} was not found in the transaction"
    return tx.events[event.__name__]


def _first_event(tx, event: type[T]) -> T:
    """Get first event of type T from transaction"""

    events = _get_events(tx, event)
    assert len(events) == 1, f"Event {event.__name__} was found more than once in the transaction"
    return events[0]


def _try_get_withdrawals_finalized(tx: Any) -> WithdrawalsFinalized:
    if WithdrawalsFinalized.__name__ in tx.events:
        return _first_event(tx, WithdrawalsFinalized)
    else:
        return {"from": ZERO_ADDRESS, "to": ZERO_ADDRESS, "amountOfETHLocked": 0, "sharesToBurn": 0, "timestamp": 0}


def _try_get_shares_burnt(tx: Any) -> SharesBurnt:
    if SharesBurnt.__name__ in tx.events:
        return _first_event(tx, SharesBurnt)
    else:
        return SharesBurnt(account=ZERO_ADDRESS, preRebaseTokenAmount=0, postRebaseTokenAmount=0, sharesAmount=0)
