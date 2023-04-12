from contextlib import contextmanager
from typing import Any, Callable, TypedDict

import brownie
import pytest
from brownie import ZERO_ADDRESS, chain, rpc, web3
from brownie.network.account import Account
from brownie.network.state import _notify_registry
from web3.types import Wei

from tests.conftest import Helpers
from utils.config import contracts, ldo_token_address, lido_dao_voting_address, lido_insurance_fund_address
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.import_current_votes import start_and_execute_votes


class Frame(TypedDict):
    """A snapshot of the state before and after an action."""

    init: dict[str, Any]
    post: dict[str, Any]


SnapshotFn = Callable[[], dict]
SandwichFn = Callable[..., tuple[Frame, Frame]]


UINT256_MAX = 2**256 - 1
_1ETH = Wei(10**18)


def test_lido_no_changes_in_views(sandwich_upgrade: SandwichFn):
    """Test that no views change during the upgrade process."""

    frames = sandwich_upgrade(
        lambda: chain.mine(),  # just upgrade and move forward
    )

    _frames_equal(frames)


def test_lido_end_user_snapshot(
    sandwich_upgrade: SandwichFn,
    eth_whale: Account,
    some_contract: Account,
    unknown_person: Account,
):
    def _script():
        lido = contracts.lido

        eth_amount = Wei(_1ETH - 42)
        assert eth_whale.balance() >= eth_amount
        assert lido.balanceOf(eth_whale) == 0

        # send ether to Lido to mint stETH
        web3.eth.send_transaction(
            {
                "from": eth_whale.address,
                "to": lido.address,
                "value": Wei(eth_amount // 2),
            }
        )
        lido.submit(
            ZERO_ADDRESS,
            {
                "from": eth_whale,
                "amount": Wei(eth_amount // 2),
            },
        )

        # play with allowance
        lido.approve(
            some_contract,
            UINT256_MAX,
            {"from": eth_whale},
        )

        lido.decreaseAllowance(
            some_contract,
            13,
            {"from": eth_whale},
        )
        lido.increaseAllowance(
            some_contract,
            13,
            {"from": eth_whale},
        )

        lido.approve(
            some_contract,
            42,
            {"from": eth_whale},
        )

        # send funds by different mechanisms
        lido.transferFrom(
            eth_whale,
            some_contract.address,
            42,
            {"from": some_contract},
        )
        lido.transfer(
            unknown_person,
            17,
            {"from": eth_whale},
        )
        lido.transferShares(
            unknown_person,
            23,
            {"from": some_contract},
        )

        # revoke allowance
        lido.approve(
            some_contract,
            0,
            {"from": eth_whale},
        )

        # split funds accross accounts
        lido.transfer(
            eth_whale,
            11,
            {"from": unknown_person},
        )
        lido.transfer(
            some_contract,
            13,
            {"from": unknown_person},
        )

    frames = sandwich_upgrade(_script)
    _frames_equal(frames)


def test_lido_send_ether_snapshot(
    sandwich_upgrade: SandwichFn,
    eth_whale: Account,
    steth_whale: Account,
):
    def _script():
        el_vault = contracts.execution_layer_rewards_vault
        lido = contracts.lido

        assert lido.balanceOf(eth_whale) == 0
        assert eth_whale.balance() >= _1ETH
        assert el_vault.balance() >= _1ETH

        # send ether to Lido to mint stETH
        lido.submit(
            ZERO_ADDRESS,
            {
                "from": eth_whale,
                "amount": 42,
            },
        )
        lido.submit(
            steth_whale.address,
            {
                "from": eth_whale,
                "amount": 42,
            },
        )

        # toggle contract state to STOPPED
        lido.stop({"from": contracts.voting})

        # toggle contract state to RUNNING
        lido.resume({"from": contracts.voting})

        lido.submit(
            ZERO_ADDRESS,
            {
                "from": eth_whale,
                "amount": 17,
            },
        )

        # receive EL rewards
        lido.receiveELRewards(
            {
                "value": _1ETH - 42,
                "from": el_vault,
            }
        )

        lido.submit(
            steth_whale,
            {
                "from": eth_whale,
                "amount": 13,
            },
        )

    frames = sandwich_upgrade(_script)
    _frames_equal(frames)


def test_lido_dao_ops_snapshot(sandwich_upgrade: SandwichFn):
    def _script():
        el_vault = contracts.execution_layer_rewards_vault
        voting = contracts.voting
        lido = contracts.lido

        assert lido.getCurrentStakeLimit() > 0
        assert lido.isStakingPaused() is False
        assert el_vault.balance() >= _1ETH
        assert lido.isStopped() is False

        lido.pauseStaking({"from": voting})
        lido.stop({"from": voting})
        lido.resumeStaking({"from": voting})
        lido.pauseStaking({"from": voting})
        lido.removeStakingLimit({"from": voting})
        lido.resumeStaking({"from": voting})
        lido.receiveELRewards(
            {
                "from": el_vault,
                "value": _1ETH,
            }
        )
        lido.pauseStaking({"from": voting})
        lido.setStakingLimit(17, 3, {"from": voting})
        lido.resume({"from": voting})
        lido.stop({"from": voting})

    frames = sandwich_upgrade(_script)
    _frames_equal(frames)


@pytest.fixture(scope="module")
def do_snapshot(
    interface,
    unknown_person: Account,
    eth_whale: Account,
    steth_whale: Account,
    some_contract: Account,
):
    lido = contracts.lido

    def _snap():
        block = chain.height
        with brownie.multicall(address="0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696", block_identifier=block):
            return {
                "block_number": chain.height,
                "address": lido.address,
                # AppProxyUpgradeable
                "isDepositable": interface.AppProxyUpgradeable(lido.address).isDepositable(),
                # ERC20
                "name": lido.name(),
                "symbol": lido.symbol(),
                "decimals": lido.decimals(),
                "totalSupply": lido.totalSupply(),
                "balanceOf(eth_whale)": lido.balanceOf(eth_whale),
                "balanceOf(steth_whale)": lido.balanceOf(steth_whale),
                "balanceOf(unknown_person)": lido.balanceOf(unknown_person),
                "allowance(steth_whale,unknown_person)": lido.allowance(steth_whale, unknown_person),
                "allowance(unknown_person,steth_whale)": lido.allowance(unknown_person, steth_whale),
                # Lido
                "sharesOf(eth_whale)": lido.sharesOf(eth_whale),
                "sharesOf(steth_whale)": lido.sharesOf(steth_whale),
                "sharesOf(unknown_person)": lido.sharesOf(unknown_person),
                "getBeaconStat": lido.getBeaconStat(),
                "getBufferedEther": lido.getBufferedEther(),
                "getTotalPooledEther": lido.getTotalPooledEther(),
                "getPooledEthByShares(100)": lido.getPooledEthByShares(100),
                "getCurrentStakeLimit": lido.getCurrentStakeLimit(),
                "getFeeDistribution": lido.getFeeDistribution(),
                "getFee": lido.getFee(),
                "getOracle": lido.getOracle(),
                "getStakeLimitFullInfo": lido.getStakeLimitFullInfo(),
                "getTotalELRewardsCollected": lido.getTotalELRewardsCollected(),
                "getTotalShares": lido.getTotalShares(),
                "getSharesByPooledEth(1 ETH)": lido.getSharesByPooledEth(_1ETH),
                "getTreasury": lido.getTreasury(),
                "getWithdrawalCredentials": lido.getWithdrawalCredentials(),
                "isStakingPaused": lido.isStakingPaused(),
                "isPetrified": lido.isPetrified(),
                "isStopped": lido.isStopped(),
                "allowRecoverability(LDO)": lido.allowRecoverability(ldo_token_address),
                "allowRecoverability(StETH)": lido.allowRecoverability(lido.address),
                "allowRecoverability(SOME_CONTRACT)": lido.allowRecoverability(some_contract),
                # constants
                "PAUSE_ROLE": lido.PAUSE_ROLE(),
                "RESUME_ROLE": lido.RESUME_ROLE(),
                "STAKING_CONTROL_ROLE": lido.STAKING_CONTROL_ROLE(),
                "STAKING_PAUSE_ROLE": lido.STAKING_PAUSE_ROLE(),
                # AragonApp
                "canPerform()": lido.canPerform(lido_dao_voting_address, lido.PAUSE_ROLE(), []),
                "getRecoveryVault": lido.getRecoveryVault(),
                "kernel": lido.kernel(),
                "appId": lido.appId(),
                "getEVMScriptExecutor(nil)": lido.getEVMScriptExecutor(EMPTY_CALLSCRIPT),
                "getEVMScriptRegistry": lido.getEVMScriptRegistry(),
                "getInitializationBlock": lido.getInitializationBlock(),
                "hasInitialized": lido.hasInitialized(),
            }

    return _snap


@pytest.fixture(scope="module")
def far_block() -> int:
    return chain.height + 1_000


@pytest.fixture(scope="module")
def steth_whale(accounts) -> Account:
    return accounts.at(lido_insurance_fund_address, force=True)


@pytest.fixture(scope="module")
def some_contract(accounts) -> Account:
    # Multicall3 contract deployed almost on the every network on the same address
    return accounts.at("0xcA11bde05977b3631167028862bE2a173976CA11", force=True)


@pytest.fixture(scope="module")
def sandwich_upgrade(
    do_snapshot: SnapshotFn,
    far_block: int,
    helpers: Helpers,
) -> Callable[..., tuple[Frame, Frame]]:
    """Snapshot the state before and after the upgrade and return the two frames."""

    def _do(
        action_fn: Callable,
        snapshot_fn=do_snapshot,
        snapshot_block=far_block,
    ):
        with _chain_snapshot():
            _sleep_till_block(snapshot_block)
            v1_snap = _snap_action(action_fn, snapshot_fn)

        start_and_execute_votes(contracts.voting, helpers)
        _sleep_till_block(snapshot_block)

        # do not call _chain_snapshot here to be able to interact with the environment in the test
        v2_snap = _snap_action(action_fn, snapshot_fn)

        # make simple check to make sure we are not comparing the same block snapshots
        assert v1_snap["init"]["block_number"] != v1_snap["post"]["block_number"]
        assert v2_snap["init"]["block_number"] != v2_snap["post"]["block_number"]

        return v1_snap, v2_snap

    return _do


def _sleep_till_block(block: int) -> None:
    curr_block = web3.eth.get_block_number()

    if curr_block > block:
        raise ValueError(f"Current block {curr_block} is greater than the target block {block}")

    print(f"Forwarding chain to block {block}, may take a while...")
    chain.mine(block - curr_block)


@contextmanager
def _chain_snapshot():
    """Custom chain snapshot context manager to avoid moving snapshots pointer."""
    id_ = rpc.snapshot()

    try:
        yield
    finally:
        if not web3.isConnected() or not rpc.is_active():
            return

        block = rpc.revert(id_)
        _notify_registry(block)


def _snap_action(action_fn: Callable, snapshot_fn: Callable[[], dict]) -> Frame:
    """Snapshot the state before and after an action and return the frame."""

    _init = snapshot_fn()

    action_fn()

    _post = snapshot_fn()

    return Frame(init=_init, post=_post)


def _frames_equal(frames: tuple[Frame, Frame], *, skip_keys: list[str] | None = None) -> None:
    """Compare two frames, asserting that they are equal."""

    v1_snap, v2_snap = frames[0].copy(), frames[1].copy()
    skip_keys = skip_keys or []

    for frame in (v1_snap, v2_snap):
        for key in skip_keys:
            frame["init"].pop(key, None)
            frame["post"].pop(key, None)

    assert v2_snap["init"] == v1_snap["init"], "snapshots before action should be equal"
    assert v2_snap["post"] == v1_snap["post"], "snapshots after action should be equal"
