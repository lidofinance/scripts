from contextlib import contextmanager
from typing import Any, Callable, Sequence, TypedDict

import pytest
from brownie import Contract, chain, web3, accounts
from hexbytes import HexBytes
from pytest_check import check
from typing_extensions import Protocol
from web3 import Web3

from tests.conftest import Helpers
from utils.config import contracts
from utils.test.governance_helpers import execute_vote_and_process_dg_proposals
from utils.test.snapshot_helpers import _chain_snapshot

from .utils import get_slot

SLOTS_COUNT_TO_CHECK = 16
MAX_ARRAY_SIZE = 2 ** 5


class Frame(TypedDict):
    """A snapshot of the state before and after an action."""

    snap: dict[str, Any]
    func: str


Stack = Sequence[Frame]
SnapshotFn = Callable[[], dict]


class SandwichFn(Protocol):
    @staticmethod
    def __call__(
        snapshot_fn: SnapshotFn = ...,
        snapshot_block: int = ...,
    ) -> tuple[Stack, Stack]: ...


def test_first_slots(sandwich_upgrade: SandwichFn):
    """Test that first slots has not been changed in contracts"""

    stacks = sandwich_upgrade()
    _stacks_equal(stacks)


@pytest.fixture(scope="module")
def skip_slots() -> Sequence[tuple[str, int]]:
    """Slots that are not checked for equality"""
    return [
        # reset slot in kernel
        (contracts.kernel.address, 0x01),
    ]


@pytest.fixture(scope="module")
def do_snapshot(skip_slots: Sequence[tuple[str, int]]) -> SnapshotFn:
    def _get_slots(contract: Contract, block: int) -> dict:
        res = {}

        for slot in range(0, SLOTS_COUNT_TO_CHECK):
            if (contract.address, slot) in skip_slots:
                continue

            slot_in_hex = HexBytes(slot).hex()
            # try plain 32 bits value first
            slot_value = get_slot(
                Web3.to_checksum_address(contract.address),
                pos=slot,
                block=block,
            )
            res[f"{contract.address}_slot_{slot_in_hex}"] = slot_value

            # if the slot stores relatively small integer, try to read as an array
            int_value = Web3.to_int(slot_value)
            if 0 < int_value < MAX_ARRAY_SIZE:
                slot_value_as_list = get_slot(
                    Web3.to_checksum_address(contract.address),
                    pos=slot,
                    as_list=True,
                    block=block,
                )
                res[f"{contract.address}_slot_{slot_in_hex}_as_list"] = slot_value_as_list

        return res

    def _snap():
        block = chain.height
        res = {}

        for contract in (
            contracts.lido,
            contracts.node_operators_registry,
            contracts.deposit_security_module,
            contracts.execution_layer_rewards_vault,
            contracts.withdrawal_vault,
            contracts.oracle_daemon_config,
            contracts.burner,
            contracts.relay_allowed_list,
            contracts.ldo_token,
            contracts.token_manager,
            contracts.finance,
            contracts.acl,
            contracts.agent,
            contracts.kernel,
            contracts.easy_track,
            contracts.wsteth,
            contracts.csm,
            contracts.cs_accounting,
            contracts.cs_fee_distributor,
            contracts.cs_fee_oracle,
            contracts.csm_hash_consensus,
            contracts.cs_verifier,
        ):
            res |= _get_slots(contract, block)

        return res

    return _snap


@pytest.fixture(scope="module")
def sandwich_upgrade(
    do_snapshot: SnapshotFn,
    far_block: int,
    far_ts: int,
    helpers: Helpers,
    vote_ids_from_env: int,
    dg_proposal_ids_from_env: int,
) -> SandwichFn:
    """Snapshot the state before and after the upgrade and return the two frames"""

    def _do(snapshot_fn=do_snapshot, snapshot_block=far_block):
        def _actions_snaps():
            _sleep_till_block(snapshot_block, far_ts)
            yield Frame(snap=snapshot_fn(), func="init")

        with _chain_snapshot():
            v1_frames = tuple(_actions_snaps())

        execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, dg_proposal_ids_from_env)

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
        for k in v1_frame["snap"]:
            with check:
                assert v1_frame["snap"][k] == v2_frame["snap"][k], f"Values for {k} are not equal"
