"""
Tests for voting ??/05/2023
"""
import pytest
from brownie import reverts, ShapellaUpgradeTemplate, chain, web3, interface
from scripts.upgrade_shapella_1 import start_vote
from collections import OrderedDict
from utils.config import (
    contracts,
    deployer_eoa,
    lido_dao_withdrawal_vault,
    lido_dao_withdrawal_vault_implementation,
    ldo_holder_address_for_tests,
    MAINNET_VOTE_DURATION,
)
from utils.evm_script import encode_error
from utils.shapella_upgrade import (
    prepare_for_shapella_upgrade_voting,
    TIMESTAMP_FIRST_SECOND_OF_JULY_2023_UTC,
)


@pytest.fixture(scope="function", autouse=True)
def template():
    return prepare_for_shapella_upgrade_voting(deployer_eoa, silent=True)


def get_current_chain_timestamp():
    return web3.eth.get_block("latest").timestamp


def typed_error(error, *values):
    # NB: brownie fails to resolve custom error names and reverts with messages like 'type error: 0x00112233
    return {
        "OnlyVotingCanUpgrade": encode_error("OnlyVotingCanUpgrade()", values),
        "ExpireSinceMustBeInRange": encode_error("ExpireSinceMustBeInRange()", values),
        "StartAndFinishMustBeInSameBlock": encode_error("StartAndFinishMustBeInSameBlock()", values),
        "Expired": encode_error("Expired()", values),
        "UpgradeAlreadyStarted": encode_error("UpgradeAlreadyStarted()", values),
        "UpgradeNotStarted": encode_error("UpgradeNotStarted()", values),
        "OnlyVotingCanUpgrade": encode_error("OnlyVotingCanUpgrade()", values),
    }[error]


def assert_single_event(tx, name, params):
    assert len(tx.events) == 1, f"More than 1 event in transaction, expected single event '{name}'"
    assert tx.events[name] == OrderedDict(params)


def upgrade_withdrawal_vault():
    vault = interface.WithdrawalVaultManager(lido_dao_withdrawal_vault)
    vault.proxy_upgradeTo(lido_dao_withdrawal_vault_implementation, b"", {"from": contracts.voting.address})


def test_expire_since_constant(accounts):
    template = ShapellaUpgradeTemplate.deploy({"from": accounts[0]})
    assert template.EXPIRE_SINCE_INCLUSIVE() == TIMESTAMP_FIRST_SECOND_OF_JULY_2023_UTC


def test_fail_if_expired(accounts, template):
    tx_args = {"from": accounts[0]}
    expire_since = TIMESTAMP_FIRST_SECOND_OF_JULY_2023_UTC

    time_to_sleep = expire_since - get_current_chain_timestamp() + 1
    chain.sleep(time_to_sleep)

    with reverts(typed_error("Expired")):
        template.startUpgrade(tx_args)

    with reverts(typed_error("Expired")):
        template.finishUpgrade(tx_args)


def test_succeed_if_5_minutes_before_expire(accounts, helpers):
    """It is hard to control time in the chain via brownie so just checking ~5 minutes before"""
    tx_params = {"from": ldo_holder_address_for_tests}
    vote_id, _ = start_vote(tx_params, silent=True)

    time_to_sleep = TIMESTAMP_FIRST_SECOND_OF_JULY_2023_UTC - get_current_chain_timestamp() - 5 * 60
    assert time_to_sleep > MAINNET_VOTE_DURATION, "this test is not supposed to work after 3 days before 1st of July"
    helpers.execute_votes(accounts, [vote_id], contracts.voting, skip_time=time_to_sleep)


def test_revert_if_upgrade_not_finished(accounts, helpers, template):
    # NB: due to some bug brownie returns empty revert string for view function
    with reverts(""):
        template.revertIfUpgradeNotFinished()

    tx_params = {"from": ldo_holder_address_for_tests}
    vote_id, _ = start_vote(tx_params, silent=True)
    helpers.execute_votes(accounts, [vote_id], contracts.voting)

    # Expect no revert
    template.revertIfUpgradeNotFinished()


def test_fail_start_if_not_from_voting(stranger, template):
    with reverts(typed_error("OnlyVotingCanUpgrade")):
        template.startUpgrade({"from": stranger})


def test_fail_finish_if_not_from_voting(stranger, template):
    with reverts(typed_error("OnlyVotingCanUpgrade")):
        template.finishUpgrade({"from": stranger})


def test_fail_start_twice(template):
    upgrade_withdrawal_vault()
    template.startUpgrade({"from": contracts.voting})
    with reverts(typed_error("UpgradeAlreadyStarted")):
        template.startUpgrade({"from": contracts.voting})


def test_fail_finish_if_not_started(template):
    with reverts(typed_error("UpgradeNotStarted")):
        template.finishUpgrade({"from": contracts.voting})


def test_revert_if_upgrade_not_finished_after_start(template):
    upgrade_withdrawal_vault()
    template.startUpgrade({"from": contracts.voting})

    # NB: due to some bug brownie returns empty revert string for view function
    with reverts(""):
        template.revertIfUpgradeNotFinished()


def test_fail_finish_if_started_in_different_block(template):
    from_voting_tx_args = {"from": contracts.voting.address}

    upgrade_withdrawal_vault()
    # By default brownie creates a separate block for each tx, so this reverts
    template.startUpgrade(from_voting_tx_args)
    with reverts(typed_error("StartAndFinishMustBeInSameBlock")):
        template.finishUpgrade(from_voting_tx_args)
