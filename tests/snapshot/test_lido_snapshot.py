
from functools import partial as _call
from typing import Any, Callable, Sequence, TypedDict

import brownie
import pytest
from brownie import ZERO_ADDRESS, chain, web3, accounts
from brownie.network.account import Account
from pytest_check import check
from web3.types import Wei

from tests.conftest import Helpers
from utils.config import contracts, LDO_TOKEN, VOTING
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
SandwichFn = Callable[..., tuple[Stack, Stack]]


UINT256_MAX = 2**256 - 1
_1ETH = Wei(10**18)


def test_lido_no_changes_in_views(sandwich_upgrade: SandwichFn):
    """Test that no views change during the upgrade process."""

    stacks = sandwich_upgrade(
        (lambda: chain.mine(),),  # just upgrade and move forward
    )
    _stacks_equal(stacks)


def test_lido_end_user_snapshot(
    sandwich_upgrade: SandwichFn,
    eth_whale: Account,
    some_contract: Account,
    stranger: Account,
):
    lido = contracts.lido

    eth_amount = Wei(_1ETH - 42)
    assert eth_whale.balance() >= eth_amount
    assert lido.balanceOf(eth_whale) == 0

    actions = (
        # send ether to Lido to mint stETH
        _call(
            web3.eth.send_transaction,
            {
                "from": eth_whale.address,
                "to": lido.address,
                "value": Wei(eth_amount // 2),
            },
        ),
        _call(
            lido.submit,
            ZERO_ADDRESS,
            {
                "from": eth_whale,
                "amount": Wei(eth_amount // 2),
            },
        ),
        # play with allowance
        _call(
            lido.approve,
            some_contract,
            UINT256_MAX,
            {"from": eth_whale},
        ),
        _call(
            lido.decreaseAllowance,
            some_contract,
            13,
            {"from": eth_whale},
        ),
        _call(
            lido.increaseAllowance,
            some_contract,
            13,
            {"from": eth_whale},
        ),
        _call(
            lido.approve,
            some_contract,
            42,
            {"from": eth_whale},
        ),
        # send funds by different mechanisms
        _call(
            lido.transferFrom,
            eth_whale,
            some_contract.address,
            42,
            {"from": some_contract},
        ),
        _call(
            lido.transfer,
            stranger,
            17,
            {"from": eth_whale},
        ),
        _call(
            lido.transferShares,
            stranger,
            23,
            {"from": some_contract},
        ),
        # revoke allowance
        _call(
            lido.approve,
            some_contract,
            0,
            {"from": eth_whale},
        ),
        # split funds accross accounts
        _call(
            lido.transfer,
            eth_whale,
            11,
            {"from": stranger},
        ),
        _call(
            lido.transfer,
            some_contract,
            13,
            {"from": stranger},
        ),
    )

    stacks = sandwich_upgrade(actions)
    _stacks_equal(stacks)


def test_lido_send_ether_snapshot(
    sandwich_upgrade: SandwichFn,
    eth_whale: Account,
    steth_whale: Account,
):
    el_vault = contracts.execution_layer_rewards_vault
    lido = contracts.lido

    assert lido.balanceOf(eth_whale) == 0
    assert eth_whale.balance() >= _1ETH
    assert el_vault.balance() >= _1ETH

    actions = (
        # send ether to Lido to mint stETH
        _call(
            lido.submit,
            ZERO_ADDRESS,
            {
                "from": eth_whale,
                "amount": 42,
            },
        ),
        _call(
            lido.submit,
            steth_whale.address,
            {
                "from": eth_whale,
                "amount": 42,
            },
        ),
        # toggle contract state to STOPPED
        _call(
            lido.stop,
            {"from": contracts.voting},
        ),
        # toggle contract state to RUNNING
        _call(
            lido.resume,
            {"from": contracts.voting},
        ),
        _call(
            lido.submit,
            ZERO_ADDRESS,
            {
                "from": eth_whale,
                "amount": 17,
            },
        ),
        # receive EL rewards
        _call(
            lido.receiveELRewards,
            {
                "value": _1ETH - 42,
                "from": el_vault,
            },
        ),
        _call(
            lido.submit,
            steth_whale,
            {
                "from": eth_whale,
                "amount": 13,
            },
        ),
    )

    stacks = sandwich_upgrade(actions)
    _stacks_equal(stacks)


def test_lido_dao_ops_snapshot(sandwich_upgrade: SandwichFn):
    el_vault = contracts.execution_layer_rewards_vault
    voting = contracts.voting
    lido = contracts.lido

    assert lido.getCurrentStakeLimit() > 0
    assert lido.isStakingPaused() is False
    assert el_vault.balance() >= _1ETH
    assert lido.isStopped() is False

    actions = (
        _call(lido.pauseStaking, {"from": voting}),
        _call(lido.stop, {"from": voting}),
        _call(lido.resumeStaking, {"from": voting}),
        _call(lido.pauseStaking, {"from": voting}),
        _call(lido.removeStakingLimit, {"from": voting}),
        _call(lido.resumeStaking, {"from": voting}),
        _call(
            lido.receiveELRewards,
            {
                "from": el_vault,
                "value": _1ETH,
            },
        ),
        _call(lido.pauseStaking, {"from": voting}),
        _call(lido.setStakingLimit, 17, 3, {"from": voting}),
        _call(lido.resume, {"from": voting}),
        _call(lido.stop, {"from": voting}),
    )

    stacks = sandwich_upgrade(actions)
    _stacks_equal(stacks)


@pytest.fixture(scope="function")
def do_snapshot(
    interface,
    stranger: Account,
    eth_whale: Account,
    steth_whale: Account,
    some_contract: Account,
):
    lido = contracts.lido

    def _snap():
        block = chain.height
        res = {}

        with brownie.multicall(block_identifier=block):
            res |= {
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
                "balanceOf(stranger)": lido.balanceOf(stranger),
                "allowance(steth_whale,stranger)": lido.allowance(steth_whale, stranger),
                "allowance(stranger,steth_whale)": lido.allowance(stranger, steth_whale),
                # Lido
                "sharesOf(eth_whale)": lido.sharesOf(eth_whale),
                "sharesOf(steth_whale)": lido.sharesOf(steth_whale),
                "sharesOf(stranger)": lido.sharesOf(stranger),
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
                "allowRecoverability(LDO)": lido.allowRecoverability(LDO_TOKEN),
                "allowRecoverability(StETH)": lido.allowRecoverability(lido.address),
                "allowRecoverability(SOME_CONTRACT)": lido.allowRecoverability(some_contract),
                # constants
                "PAUSE_ROLE": lido.PAUSE_ROLE(),
                "RESUME_ROLE": lido.RESUME_ROLE(),
                "STAKING_CONTROL_ROLE": lido.STAKING_CONTROL_ROLE(),
                "STAKING_PAUSE_ROLE": lido.STAKING_PAUSE_ROLE(),
                # AragonApp
                "canPerform()": lido.canPerform(VOTING, lido.PAUSE_ROLE(), []),
                "getRecoveryVault": lido.getRecoveryVault(),
                "kernel": lido.kernel(),
                "appId": lido.appId(),
                "getEVMScriptExecutor(nil)": lido.getEVMScriptExecutor(EMPTY_CALLSCRIPT),
                "getEVMScriptRegistry": lido.getEVMScriptRegistry(),
                "getInitializationBlock": lido.getInitializationBlock(),
                "hasInitialized": lido.hasInitialized(),
            }

        for v1_slot in (
            # Lido.sol
            "lido.Lido.beaconBalance",
            "lido.Lido.beaconValidators",
            "lido.Lido.bufferedEther",
            "lido.Lido.depositContract",
            "lido.Lido.depositedValidators",
            "lido.Lido.ELRewardsWithdrawalLimit",
            "lido.Lido.executionLayerRewardsVault",
            "lido.Lido.fee",
            "lido.Lido.insuranceFee",
            "lido.Lido.insuranceFund",
            "lido.Lido.nodeOperatorsFee",
            "lido.Lido.nodeOperatorsRegistry",
            "lido.Lido.oracle",
            "lido.Lido.stakeLimit",
            "lido.Lido.totalELRewardsCollected",
            "lido.Lido.treasury",
            "lido.Lido.treasuryFee",
            "lido.Lido.withdrawalCredentials",
            # StETH.sol
            "lido.StETH.totalShares",
            # Pausable.sol
            "lido.Pausable.activeFlag",
            # AragonApp.sol
            "aragonOS.appStorage.kernel",
            "aragonOS.appStorage.appId",
        ):
            res[v1_slot] = get_slot(
                lido.address,
                name=v1_slot,
                block=block,
            )

        return res

    return _snap


@pytest.fixture(scope="module")
def far_block() -> int:
    return chain.height + 1_000


@pytest.fixture(scope="module")
def some_contract(accounts) -> Account:
    some_contract_addr = "0xcA11bde05977b3631167028862bE2a173976CA11"
    # Multicall3 contract deployed almost on the every network on the same address
    return accounts.at(some_contract_addr, force=True)


@pytest.fixture(scope="function")
def sandwich_upgrade(
    do_snapshot: SnapshotFn,
    far_block: int,
    helpers: Helpers,
    vote_ids_from_env,
) -> Callable[..., tuple[Stack, Stack]]:
    """Snapshot the state before and after the upgrade and return the two frames"""

    def _do(
        actions_list: Sequence[Callable],
        snapshot_fn=do_snapshot,
        snapshot_block=far_block,
    ):
        def _actions_snaps():
            _sleep_till_block(snapshot_block)

            yield Frame(snap=snapshot_fn(), func="init")

            for action_fn in actions_list:
                action_fn()
                yield Frame(
                    snap=snapshot_fn(),
                    func=repr(action_fn),
                )

        with _chain_snapshot():
            v1_frames = tuple(_actions_snaps())

        if vote_ids_from_env:
            helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting, topup="0.5 ether")
        else:
            start_and_execute_votes(contracts.voting, helpers)

        # do not call _chain_snapshot here to be able to interact with the environment in the test
        v2_frames = tuple(_actions_snaps())

        return v1_frames, v2_frames

    return _do


def _sleep_till_block(block: int) -> None:
    curr_block = web3.eth.get_block_number()

    if curr_block > block:
        raise ValueError(f"Current block {curr_block} is greater than the target block {block}")

    print(f"Forwarding chain to block {block}, may take a while...")
    chain.mine(block - curr_block)


def _stacks_equal(stacks: tuple[Stack, Stack]) -> None:
    """Compare two stacks, asserting that they are equal"""

    for v1_frame, v2_frame in zip(*stacks, strict=True):
        with check:  # soft asserts
            assert v1_frame["snap"] == v2_frame["snap"], f"Snapshots after {v1_frame['func']} are not equal"
