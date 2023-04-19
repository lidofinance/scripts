from contextlib import contextmanager
from typing import Any, Callable, Sequence, TypedDict

from web3 import Web3
import brownie
import pytest
from brownie import Contract, accounts, chain, rpc, web3
from brownie.network.account import Account
from brownie.network.state import _notify_registry
from pytest_check import check
from typing_extensions import Protocol

from tests.conftest import Helpers
from utils.config import contracts
from utils.import_current_votes import start_and_execute_votes


class Frame(TypedDict):
    """A snapshot of the state before and after an action."""

    snap: dict[str, Any]
    func: str


Stack = Sequence[Frame]
SnapshotFn = Callable[[Any], dict]


# Just for better language server support
class SandwichFn(Protocol):
    @staticmethod
    def __call__(
        actions_list: Sequence[Callable],
        snapshot_fn: SnapshotFn = ...,
        snapshot_block: int = ...,
    ) -> tuple[Stack, Stack]:
        ...


def test_dsm_no_changes_in_views(sandwich_upgrade: SandwichFn):
    """Test that no views change during the upgrade process"""

    stacks = sandwich_upgrade([])
    _stacks_equal(stacks)


def test_dsm_no_changes_in_views_with_ops(
    sandwich_upgrade: SandwichFn,
    new_owner: Account,
    some_contract: Account,
    some_eoa: Account,
    guardian: Account,
):
    """Test that no views change during the upgrade process"""

    stacks = sandwich_upgrade(
        (
            pause_deposits,
            lambda dsm: dsm.setOwner(new_owner.address, {"from": dsm.getOwner()}),
            lambda dsm: dsm.setMaxDeposits(42, {"from": new_owner.address}),
            lambda dsm: dsm.setMinDepositBlockDistance(
                17,
                {"from": new_owner.address},
            ),
            lambda dsm: dsm.removeGuardian(
                guardian.address,
                3,
                {"from": new_owner.address},
            ),
            lambda dsm: dsm.addGuardian(
                some_eoa.address,
                4,
                {"from": new_owner.address},
            ),
            lambda dsm: dsm.removeGuardian(
                some_eoa.address,
                3,
                {"from": new_owner.address},
            ),
            lambda dsm: dsm.addGuardians(
                [
                    some_contract.address,
                    some_eoa.address,
                ],
                4,
                {"from": new_owner.address},
            ),
            lambda dsm: dsm.removeGuardian(
                some_contract.address,
                4,
                {"from": new_owner.address},
            ),
            lambda dsm: dsm.setPauseIntentValidityPeriodBlocks(
                42,
                {"from": new_owner.address},
            ),
            lambda dsm: dsm.setGuardianQuorum(0, {"from": new_owner.address}),
            lambda dsm: dsm.setGuardianQuorum(3, {"from": new_owner.address}),
            resume_deposits,
        )
    )
    _stacks_equal(stacks)


def pause_deposits(dsm: Contract):
    if _is_v2(dsm):
        dsm.pauseDeposits(
            chain.height,
            1,  # NOR
            [0, 0],  # skip signature
            {"from": dsm.getGuardians()[0]},
        )
    else:
        dsm.pauseDeposits(
            chain.height,
            [0, 0],  # skip signature
            {"from": dsm.getGuardians()[0]},
        )


def resume_deposits(dsm: Contract):
    if _is_v2(dsm):
        dsm.unpauseDeposits(
            1,  # NOR
            {"from": dsm.getOwner()},
        )
    else:
        dsm.unpauseDeposits(
            {"from": dsm.getOwner()},
        )


@pytest.fixture(scope="module")
def dsm_v1():
    """Deposit Security Module v1"""
    return contracts.deposit_security_module_v1


@pytest.fixture(scope="module")
def dsm_v2():
    """Deposit Security Module v2"""
    return contracts.deposit_security_module


