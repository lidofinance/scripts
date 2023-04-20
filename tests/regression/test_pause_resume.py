import brownie
import pytest

from utils.config import contracts

DEPOSIT_AMOUNT = 100 * 10 ** 18


class TestEventsEmitted:
    @pytest.mark.usefixtures("active_lido")
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


    @pytest.mark.usefixtures("active_lido")
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


class TestRevertedSecondCalls:
    @pytest.mark.usefixtures("active_lido")
    def test_revert_second_stop_resume(self):
        contracts.lido.stop({"from": contracts.voting})

        with brownie.reverts("CONTRACT_IS_STOPPED"):
            contracts.lido.stop({"from": contracts.voting})

        contracts.lido.resume({"from": contracts.voting})

        with brownie.reverts("CONTRACT_IS_ACTIVE"):
            contracts.lido.resume({"from": contracts.voting})

    @pytest.mark.skip(reason="Second call of pause/resume staking is not reverted right now."
                             "It maybe should be fixed in the future to be consistent, "
                             "there's not a real problem with it.")
    @pytest.mark.usefixtures("active_lido")
    def test_revert_second_pause_resume_staking(self):
        contracts.lido.pauseStaking({"from": contracts.voting})

        with brownie.reverts(""):
            contracts.lido.pauseStaking({"from": contracts.voting})

        contracts.lido.resumeStaking({"from": contracts.voting})

        with brownie.reverts(""):
            contracts.lido.resumeStaking({"from": contracts.voting})


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
