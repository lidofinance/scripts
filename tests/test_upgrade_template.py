"""
Tests for voting ??/05/2023
"""
from brownie import reverts, ShapellaUpgradeTemplate, chain, web3, interface, ZERO_ADDRESS
from brownie.convert import to_uint
from collections import OrderedDict
from utils.config import (
    contracts,
    deployer_eoa,
    lido_dao_withdrawal_vault,
    lido_dao_withdrawal_vault_implementation,
)
from utils.shapella_upgrade import (
    prepare_for_shapella_upgrade_voting,
    prepare_deploy_upgrade_template,
    TIMESTAMP_FIRST_SECOND_OF_JULY_2023,
)

VOTING_DURATION = 3 * 24 * 60 * 60


def get_current_timestamp():
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


def deploy_template_with_preparation():
    template = prepare_for_shapella_upgrade_voting(deployer_eoa, silent=True)
    # Also need to do the preliminary startUpgrade voting item
    upgrade_withdrawal_vault()
    return template


def test_expire_since_allowed_values_range(accounts):
    def get_min_expire_since():
        return get_current_timestamp() + VOTING_DURATION

    # with reverts(typed_error("ExpireSinceMustBeInRange", get_min_expire_since(), TIMESTAMP_FIRST_SECOND_OF_JULY_2023)):
    #     ShapellaUpgradeTemplate.deploy(0, {"from": accounts[0]})

    # min_expire_since = get_min_expire_since()
    # with reverts(typed_error("ExpireSinceMustBeInRange", min_expire_since, TIMESTAMP_FIRST_SECOND_OF_JULY_2023)):
    #     ShapellaUpgradeTemplate.deploy(min_expire_since - 1, {"from": accounts[0]})

    # ShapellaUpgradeTemplate.deploy(get_min_expire_since(), {"from": accounts[0]})
    ShapellaUpgradeTemplate.deploy(TIMESTAMP_FIRST_SECOND_OF_JULY_2023, {"from": accounts[0]})

    # with reverts(typed_error("ExpireSinceMustBeInRange", get_min_expire_since(), TIMESTAMP_FIRST_SECOND_OF_JULY_2023)):
    #     ShapellaUpgradeTemplate.deploy(TIMESTAMP_FIRST_SECOND_OF_JULY_2023 + 1, {"from": accounts[0]})

    # ShapellaUpgradeTemplate.deploy(get_current_timestamp() + 2, {"from": accounts[0]})


def test_expiration(accounts):
    expire_in = 4 * 24 * 60 * 60
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
        template.revertIfUpgradeNotFinished(tx_args)


def test_fail_start_if_not_from_voting(accounts):
    template = deploy_template_with_preparation()
    with reverts(typed_error("OnlyVotingCanUpgrade")):
        template.startUpgrade({"from": accounts[9]})


def test_fail_finish_if_not_from_voting(accounts):
    template = deploy_template_with_preparation()
    with reverts(typed_error("OnlyVotingCanUpgrade")):
        template.finishUpgrade({"from": accounts[9]})


def test_fail_start_twice():
    template = deploy_template_with_preparation()
    template.startUpgrade({"from": contracts.voting})
    with reverts(typed_error("UpgradeAlreadyStarted")):
        template.startUpgrade({"from": contracts.voting})


def test_fail_finish_if_not_started():
    template = deploy_template_with_preparation()
    with reverts(typed_error("UpgradeNotStarted")):
        template.finishUpgrade({"from": contracts.voting})


def test_fail_finish_if_started_in_different_block():
    from_voting_tx_args = {"from": contracts.voting.address}
    template = deploy_template_with_preparation()

    # By default brownie creates a separate block for each tx, so this reverts
    template.startUpgrade(from_voting_tx_args)
    with reverts(typed_error("StartAndFinishMustBeInSameBlock")):
        template.finishUpgrade(from_voting_tx_args)

    # I've tried to check that is passes in the same block by using brownie.multicall
    # but hasn't succeeded in substituting the multicall_address to voting
