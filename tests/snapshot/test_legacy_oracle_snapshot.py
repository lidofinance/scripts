from contextlib import contextmanager
from typing import Any, Callable, Sequence, TypedDict

import brownie
import pytest
from brownie import chain, rpc, web3
from brownie.network.account import Account
from brownie.network.state import _notify_registry
from pytest_check import check
from typing_extensions import Protocol

from tests.conftest import Helpers
from utils.config import contracts, ldo_token_address
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.import_current_votes import start_and_execute_votes


class Frame(TypedDict):
    """A snapshot of the state before and after an action."""

    snap: dict[str, Any]
    func: str


Stack = Sequence[Frame]
SnapshotFn = Callable[[], dict]


class SandwichFn(Protocol):
    @staticmethod
    def __call__(
        actions_list: Sequence[Callable],
        snapshot_fn: SnapshotFn = ...,
        snapshot_block: int = ...,
    ) -> tuple[Stack, Stack]:
        ...


def test_legacy_oracle_no_changes_in_views(sandwich_upgrade: SandwichFn):
    """Test that no views change during the upgrade process"""

    stacks = sandwich_upgrade([])
    _stacks_equal(stacks)


@pytest.fixture(scope="module")
def do_snapshot(
    interface,
    some_contract: Account,
):
    oracle = contracts.legacy_oracle

    def _snap():
        block = chain.height
        with brownie.multicall(block_identifier=block):
            return {
                "block_number": chain.height,
                "chain_time": web3.eth.get_block(chain.height)["timestamp"],
                "address": oracle.address,
                # AppProxyUpgradeable
                "isDepositable": interface.AppProxyUpgradeable(oracle.address).isDepositable(),
                # Oracle
                "allowRecoverability(LDO)": oracle.allowRecoverability(ldo_token_address),
                "allowRecoverability(SOME_CONTRACT)": oracle.allowRecoverability(some_contract),
                "getBeaconSpec": oracle.getBeaconSpec(),
                "getCurrentEpochId": oracle.getCurrentEpochId(),
                "getCurrentFrame": oracle.getCurrentFrame(),
                "getLastCompletedEpochId": oracle.getLastCompletedEpochId(),
                "getLastCompletedReportDelta": oracle.getLastCompletedReportDelta(),
                "getLido": oracle.getLido(),
                # AragonApp
                "getRecoveryVault": oracle.getRecoveryVault(),
                "kernel": oracle.kernel(),
                "appId": oracle.appId(),
                "getEVMScriptExecutor(nil)": oracle.getEVMScriptExecutor(EMPTY_CALLSCRIPT),
                "getEVMScriptRegistry": oracle.getEVMScriptRegistry(),
                "getInitializationBlock": oracle.getInitializationBlock(),
                "hasInitialized": oracle.hasInitialized(),
            }

    return _snap


@pytest.fixture(scope="module")
def some_contract(accounts) -> Account:
    # Multicall3 contract deployed almost on the every network on the same address
    return accounts.at("0xcA11bde05977b3631167028862bE2a173976CA11", force=True)


@pytest.fixture(scope="module")
def sandwich_upgrade(
    do_snapshot: SnapshotFn,
    far_block: int,
    far_ts: int,
    helpers: Helpers,
) -> SandwichFn:
    """Snapshot the state before and after the upgrade and return the two frames"""

    def _do(
        actions_list: Sequence[Callable],
        snapshot_fn=do_snapshot,
        snapshot_block=far_block,
    ):
        def _actions_snaps():
            _sleep_till_block(snapshot_block, far_ts)

            yield Frame(snap=snapshot_fn(), func="init")

            for action_fn in actions_list:
                action_fn()
                yield Frame(
                    snap=snapshot_fn(),
                    func=repr(action_fn),
                )

        with _chain_snapshot():
            v1_frames = tuple(_actions_snaps())

        start_and_execute_votes(contracts.voting, helpers)

        # do not call _chain_snapshot here to be able to interact with the environment in the test
        v2_frames = tuple(_actions_snaps())

        return v1_frames, v2_frames

    return _do


@pytest.fixture(scope="module")
def far_block() -> int:
    return chain.height + 1_000


@pytest.fixture(scope="module")
def far_ts() -> int:
    return chain.time() + 14 * 24 * 60 * 60  # 14 days


def _sleep_till_block(block: int, ts: int) -> None:
    curr_block = web3.eth.get_block_number()

    if curr_block > block:
        raise ValueError(f"Current block {curr_block} is greater than the target block {block}")

    print(f"Forwarding chain to block {block}, may take a while...")
    chain.mine(block - curr_block, timestamp=ts)


def _stacks_equal(stacks: tuple[Stack, Stack]) -> None:
    """Compare two stacks, asserting that they are equal"""

    for v1_frame, v2_frame in zip(*stacks, strict=True):
        with check:  # soft asserts
            assert v1_frame["snap"] == v2_frame["snap"], f"Snapshots after {v1_frame['func']} are not equal"


@contextmanager
def _chain_snapshot():
    """Custom chain snapshot context manager to avoid moving snapshots pointer"""
    id_ = rpc.snapshot()

    try:
        yield
    finally:
        if not web3.isConnected() or not rpc.is_active():
            return

        block = rpc.revert(id_)
        _notify_registry(block)
