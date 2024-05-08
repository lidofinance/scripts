from enum import IntEnum

import brownie
import pytest
from brownie import ZERO_ADDRESS, web3, chain, Contract

from utils.config import contracts
from utils.evm_script import encode_error
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes
from utils.test.oracle_report_helpers import oracle_report, prepare_exit_bus_report
from utils.test.helpers import almostEqEth, almostEqWithDiff

DEPOSIT_AMOUNT = 100 * 10**18


@pytest.fixture()
def stopped_lido():
    contracts.lido.stop({"from": contracts.voting})


@pytest.fixture(scope="module")
def burner() -> Contract:
    return contracts.burner


@pytest.fixture(scope="function", autouse=is_there_any_vote_scripts())
def autoexecute_vote(helpers, vote_ids_from_env, accounts):
    if vote_ids_from_env:
        helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting, topup="0.5 ether")
    else:
        start_and_execute_votes(contracts.voting, helpers)


class StakingModuleStatus(IntEnum):
    Active = 0
    DepositsPaused = 1
    Stopped = 2


class TestEventsEmitted:
    def test_stop_resume_lido_emit_events(self, helpers):
        tx = contracts.lido.stop({"from": contracts.voting})
        helpers.assert_single_event_named("Stopped", tx, {})
        helpers.assert_single_event_named("StakingPaused", tx, {})
        assert contracts.lido.isStopped()
        assert contracts.lido.isStakingPaused()

        tx = contracts.lido.resume({"from": contracts.voting})
        helpers.assert_single_event_named("Resumed", tx, {})

        assert not contracts.lido.isStopped()
        assert not contracts.lido.isStakingPaused()

    def test_stop_resume_staking_lido_emit_events(self, helpers):
        tx = contracts.lido.pauseStaking({"from": contracts.voting})
        helpers.assert_single_event_named("StakingPaused", tx, {})
        helpers.assert_event_not_emitted("Stopped", tx)

        assert contracts.lido.isStakingPaused()
        assert not contracts.lido.isStopped()

        tx = contracts.lido.resumeStaking({"from": contracts.voting})
        helpers.assert_single_event_named("StakingResumed", tx, {})
        helpers.assert_event_not_emitted("Resumed", tx)

        assert not contracts.lido.isStakingPaused()
        assert not contracts.lido.isStopped()

    def test_pause_resume_deposits_staking_module(self, helpers, stranger):
        tx = contracts.staking_router.pauseStakingModule(1, {"from": contracts.deposit_security_module})
        helpers.assert_single_event_named(
            "StakingModuleStatusSet",
            tx,
            {
                "setBy": contracts.deposit_security_module,
                "stakingModuleId": 1,
                "status": StakingModuleStatus.DepositsPaused,
            },
        )
        assert contracts.staking_router.getStakingModuleIsDepositsPaused(1)

        contracts.staking_router.grantRole(
            web3.keccak(text="STAKING_MODULE_RESUME_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        tx = contracts.staking_router.resumeStakingModule(1, {"from": stranger})
        helpers.assert_single_event_named(
            "StakingModuleStatusSet",
            tx,
            {"setBy": stranger, "stakingModuleId": 1, "status": StakingModuleStatus.Active},
        )
        assert contracts.staking_router.getStakingModuleIsActive(1)

    def test_stop_staking_module(self, helpers, stranger):
        contracts.staking_router.grantRole(
            web3.keccak(text="STAKING_MODULE_MANAGE_ROLE"),
            stranger,
            {"from": contracts.agent},
        )

        tx = contracts.staking_router.setStakingModuleStatus(1, StakingModuleStatus.Stopped, {"from": stranger})
        helpers.assert_single_event_named(
            "StakingModuleStatusSet",
            tx,
            {"setBy": stranger, "stakingModuleId": 1, "status": StakingModuleStatus.Stopped},
        )

        assert contracts.staking_router.getStakingModuleIsStopped(1)

    def test_pause_resume_withdrawal_queue(self, helpers, stranger):
        inf = contracts.withdrawal_queue.PAUSE_INFINITELY()
        contracts.withdrawal_queue.grantRole(
            web3.keccak(text="PAUSE_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        tx = contracts.withdrawal_queue.pauseFor(inf, {"from": stranger})
        helpers.assert_single_event_named("Paused", tx, {"duration": inf})
        assert contracts.withdrawal_queue.isPaused()

        contracts.withdrawal_queue.grantRole(
            web3.keccak(text="RESUME_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        tx = contracts.withdrawal_queue.resume({"from": stranger})
        helpers.assert_single_event_named("Resumed", tx, {})
        assert not contracts.withdrawal_queue.isPaused()

    def test_pause_resume_validators_exit_bus(self, helpers, stranger):
        inf = contracts.validators_exit_bus_oracle.PAUSE_INFINITELY()
        contracts.validators_exit_bus_oracle.grantRole(
            web3.keccak(text="PAUSE_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        tx = contracts.validators_exit_bus_oracle.pauseFor(inf, {"from": stranger})
        helpers.assert_single_event_named("Paused", tx, {"duration": inf})
        assert contracts.validators_exit_bus_oracle.isPaused()

        contracts.validators_exit_bus_oracle.grantRole(
            web3.keccak(text="RESUME_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        tx = contracts.validators_exit_bus_oracle.resume({"from": stranger})
        helpers.assert_single_event_named("Resumed", tx, {})
        assert not contracts.validators_exit_bus_oracle.isPaused()


class TestRevertedSecondCalls:
    def test_revert_second_stop_resume(self):
        contracts.lido.stop({"from": contracts.voting})

        with brownie.reverts("CONTRACT_IS_STOPPED"):
            contracts.lido.stop({"from": contracts.voting})

        contracts.lido.resume({"from": contracts.voting})

        with brownie.reverts("CONTRACT_IS_ACTIVE"):
            contracts.lido.resume({"from": contracts.voting})

    @pytest.mark.skip(
        reason="Second call of pause/resume staking is not reverted right now."
        "It maybe should be fixed in the future to be consistent, "
        "there's not a real problem with it."
    )
    def test_revert_second_pause_resume_staking(self):
        contracts.lido.pauseStaking({"from": contracts.voting})

        with brownie.reverts(""):
            contracts.lido.pauseStaking({"from": contracts.voting})

        contracts.lido.resumeStaking({"from": contracts.voting})

        with brownie.reverts(""):
            contracts.lido.resumeStaking({"from": contracts.voting})

    def test_revert_second_pause_resume_staking_module(self, stranger):
        contracts.staking_router.pauseStakingModule(1, {"from": contracts.deposit_security_module})

        with brownie.reverts(encode_error("StakingModuleNotActive()")):
            contracts.staking_router.pauseStakingModule(1, {"from": contracts.deposit_security_module})

        contracts.staking_router.grantRole(
            web3.keccak(text="STAKING_MODULE_RESUME_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        contracts.staking_router.resumeStakingModule(1, {"from": stranger})

        with brownie.reverts(encode_error("StakingModuleNotPaused()")):
            contracts.staking_router.resumeStakingModule(1, {"from": stranger})

    def test_revert_second_stop_staking_module(self, helpers, stranger):
        contracts.staking_router.grantRole(
            web3.keccak(text="STAKING_MODULE_MANAGE_ROLE"),
            stranger,
            {"from": contracts.agent},
        )

        contracts.staking_router.setStakingModuleStatus(1, StakingModuleStatus.Stopped, {"from": stranger})
        with brownie.reverts(encode_error("StakingModuleStatusTheSame()")):
            contracts.staking_router.setStakingModuleStatus(1, StakingModuleStatus.Stopped, {"from": stranger})

    def test_revert_second_pause_resume_withdrawal_queue(self, helpers, stranger):
        inf = contracts.withdrawal_queue.PAUSE_INFINITELY()
        contracts.withdrawal_queue.grantRole(
            web3.keccak(text="PAUSE_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        contracts.withdrawal_queue.pauseFor(inf, {"from": stranger})
        with brownie.reverts(encode_error("ResumedExpected()")):
            contracts.withdrawal_queue.pauseFor(inf, {"from": stranger})

        contracts.withdrawal_queue.grantRole(
            web3.keccak(text="RESUME_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        contracts.withdrawal_queue.resume({"from": stranger})
        with brownie.reverts(encode_error("PausedExpected()")):
            contracts.withdrawal_queue.resume({"from": stranger})

    def test_revert_second_pause_resume_validators_exit_bus(self, helpers, stranger):
        inf = contracts.validators_exit_bus_oracle.PAUSE_INFINITELY()
        contracts.validators_exit_bus_oracle.grantRole(
            web3.keccak(text="PAUSE_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        contracts.validators_exit_bus_oracle.pauseFor(inf, {"from": stranger})
        with brownie.reverts(encode_error("ResumedExpected()")):
            contracts.validators_exit_bus_oracle.pauseFor(inf, {"from": stranger})

        contracts.validators_exit_bus_oracle.grantRole(
            web3.keccak(text="RESUME_ROLE"),
            stranger,
            {"from": contracts.agent},
        )
        contracts.validators_exit_bus_oracle.resume({"from": stranger})
        with brownie.reverts(encode_error("PausedExpected()")):
            contracts.validators_exit_bus_oracle.resume({"from": stranger})


# Lido contract tests


@pytest.mark.usefixtures("stopped_lido")
def test_stopped_lido_cant_stake(stranger):
    with brownie.reverts("STAKING_PAUSED"):
        stranger.transfer(contracts.lido, DEPOSIT_AMOUNT)


@pytest.mark.usefixtures("stopped_lido")
def test_stopped_lido_cant_deposit():
    with brownie.reverts("CAN_NOT_DEPOSIT"):
        contracts.lido.deposit(1, 1, "0x", {"from": contracts.deposit_security_module}),


@pytest.mark.usefixtures("stopped_lido")
def test_resumed_staking_can_stake(stranger):
    contracts.lido.resumeStaking({"from": contracts.voting})
    stranger.transfer(contracts.lido, DEPOSIT_AMOUNT)


@pytest.mark.usefixtures("stopped_lido")
def test_resumed_staking_cant_deposit():
    contracts.lido.resumeStaking({"from": contracts.voting})

    with brownie.reverts("CAN_NOT_DEPOSIT"):
        contracts.lido.deposit(1, 1, "0x", {"from": contracts.deposit_security_module}),


@pytest.mark.usefixtures("stopped_lido")
def test_resumed_lido_can_stake(stranger):
    contracts.lido.resume({"from": contracts.voting})
    stranger.transfer(contracts.lido, DEPOSIT_AMOUNT)


@pytest.mark.usefixtures("stopped_lido")
def test_resumed_lido_can_deposit(stranger):
    contracts.lido.resume({"from": contracts.voting})
    contracts.lido.deposit(1, 1, "0x", {"from": contracts.deposit_security_module}),


def test_paused_staking_can_report():
    contracts.lido.pauseStaking({"from": contracts.voting})
    oracle_report()


# Staking module tests


def test_paused_staking_module_cant_stake():
    contracts.staking_router.pauseStakingModule(1, {"from": contracts.deposit_security_module})
    with brownie.reverts(encode_error("StakingModuleNotActive()")):
        contracts.lido.deposit(1, 1, "0x", {"from": contracts.deposit_security_module}),


def test_paused_staking_module_can_reward(burner: Contract):
    _, module_address, *_ = contracts.staking_router.getStakingModule(1)
    contracts.staking_router.pauseStakingModule(1, {"from": contracts.deposit_security_module})
    (report_tx, _) = oracle_report()
    print(report_tx.events["Transfer"])
    module_index = 0
    simple_dvt_index = 1

    if report_tx.events["Transfer"][module_index]["to"] == burner.address:
        module_index += 1
        simple_dvt_index += 1

    agent_index = module_index + 2
    assert report_tx.events["Transfer"][module_index]["to"] == module_address
    assert report_tx.events["Transfer"][module_index]["from"] == ZERO_ADDRESS
    assert report_tx.events["Transfer"][agent_index]["to"] == contracts.agent
    assert report_tx.events["Transfer"][agent_index]["from"] == ZERO_ADDRESS

    # the staking modules ids starts from 1, so SDVT has id = 2
    simple_dvt_stats = contracts.staking_router.getStakingModule(2)
    # simple_dvt_treasury_fee = sdvt_share / share_pct * treasury_pct
    simple_dvt_treasury_fee = (
        report_tx.events["Transfer"][simple_dvt_index]["value"]
        * 100_00
        // simple_dvt_stats["stakingModuleFee"]
        * simple_dvt_stats["treasuryFee"]
        // 100_00
    )
    assert almostEqWithDiff(
        report_tx.events["Transfer"][module_index]["value"] + simple_dvt_treasury_fee,
        report_tx.events["Transfer"][agent_index]["value"],
        100,
    )
    assert report_tx.events["Transfer"][module_index]["value"] > 0


def test_stopped_staking_module_cant_stake(stranger):
    contracts.staking_router.grantRole(
        web3.keccak(text="STAKING_MODULE_MANAGE_ROLE"),
        stranger,
        {"from": contracts.agent},
    )

    contracts.staking_router.setStakingModuleStatus(1, StakingModuleStatus.Stopped, {"from": stranger})
    with brownie.reverts(encode_error("StakingModuleNotActive()")):
        contracts.lido.deposit(1, 1, "0x", {"from": contracts.deposit_security_module}),


def test_stopped_staking_module_cant_reward(stranger):
    contracts.staking_router.grantRole(
        web3.keccak(text="STAKING_MODULE_MANAGE_ROLE"),
        stranger,
        {"from": contracts.agent},
    )
    _, module_address, *_ = contracts.staking_router.getStakingModule(1)
    contracts.staking_router.setStakingModuleStatus(1, StakingModuleStatus.Stopped, {"from": stranger})
    shares_before = contracts.lido.sharesOf(module_address)
    oracle_report()
    assert contracts.lido.sharesOf(module_address) == shares_before


def test_stopped_lido_cant_reward(stranger):
    contracts.lido.stop({"from": contracts.voting})

    with brownie.reverts("CONTRACT_IS_STOPPED"):
        oracle_report()


# Withdrawal queue tests


def make_withdrawal_request(stranger):
    stranger.transfer(contracts.lido, DEPOSIT_AMOUNT)
    contracts.lido.approve(contracts.withdrawal_queue, DEPOSIT_AMOUNT - 1, {"from": stranger})
    contracts.withdrawal_queue.requestWithdrawals([DEPOSIT_AMOUNT - 1], stranger, {"from": stranger})


def pause_withdrawal_queue(stranger):
    contracts.withdrawal_queue.grantRole(
        web3.keccak(text="PAUSE_ROLE"),
        stranger,
        {"from": contracts.agent},
    )
    inf = contracts.withdrawal_queue.PAUSE_INFINITELY()
    contracts.withdrawal_queue.pauseFor(inf, {"from": stranger})


def test_paused_withdrawal_queue_cant_withdraw(stranger):
    pause_withdrawal_queue(stranger)

    with brownie.reverts(encode_error("ResumedExpected()")):
        make_withdrawal_request(stranger)


def test_paused_withdrawal_queue_can_stake(stranger):
    pause_withdrawal_queue(stranger)
    stranger.transfer(contracts.lido, DEPOSIT_AMOUNT)


def test_paused_withdrawal_queue_can_rebase(stranger):
    pause_withdrawal_queue(stranger)
    oracle_report()


def test_stopped_lido_cant_withdraw(stranger):
    stranger.transfer(contracts.lido, DEPOSIT_AMOUNT)
    contracts.lido.approve(contracts.withdrawal_queue, DEPOSIT_AMOUNT - 1, {"from": stranger})

    contracts.lido.stop({"from": contracts.voting})

    with brownie.reverts("CONTRACT_IS_STOPPED"):
        contracts.withdrawal_queue.requestWithdrawals([DEPOSIT_AMOUNT - 1], stranger, {"from": stranger})


# Validators exit bus tests


def prepare_report():
    ref_slot, _ = contracts.hash_consensus_for_validators_exit_bus_oracle.getCurrentFrame()
    consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    items, hash = prepare_exit_bus_report([], ref_slot)
    fast_lane_members, _ = contracts.hash_consensus_for_validators_exit_bus_oracle.getFastLaneMembers()
    for m in fast_lane_members:
        contracts.hash_consensus_for_validators_exit_bus_oracle.submitReport(
            ref_slot, hash, consensus_version, {"from": m}
        )
    return items, m


def pause_validators_exit_bus(stranger):
    contracts.validators_exit_bus_oracle.grantRole(
        web3.keccak(text="PAUSE_ROLE"),
        stranger,
        {"from": contracts.agent},
    )
    inf = contracts.validators_exit_bus_oracle.PAUSE_INFINITELY()
    contracts.validators_exit_bus_oracle.pauseFor(inf, {"from": stranger})


def test_paused_validators_exit_bus_cant_submit_report(stranger):
    chain.sleep(2 * 24 * 3600)
    chain.mine()

    contract_version = contracts.validators_exit_bus_oracle.getContractVersion()

    pause_validators_exit_bus(stranger)

    report, member = prepare_report()
    with brownie.reverts(encode_error("ResumedExpected()")):
        contracts.validators_exit_bus_oracle.submitReportData(report, contract_version, {"from": member})


def test_stopped_lido_can_exit_validators(stranger):
    chain.sleep(2 * 24 * 3600)
    chain.mine()

    contract_version = contracts.validators_exit_bus_oracle.getContractVersion()

    contracts.lido.stop({"from": contracts.voting})

    report, member = prepare_report()
    contracts.validators_exit_bus_oracle.submitReportData(report, contract_version, {"from": member})
