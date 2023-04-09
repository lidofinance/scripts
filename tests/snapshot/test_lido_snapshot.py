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


def test_lido_send_ether_snapshot(
    sandwich_upgrade: SandwichFn,
    eth_whale: Account,
):
    assert eth_whale.balance() >= _1ETH
    assert contracts.lido.balanceOf(eth_whale) == 0

    frames = sandwich_upgrade(
        lambda: web3.eth.send_transaction(
            {
                "to": contracts.lido.address,
                "from": eth_whale.address,
                "value": _1ETH,
            }
        ),
    )

    assert contracts.lido.balanceOf(eth_whale) > 0

    _frames_equal(frames)


def test_lido_submit_snapshot(
    sandwich_upgrade: SandwichFn,
    staker: Account,
):
    assert staker.balance() >= _1ETH
    assert contracts.lido.balanceOf(staker) == 0

    frames = sandwich_upgrade(
        lambda: contracts.lido.submit(
            ZERO_ADDRESS,
            {
                "from": staker,
                "amount": _1ETH,
            },
        ),
    )

    assert contracts.lido.balanceOf(staker) > 0

    _frames_equal(frames)


def test_lido_appove_snapshot(
    sandwich_upgrade: SandwichFn,
    unknown_person: Account,
    eth_whale: Account,
):
    frames = sandwich_upgrade(
        lambda: contracts.lido.approve(
            unknown_person,
            _1ETH,
            {"from": eth_whale},
        ),
    )

    _frames_equal(frames)


def test_lido_increase_allowance(
    sandwich_upgrade: SandwichFn,
    unknown_person: Account,
    steth_whale: Account,
):
    frames = sandwich_upgrade(
        lambda: contracts.lido.increaseAllowance(
            unknown_person,
            _1ETH,
            {"from": steth_whale},
        ),
    )

    _frames_equal(frames)


def test_lido_decrease_allowance(
    sandwich_upgrade: SandwichFn,
    unknown_person: Account,
    steth_whale: Account,
):
    contracts.lido.approve(unknown_person, _1ETH, {"from": steth_whale})

    frames = sandwich_upgrade(
        lambda: contracts.lido.decreaseAllowance(
            unknown_person,
            _1ETH - 1,
            {"from": steth_whale},
        ),
    )

    _frames_equal(frames)


def test_lido_transfer_snapshot(
    sandwich_upgrade: SandwichFn,
    unknown_person: Account,
    steth_whale: Account,
):
    frames = sandwich_upgrade(
        lambda: contracts.lido.transfer(
            unknown_person,
            100,
            {"from": steth_whale},
        ),
    )

    _frames_equal(frames)


def test_lido_transfer_from_snapshot(
    sandwich_upgrade: SandwichFn,
    unknown_person: Account,
    steth_whale: Account,
):
    contracts.lido.approve(unknown_person, _1ETH, {"from": steth_whale})

    frames = sandwich_upgrade(
        lambda: contracts.lido.transferFrom(
            steth_whale,
            unknown_person,
            _1ETH - 1,
            {"from": unknown_person},
        ),
    )

    _frames_equal(frames)


def test_lido_transfer_shares_snapshot(
    sandwich_upgrade: SandwichFn,
    unknown_person: Account,
    steth_whale: Account,
):
    frames = sandwich_upgrade(
        lambda: contracts.lido.transferShares(
            unknown_person,
            100,
            {"from": steth_whale},
        ),
    )

    _frames_equal(frames)


def test_lido_pause_staking_snapshot(sandwich_upgrade: SandwichFn):
    frames = sandwich_upgrade(
        lambda: contracts.lido.pauseStaking(
            {"from": contracts.voting.address},
        ),
    )

    assert contracts.lido.isStakingPaused() is True

    _frames_equal(frames)


@pytest.mark.parametrize("value", [0, 1, 58992, _1ETH])
def test_lido_receive_el_rewards_snapshot(
    sandwich_upgrade: SandwichFn,
    value: int,
):
    assert contracts.execution_layer_rewards_vault.balance() >= _1ETH
    init_el_rewards = contracts.lido.getTotalELRewardsCollected()

    frames = sandwich_upgrade(
        lambda: contracts.lido.receiveELRewards(
            {
                "from": contracts.execution_layer_rewards_vault.address,
                "value": value,
            }
        ),
    )

    assert contracts.lido.getTotalELRewardsCollected() - init_el_rewards == value

    _frames_equal(frames)


def test_lido_set_staking_limit_snapshot(sandwich_upgrade: SandwichFn):
    frames = sandwich_upgrade(
        lambda: contracts.lido.setStakingLimit(
            17,
            3,
            {"from": contracts.voting.address},
        ),
    )

    assert contracts.lido.getCurrentStakeLimit() == 17

    _frames_equal(frames)


def test_lido_remove_staking_limit(sandwich_upgrade: SandwichFn):
    assert contracts.lido.getCurrentStakeLimit() > 0

    frames = sandwich_upgrade(
        lambda: contracts.lido.removeStakingLimit({"from": contracts.voting.address}),
    )

    assert contracts.lido.getCurrentStakeLimit() == UINT256_MAX

    _frames_equal(frames)


def test_lido_resume_snapshot(sandwich_upgrade: SandwichFn):
    contracts.lido.stop({"from": contracts.voting.address})
    assert contracts.lido.isStopped() is True

    frames = sandwich_upgrade(
        lambda: contracts.lido.resume(
            {"from": contracts.voting.address},
        ),
    )

    assert contracts.lido.isStopped() is False

    _frames_equal(frames)


def test_lido_resume_staking_snapshot(sandwich_upgrade: SandwichFn):
    contracts.lido.pauseStaking({"from": contracts.voting.address})
    assert contracts.lido.isStakingPaused() is True

    frames = sandwich_upgrade(
        lambda: contracts.lido.resumeStaking(
            {"from": contracts.voting.address},
        ),
    )

    assert contracts.lido.isStakingPaused() is False

    _frames_equal(frames)


def test_lido_stop_snapshot(sandwich_upgrade: SandwichFn):
    assert contracts.lido.isStopped() is False

    frames = sandwich_upgrade(
        lambda: contracts.lido.stop(
            {"from": contracts.voting.address},
        ),
    )

    assert contracts.lido.isStopped() is True

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
        with brownie.multicall(block_identifier=block):
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
def staker(accounts) -> Account:
    return accounts[0]


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
