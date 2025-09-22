from typing import Any, Callable, Sequence, TypedDict

from web3 import Web3
import brownie
import pytest
from brownie import Contract, accounts, chain, web3
from brownie.network.account import Account
from pytest_check import almost_equal, check
from typing_extensions import Protocol

from tests.conftest import Helpers
from utils.config import contracts
from utils.test.governance_helpers import execute_vote_and_process_dg_proposals
from utils.test.snapshot_helpers import _chain_snapshot


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
        actions_list: dict[str, Callable],
        snapshot_fn: SnapshotFn = ...,
        snapshot_block: int = ...,
    ) -> tuple[Stack, Stack]:
        ...

@pytest.mark.skip("Skip for now, restore after the TW voting")
def test_dsm_no_changes_in_views(sandwich_upgrade: SandwichFn):
    """Test that no views change during the upgrade process"""

    stacks = sandwich_upgrade({})
    _stacks_equal(stacks)


@pytest.fixture(scope="module")
def guardian(dsm: Contract, accounts) -> Account:
    """Guardian account"""
    return accounts.at(contracts.deposit_security_module.getGuardians()[1], force=True)


@pytest.mark.skip("Skip for now, restore after the TW voting")
def test_dsm_no_changes_in_views_with_ops(
    sandwich_upgrade: SandwichFn,
    new_owner: Account,
    some_contract: Account,
    some_eoa: Account,
    guardian: Account,
):
    """Test that no views change during the upgrade process"""

    stacks = sandwich_upgrade(
        {
            "pauseDeposits": pause_deposits,
            "setOwner": lambda dsm: dsm.setOwner(new_owner.address, {"from": dsm.getOwner()}),
            "removeGuardian(existing)": lambda dsm: dsm.removeGuardian(
                guardian.address,
                3,
                {"from": new_owner.address},
            ),
            "addGuardian(new)": lambda dsm: dsm.addGuardian(
                some_eoa.address,
                4,
                {"from": new_owner.address},
            ),
            "removeGuardian(new)": lambda dsm: dsm.removeGuardian(
                some_eoa.address,
                3,
                {"from": new_owner.address},
            ),
            "addGuardians": lambda dsm: dsm.addGuardians(
                [
                    some_contract.address,
                    some_eoa.address,
                ],
                4,
                {"from": new_owner.address},
            ),
            "removeGuardian(contract)": lambda dsm: dsm.removeGuardian(
                some_contract.address,
                4,
                {"from": new_owner.address},
            ),
            "setPauseIntentValidityPeriodBlocks": lambda dsm: dsm.setPauseIntentValidityPeriodBlocks(
                42,
                {"from": new_owner.address},
            ),
            "setGuardianQuorum(0)": lambda dsm: dsm.setGuardianQuorum(0, {"from": new_owner.address}),
            "setGuardianQuorum(3)": lambda dsm: dsm.setGuardianQuorum(3, {"from": new_owner.address}),
            "unpauseDeposits": resume_deposits,
            "setMaxOperatorsPerUnvetting(42)": lambda dsm: dsm.setMaxOperatorsPerUnvetting(42, {"from": new_owner.address}),

        }
    )
    _stacks_equal(stacks)


def pause_deposits(dsm: Contract):
    dsm.pauseDeposits(
        chain.height,
        [0, 0],  # skip signature
        {"from": dsm.getGuardians()[0]},
    )


def resume_deposits(dsm: Contract):
    dsm.unpauseDeposits(
        {"from": dsm.getOwner()},
    )


@pytest.fixture(scope="module")
def dsm():
    return contracts.deposit_security_module


@pytest.fixture(scope="module")
def do_snapshot(guardian: Account, some_eoa: Account):
    """Snapshot function for the Deposit Security Module"""

    def _snap(dsm):
        block = chain.height
        with brownie.multicall(block_identifier=block):
            return {
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
                "getPauseIntentValidityPeriodBlocks": dsm.getPauseIntentValidityPeriodBlocks(),
                "getMaxOperatorsPerUnvetting": dsm.getMaxOperatorsPerUnvetting(),
                "getLastDepositBlock": dsm.getLastDepositBlock(),
                "isDepositsPaused": dsm.isDepositsPaused(),
                # NOTE: unchecked views
                # Implementation address changes
                # "address": dsm.address,
                # The following two fields are constant and built differently across versions
                # "ATTEST_MESSAGE_PREFIX": dsm.ATTEST_MESSAGE_PREFIX(),
                # "PAUSE_MESSAGE_PREFIX": dsm.PAUSE_MESSAGE_PREFIX(),
            }

    return _snap


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
    dsm: Any,
    far_block: int,
    far_ts: int,
    helpers: Helpers,
    vote_ids_from_env: Any,
    dg_proposal_ids_from_env: Any,
) -> SandwichFn:
    """Snapshot the state before and after the upgrade and return the two frames"""

    def _do(
        actions_list: dict[str, Callable],
        snapshot_fn=do_snapshot,
        snapshot_block=far_block,
    ):
        def _actions_snaps(dsm):
            _sleep_till_block(snapshot_block, far_ts)

            yield Frame(snap=snapshot_fn(dsm), func="init")

            for desc, action_fn in actions_list.items():
                action_fn(dsm)
                yield Frame(
                    snap=snapshot_fn(dsm),
                    func=desc,
                )

        with _chain_snapshot():
            v1_frames = tuple(_actions_snaps(dsm))

        execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, dg_proposal_ids_from_env)

        # do not call _chain_snapshot here to be able to interact with the environment in the test
        v2_frames = tuple(_actions_snaps(dsm))

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
    chain.sleep(ts - chain.time())
    chain.mine(block - curr_block)


def _stacks_equal(stacks: tuple[Stack, Stack]) -> None:
    """Compare two stacks, asserting that they are equal"""

    for v1_frame, v2_frame in zip(*stacks, strict=True):
        for k in v1_frame["snap"]:
            with check:  # soft asserts
                if k == "chain_time":
                    almost_equal(
                        v1_frame["snap"][k],
                        v2_frame["snap"][k],
                        1,  # 1 second tolerance
                        msg=f"Large chain time difference after '{v1_frame['func']}'",
                    )
                    continue

                assert (
                    v1_frame["snap"][k] == v2_frame["snap"][k]
                ), f"Snapshots for key '{k}' after '{v1_frame['func']}' are not equal"
