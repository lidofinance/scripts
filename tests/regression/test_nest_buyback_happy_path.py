from brownie import convert, interface, ZERO_ADDRESS

from utils.config import contracts
from utils.test.helpers import ETH
from utils.test.deposits_helpers import WEI_TOLERANCE
from utils.test.oracle_report_helpers import oracle_report

from scripts.upgrade_2026_08_05 import (
    TMC,
    ORACLE_ROUTER,
    LIDO_LOCATOR,
    NEW_TOKEN_RATE_NOTIFIER,
    STAKING_REVENUE_SOURCE,
    BUYBACK_EXECUTOR,
    BUYBACK_STONKS_TREASURY,
    BUYBACK_ALLOCATOR,
)

QUOTE_DENOMINATION_ETH = 1
ONE_DAY = 86400

# Launch staleness (finance) is 1h ETH/USD bridge, 24h token feeds. Not usable on the fork: fast-forwarded
# DG timelock delays plus the oracle_report frame push the clock past the Chainlink feeds' frozen updatedAt,
# so 1h/24h trip OracleStale. We widen the bound to cover that gap for the fork run — quote (ETH), active
# flag and underlying feeds are identical to launch.
FORK_FEED_STALENESS_SECONDS = 30 * ONE_DAY

TOTAL_BASIS_POINTS = 10_000
SECONDS_PER_YEAR = 365 * ONE_DAY
NORMAL_CL_APR_BP = 300  # 3%, well under the oracle's ~10% annual CL-increase sanity limit


def _configure_oracle_router_feeds(oracle_router, tmc):
    """Set the OracleRouter feeds as TMC — the operational step the vote leaves to TMC post-launch."""
    steth = contracts.lido.address
    ldo = contracts.ldo_token.address
    if oracle_router.ethUsdBridge()["aggregator"] == ZERO_ADDRESS:
        oracle_router.setEthUsdBridge(FORK_FEED_STALENESS_SECONDS, {"from": tmc})
    if not oracle_router.tokenConfig(steth)["isActive"]:
        oracle_router.setTokenFeed(steth, QUOTE_DENOMINATION_ETH, FORK_FEED_STALENESS_SECONDS, True, {"from": tmc})
    if not oracle_router.tokenConfig(ldo)["isActive"]:
        oracle_router.setTokenFeed(ldo, QUOTE_DENOMINATION_ETH, FORK_FEED_STALENESS_SECONDS, True, {"from": tmc})


def _production_rebase_cl_diff():
    """CL rewards a normal report carries: current CL balance at ~3% APR over the report's period."""
    consensus = contracts.hash_consensus_for_accounting_oracle
    slots_per_epoch, seconds_per_slot, _ = consensus.getChainConfig()
    _, epochs_per_frame, _ = consensus.getFrameConfig()
    current_ref_slot, _ = consensus.getCurrentFrame()
    last_processing_ref_slot = contracts.accounting_oracle.getLastProcessingRefSlot()

    next_ref_slot = current_ref_slot + epochs_per_frame * slots_per_epoch
    elapsed_seconds = (next_ref_slot - last_processing_ref_slot) * seconds_per_slot

    cl_validators_balance, cl_pending_balance, *_ = contracts.lido.getBalanceStats()
    cl_balance = cl_validators_balance + cl_pending_balance
    return cl_balance * NORMAL_CL_APR_BP * elapsed_seconds // (TOTAL_BASIS_POINTS * SECONDS_PER_YEAR)


