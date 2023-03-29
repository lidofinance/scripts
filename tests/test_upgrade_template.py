"""
Tests for voting ??/05/2023
"""
from brownie import reverts, ShapellaUpgradeTemplate, chain, web3
from collections import OrderedDict


def get_current_timestamp():
    return web3.eth.get_block("latest").timestamp


def typed_error(error):
    def get_error_msg(hash):
        return f"typed error: {hash}"

    return {
        "OnlyVotingCanUpgrade": get_error_msg("0x8391d412"),
        "ExpireSinceMustBeInFuture": get_error_msg("0xb07ade0f"),
    }[error]


def test_allowed_expiration_timestamp(accounts):
    with reverts(typed_error("ExpireSinceMustBeInFuture")):
        ShapellaUpgradeTemplate.deploy(0, {"from": accounts[0]})

    with reverts(typed_error("ExpireSinceMustBeInFuture")):
        ShapellaUpgradeTemplate.deploy(get_current_timestamp() - 1, {"from": accounts[0]})

    with reverts(typed_error("ExpireSinceMustBeInFuture")):
        ShapellaUpgradeTemplate.deploy(get_current_timestamp(), {"from": accounts[0]})

    ShapellaUpgradeTemplate.deploy(get_current_timestamp() + 2, {"from": accounts[0]})


def test_expiration(accounts):
    expire_in = 100
    tx_args = {"from": accounts[0]}
    expire_since = get_current_timestamp() + expire_in

    template = ShapellaUpgradeTemplate.deploy(expire_since, tx_args)
    assert len(template.tx.events) == 1
    assert template.tx.events["TemplateCreated"] == OrderedDict([("expiresSinceInclusive", expire_since)])

    with reverts(typed_error("OnlyVotingCanUpgrade")):
        template.startUpgrade(tx_args)

    with reverts(typed_error("OnlyVotingCanUpgrade")):
        template.finishUpgrade(tx_args)

    chain.sleep(2 * expire_in)

    tx = template.startUpgrade(tx_args)
    assert len(tx.events) == 0

    tx = template.finishUpgrade(tx_args)
    assert len(tx.events) == 0

    # NB: for unknown reason it reverts with empty typed error string, although it mustn't
    with reverts():
        template.assertUpgradeIsFinishedCorrectly(tx_args)

    # NB: for unknown reason it reverts with empty typed error string, although it mustn't
    with reverts():
        template.revertIfUpgradeNotEnacted(tx_args)
