"""
Tests for voting ??/05/2023
"""
from brownie import reverts, ShapellaUpgradeTemplate, chain, web3, interface, multicall, Contract, network
from collections import OrderedDict
from utils.config import (
    contracts,
    deployer_eoa,
    lido_dao_withdrawal_vault,
    lido_dao_withdrawal_vault_implementation,
)
from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting


FAR_FUTURE = 4836112151


def get_current_timestamp():
    return web3.eth.get_block("latest").timestamp


def typed_error(error):
    def get_error_msg(hash):
        return f"typed error: {hash}"

    return {
        "OnlyVotingCanUpgrade": get_error_msg("0x8391d412"),
        "ExpireSinceMustBeInFuture": get_error_msg("0xb07ade0f"),
        "StartAndFinishMustBeInSameBlock": get_error_msg("0xec65b7ba"),
        "Expired": get_error_msg("0x203d82d8"),
    }[error]


def assert_single_event(tx, name, params):
    assert len(tx.events) == 1, f"More than 1 event in transaction, expected single event '{name}'"
    assert tx.events[name] == OrderedDict(params)


def upgrade_withdrawal_vault():
    vault = interface.WithdrawalVaultManager(lido_dao_withdrawal_vault)
    vault.proxy_upgradeTo(lido_dao_withdrawal_vault_implementation, b"", {"from": contracts.voting.address})


def test_allowed_expiration_timestamp(accounts):
    with reverts(typed_error("ExpireSinceMustBeInFuture")):
        ShapellaUpgradeTemplate.deploy(0, {"from": accounts[0]})

    with reverts(typed_error("ExpireSinceMustBeInFuture")):
        ShapellaUpgradeTemplate.deploy(get_current_timestamp() - 1, {"from": accounts[0]})

    with reverts(typed_error("ExpireSinceMustBeInFuture")):
        ShapellaUpgradeTemplate.deploy(get_current_timestamp(), {"from": accounts[0]})

    ShapellaUpgradeTemplate.deploy(get_current_timestamp() + 2, {"from": accounts[0]})


def test_start_and_finish_in_same_block(accounts):
    from_voting_tx_args = {"from": contracts.voting.address}
    chain.snapshot()
    template = prepare_for_shapella_upgrade_voting(deployer_eoa, silent=True)
    # Also need to do the preliminary startUpgrade voting item
    upgrade_withdrawal_vault()

    chain.snapshot()
    # By default brownie creates a separate block for each tx, so this reverts
    template.startUpgrade(from_voting_tx_args)
    with reverts(typed_error("StartAndFinishMustBeInSameBlock")):
        template.finishUpgrade(from_voting_tx_args)

    # I've tried to check that is passes in the same block by using brownie.multicall
    # but hasn't succeeded in substituting the multicall_address to voting

    chain.revert()


def test_expiration(accounts):
    expire_in = 100
    tx_args = {"from": accounts[0]}
    expire_since = get_current_timestamp() + expire_in

    template = ShapellaUpgradeTemplate.deploy(expire_since, tx_args)
    assert_single_event(template.tx, "TemplateCreated", {"expireSinceInclusive": expire_since})

    with reverts(typed_error("OnlyVotingCanUpgrade")):
        template.startUpgrade(tx_args)

    with reverts(typed_error("OnlyVotingCanUpgrade")):
        template.finishUpgrade(tx_args)

    chain.sleep(expire_in)

    with reverts(typed_error("Expired")):
        template.startUpgrade(tx_args)

    with reverts(typed_error("Expired")):
        template.finishUpgrade(tx_args)

    # NB: for unknown reason brownie returns empty revert string, although it must fail with typed error
    #     that's why don't check the revert message here
    with reverts():
        template.assertUpgradeIsFinishedCorrectly(tx_args)

    # NB: for unknown reason brownie returns empty revert string, although it must fail with typed error
    #     that's why don't check the revert message here
    with reverts():
        template.revertIfUpgradeNotEnacted(tx_args)