def test_nest_buyback_happy_path(accounts, stranger):
    """Drive the launched NEST buyback end to end: rebase -> revenue -> allocate -> CoW order.

    The vote and its DG proposal are applied by the autouse fixtures in tests/regression/conftest.py.
    """
    steth = contracts.lido
    tmc = accounts.at(TMC, force=True)

    oracle_router = interface.OracleRouter(ORACLE_ROUTER)
    buyback_executor = interface.BuybackExecutor(BUYBACK_EXECUTOR)
    buyback_allocator = interface.BuybackAllocator(BUYBACK_ALLOCATOR)
    staking_revenue_source = interface.StakingRevenueSource(STAKING_REVENUE_SOURCE)

    # Preconditions: the launch is in place
    assert interface.LidoLocator(LIDO_LOCATOR).postTokenRebaseReceiver() == NEW_TOKEN_RATE_NOTIFIER
    assert buyback_allocator.activationTS() > 0, "BuybackAllocator not activated"
    assert buyback_executor.stonks() == BUYBACK_STONKS_TREASURY, "BuybackExecutor stonks not set"
    assert buyback_allocator.STETH() == steth.address, "Allocator stETH handle mismatch"

    _configure_oracle_router_feeds(oracle_router, tmc)
    assert oracle_router.tokenConfig(steth.address)["isActive"], "stETH feed not configured on OracleRouter"

    min_order_steth = buyback_executor.minAllowedOrderAmount()

    # Rebase -> revenue accrues in the StakingRevenueSource, then convert it to USD
    cumulative_revenue_before = staking_revenue_source.getCumulativeRevenueUSD()
    oracle_report(cl_diff=_production_rebase_cl_diff(), silent=True)
    assert staking_revenue_source.pendingRevenueStEth() > 0, "no fee shares reached the StakingRevenueSource"

    staking_revenue_source.convertPendingRevenueToUSD({"from": stranger})
    assert staking_revenue_source.getCumulativeRevenueUSD() > cumulative_revenue_before, "cumulative revenue did not grow"
    assert staking_revenue_source.pendingRevenueStEth() == 0, "pending revenue not fully converted"

    # Fund the allocator with fresh stETH
    steth_to_fund = ETH(1000)
    steth.submit(ZERO_ADDRESS, {"from": stranger, "value": steth_to_fund})
    steth.transfer(BUYBACK_ALLOCATOR, steth_to_fund, {"from": stranger})
    assert steth.balanceOf(BUYBACK_ALLOCATOR) >= steth_to_fund - WEI_TOLERANCE, "allocator not funded with stETH"

    spendable_steth = buyback_allocator.spendable()["spendableStEth"]
    assert spendable_steth > 0, "allocator reports nothing spendable"

    # allocate() spends and forwards stETH to Stonks
    stonks_steth_before = steth.balanceOf(BUYBACK_STONKS_TREASURY)
    allocate_tx = buyback_allocator.allocate({"from": stranger})
    assert "AllocationSkipped" not in allocate_tx.events, "allocate() skipped instead of spending"
    allocated = allocate_tx.events["Allocated"]
    assert allocated["spendStEth"] > 0 and allocated["spendUSD"] > 0, "allocate() spent nothing"
    assert convert.to_address(allocated["executor"]) == convert.to_address(BUYBACK_EXECUTOR), "wrong executor"
    processed = allocate_tx.events["AllocationProcessed"]
    assert convert.to_address(processed["stonks"]) == convert.to_address(BUYBACK_STONKS_TREASURY), "wrong stonks"
    assert processed["forwardedToStonks"] > 0, "nothing forwarded to Stonks"
    assert steth.balanceOf(BUYBACK_STONKS_TREASURY) > stonks_steth_before, "Stonks stETH balance did not grow"

    # placeOrder() creates the Stonks/CoW order (stop before off-chain settlement)
    placement = buyback_executor.getPlacementStatus()
    assert placement["canPlace"], "executor cannot place an order"
    assert not placement["isStonksCreationPaused"] and not placement["isStonksKilled"], "Stonks creation blocked"
    assert placement["sellAmount"] >= min_order_steth, "sell amount below the minimum order amount"

    place_order_tx = buyback_executor.placeOrder({"from": stranger})
    order = place_order_tx.return_value
    assert order is not None, "placeOrder returned no order"
    assert order != ZERO_ADDRESS, "placeOrder returned the zero address"
    order_placed = place_order_tx.events["OrderPlaced"]
    assert convert.to_address(order_placed["order"]) == convert.to_address(order), "OrderPlaced order mismatch"
    assert order_placed["sellAmount"] > 0 and order_placed["minBuyAmount"] > 0, "order has zero sell/buy amount"
    assert buyback_executor.lastOrderAddress() == order, "lastOrderAddress not updated"
    assert buyback_executor.lastOrderValidTo() > 0, "lastOrderValidTo not set"