@pytest.fixture(scope="module")
def do_snapshot(guardian: Account, some_eoa: Account):
    """Snapshot function for the Deposit Security Module"""

    def _snap(dsm):
        block = chain.height
        with brownie.multicall(block_identifier=block):
            return {
                "block_number": chain.height,
                "chain_time": web3.eth.get_block(chain.height)["timestamp"],
                "DEPOSIT_CONTRACT": dsm.DEPOSIT_CONTRACT(),
                "LIDO": dsm.LIDO(),
                "getOwner": dsm.getOwner(),
                "getGuardianIndex(positive)": dsm.getGuardianIndex(guardian.address),
                "getGuardianIndex(negative)": dsm.getGuardianIndex(accounts[0].address),
                "getGuardianIndex(changes)": dsm.getGuardianIndex(some_eoa.address),
                "getGuardianQuorum": dsm.getGuardianQuorum(),
                "getGuardians": dsm.getGuardians(),
                "isGuardian(positive)": dsm.isGuardian(guardian.address),
                "isGuardian(negative)": dsm.isGuardian(accounts[0].address),
                "isGuardian(changes)": dsm.isGuardian(some_eoa.address),
                "getMaxDeposits": dsm.getMaxDeposits(),
                "getMinDepositBlockDistance": dsm.getMinDepositBlockDistance(),
                "getPauseIntentValidityPeriodBlocks": dsm.getPauseIntentValidityPeriodBlocks(),
                # NOTE: unchecked views
                # Implementation address changes
                # "address": dsm.address,
                # The following two fields are constant and built differently accross versions
                # "ATTEST_MESSAGE_PREFIX": dsm.ATTEST_MESSAGE_PREFIX(),
                # "PAUSE_MESSAGE_PREFIX": dsm.PAUSE_MESSAGE_PREFIX(),
            }

    return _snap


@pytest.fixture(scope="module")
def guardian(dsm_v1: Contract, accounts) -> Account:
    """Guardian account"""
    return accounts.at(dsm_v1.getGuardians()[1], force=True)


@pytest.fixture(scope="module")
def new_owner(accounts) -> Account:
    """New owner account"""
    return accounts[7]


@pytest.fixture(scope="module")
def some_eoa(accounts) -> Account:
    """Some EOA account"""
    return accounts[8]


@pytest.fixture(scope="module")
def some_contract(accounts) -> Account:
    # Multicall3 contract deployed almost on the every network on the same address
    return accounts.at("0xcA11bde05977b3631167028862bE2a173976CA11", force=True)


@pytest.fixture(scope="module")
def sandwich_upgrade(
    do_snapshot: SnapshotFn,
    dsm_v1: Any,
    dsm_v2: Any,
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
        def _actions_snaps(dsm):
            _sleep_till_block(snapshot_block, far_ts)

            yield Frame(snap=snapshot_fn(dsm), func="init")

            for action_fn in actions_list:
                action_fn(dsm)
                yield Frame(
                    snap=snapshot_fn(dsm),
                    func=repr(action_fn),
                )

        with _chain_snapshot():
            v1_frames = tuple(_actions_snaps(dsm_v1))

        start_and_execute_votes(contracts.voting, helpers)
        # NOTE: grant role to DSM to be able to resume deposits
        contracts.staking_router.grantRole(
            Web3.keccak(text="STAKING_MODULE_RESUME_ROLE"),
            dsm_v2.address,
            {"from": contracts.agent.address},
        )

        # do not call _chain_snapshot here to be able to interact with the environment in the test
        v2_frames = tuple(_actions_snaps(dsm_v2))

        return v1_frames, v2_frames

    return _do


@pytest.fixture(scope="module")
def far_block() -> int:
    return chain.height + 1_000


@pytest.fixture(scope="module")
def far_ts() -> int:
    return chain.time() + 14 * 24 * 60 * 60  # 14 days


def _is_v2(dsm: Contract) -> bool:
    """Check if the DSM contract is a v2 contract"""
    return dsm.address == contracts.deposit_security_module.address


def _sleep_till_block(block: int, ts: int) -> None:
    curr_block = web3.eth.get_block_number()

    if curr_block > block:
        raise ValueError(f"Current block {curr_block} is greater than the target block {block}")

    print(f"Forwarding chain to block {block}, may take a while...")
    chain.mine(block - curr_block, timestamp=ts)


def _stacks_equal(stacks: tuple[Stack, Stack]) -> None:
    """Compare two stacks, asserting that they are equal"""

    for v1_frame, v2_frame in zip(*stacks, strict=True):
        for k in v1_frame["snap"]:
            with check:  # soft asserts
                assert (
                    v1_frame["snap"][k] == v2_frame["snap"][k]
                ), f"Snapshots for key '{k}' after '{v1_frame['func']}' are not equal"


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
