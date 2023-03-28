"""
Tests for voting ??/05/2023
"""
from brownie import reverts, ShapellaUpgradeTemplate, chain, web3


def get_current_timestamp():
    return web3.eth.get_block("latest").timestamp


def typed_error(error):
    def get_error_msg(hash):
        return f"typed error: {hash}"

    return {
        "OnlyVotingCanUpgrade": get_error_msg("0x8391d412"),
        "ExpireSinceMustBeInFuture": get_error_msg("0xb07ade0f"),
        "Expired": get_error_msg("0x203d82d8"),
    }[error]


def test_allowed_expiration_timestamp(accounts):
    with reverts(typed_error("ExpireSinceMustBeInFuture")):
        ShapellaUpgradeTemplate.deploy(0, {"from": accounts[0]})

    with reverts(typed_error("ExpireSinceMustBeInFuture")):
        ShapellaUpgradeTemplate.deploy(get_current_timestamp() - 1, {"from": accounts[0]})

    with reverts(typed_error("ExpireSinceMustBeInFuture")):
        ShapellaUpgradeTemplate.deploy(get_current_timestamp(), {"from": accounts[0]})

    ShapellaUpgradeTemplate.deploy(get_current_timestamp() + 1, {"from": accounts[0]})


def test_expiration_at_current_block(accounts):
    expire_in = 100
    template = ShapellaUpgradeTemplate.deploy(get_current_timestamp() + expire_in, {"from": accounts[0]})

    with reverts(typed_error("OnlyVotingCanUpgrade")):
        template.startUpgrade({"from": accounts[0]})

    chain.sleep(2 * expire_in)
    with reverts(typed_error("Expired")):
        template.startUpgrade({"from": accounts[0]})

    with reverts(typed_error("Expired")):
        template.finishUpgrade({"from": accounts[0]})

    # NB: for unknown reason it reverts with empty typed error string, although it mustn't
    with reverts():
        template.assertUpgradeIsFinishedCorrectly({"from": accounts[0]})

    # NB: for unknown reason it reverts with empty typed error string, although it mustn't
    with reverts():
        template.revertIfUpgradeNotEnacted({"from": accounts[0]})
