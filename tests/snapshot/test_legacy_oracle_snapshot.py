from contextlib import contextmanager
from typing import Any, Callable, Sequence, TypedDict

import brownie
import pytest
from brownie import chain, web3, accounts
from brownie.network.account import Account
from pytest_check import check
from typing_extensions import Protocol

from tests.conftest import Helpers
from utils.config import contracts, LDO_TOKEN
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.import_current_votes import start_and_execute_votes, is_there_any_vote_scripts
from utils.test.snapshot_helpers import _chain_snapshot

from .utils import get_slot


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
        res = {}

        with brownie.multicall(block_identifier=block):
            res |= {
                "block_number": chain.height,
                "chain_time": web3.eth.get_block(chain.height)["timestamp"],
                "address": oracle.address,
                # AppProxyUpgradeable
                "isDepositable": interface.AppProxyUpgradeable(oracle.address).isDepositable(),
                # Oracle
                "allowRecoverability(LDO)": oracle.allowRecoverability(LDO_TOKEN),
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

        for v1_slot in (
            # LidoOracle.sol
            "lido.LidoOracle.allowedBeaconBalanceAnnualRelativeIncrease",
            "lido.LidoOracle.allowedBeaconBalanceDecrease",
            "lido.LidoOracle.beaconReportReceiver",
            "lido.LidoOracle.beaconSpec",
            "lido.LidoOracle.expectedEpochId",
            "lido.LidoOracle.lastCompletedEpochId",
            "lido.LidoOracle.lastReportedEpochId",
            "lido.LidoOracle.lido",
            "lido.LidoOracle.postCompletedTotalPooledEther",
            "lido.LidoOracle.preCompletedTotalPooledEther",
            "lido.LidoOracle.quorum",
            "lido.LidoOracle.reportsBitMask",
            "lido.LidoOracle.timeElapsed",
            # AragonApp.sol
            "aragonOS.appStorage.kernel",
            "aragonOS.appStorage.appId",
        ):
            res[v1_slot] = get_slot(
                oracle.address,
                name=v1_slot,
                block=block,
            )

        res["members"] = get_slot(
            oracle.address,
            pos=0,
            as_list=True,
            block=block,
        )

        return res

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
    vote_ids_from_env: Any,
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
            before = tuple(_actions_snaps())

        if vote_ids_from_env:
            helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting, topup="0.5 ether")
        else:
            start_and_execute_votes(contracts.voting, helpers)

        # do not call _chain_snapshot here to be able to interact with the environment in the test
        after = tuple(_actions_snaps())

        return before, after

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
