"""
Tests for voting ??/05/2023
"""
import pytest
from brownie import reverts, ShapellaUpgradeTemplate, chain, web3, interface, ZERO_ADDRESS
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
    def hex_encode(value):
        padding = 66
        return f"{value:#0{padding}x}"[2:]

    def get_error_msg(hash, values):
        s = f"typed error: {hash}"
        for v in values:
            s += hex_encode(v)
        return s

    # NB: brownie fails to resolve custom error names and reverts with messages like 'type error: 0x00112233
    return {
        "OnlyVotingCanUpgrade": get_error_msg("0x8391d412", values),
        "ExpireSinceMustBeInRange": get_error_msg("0x3c225381", values),
        "StartAndFinishMustBeInSameBlock": get_error_msg("0xec65b7ba", values),
        "Expired": get_error_msg("0x203d82d8", values),
        "UpgradeAlreadyStarted": get_error_msg("0x18364e28", values),
        "UpgradeNotStarted": get_error_msg("0x3b7e326c", values),
        "OnlyVotingCanUpgrade": get_error_msg("0x8391d412", values),
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
    # NB: for unknown reason brownie returns empty revert string, although it must fail with typed error
    #     that's why don't check the revert message here
    with reverts(""):
        template.revertIfUpgradeNotFinished()

    # NB: for unknown reason brownie returns empty revert string, although it must fail with typed error
    #     that's why don't check the revert message here
    with reverts(""):
        template.assertUpgradeIsFinishedCorrectly()

    tx_params = {"from": ldo_holder_address_for_tests}
    vote_id, _ = start_vote(tx_params, silent=True)
    helpers.execute_votes(accounts, [vote_id], contracts.voting)

    # Expect no revert
    template.revertIfUpgradeNotFinished()
    template.assertUpgradeIsFinishedCorrectly()


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

    # NB: for unknown reason brownie returns empty revert string, although it must fail with typed error
    #     that's why don't check the revert message here
    with reverts(""):
        template.revertIfUpgradeNotFinished()


def test_fail_finish_if_started_in_different_block(template):
    from_voting_tx_args = {"from": contracts.voting.address}

    upgrade_withdrawal_vault()
    # By default brownie creates a separate block for each tx, so this reverts
    template.startUpgrade(from_voting_tx_args)
    with reverts(typed_error("StartAndFinishMustBeInSameBlock")):
        template.finishUpgrade(from_voting_tx_args)

    # I've tried to check that is passes in the same block by using brownie.multicall
    # but hasn't succeeded in substituting the multicall_address to voting
