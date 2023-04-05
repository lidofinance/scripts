
from brownie import web3, interface
from collections import OrderedDict
from utils.withdrawal_credentials import (
    extract_address_from_eth1_wc
)
from utils.config import (
    contracts,
    deployer_eoa,
    lido_dao_withdrawal_vault,
    lido_dao_withdrawal_vault_implementation,
    lido_dao_lido_locator,
)
from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting


WITHDRAWAL_VAULT_ADDRESS = '0xb9d7934878b5fb9610b3fe8a5e441e8fad7e293f'
EL_REWARDS_VAULT_ADDRESS = '0x388C818CA8B9251b393131C08a736A67ccB19297'



def upgrade_withdrawal_vault():
    vault = interface.WithdrawalVaultManager(lido_dao_withdrawal_vault)
    vault.proxy_upgradeTo(lido_dao_withdrawal_vault_implementation, b"", {"from": contracts.voting.address})


# ElRewardsVault did not changed
def test_el_rewards_vault_did_not_changed(accounts):
    template = prepare_for_shapella_upgrade_voting(deployer_eoa, silent=True)

    locator = interface.LidoLocator(lido_dao_lido_locator)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._elRewardsVault() == EL_REWARDS_VAULT_ADDRESS
    assert core_components[0] == EL_REWARDS_VAULT_ADDRESS
    assert oracle_report_components[1] == EL_REWARDS_VAULT_ADDRESS


# Withdrawals vault addr did not changed
def test_withdrawals_vault_addr_did_not_changed(accounts):
    template = prepare_for_shapella_upgrade_voting(deployer_eoa, silent=True)
    upgrade_withdrawal_vault()

    locator = interface.LidoLocator(lido_dao_lido_locator)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._withdrawalVault() == WITHDRAWAL_VAULT_ADDRESS
    assert core_components[5] == WITHDRAWAL_VAULT_ADDRESS
    assert oracle_report_components[5] == WITHDRAWAL_VAULT_ADDRESS


# WithdrawalVault address is matching with WithdrawalCredentials
def test_withdrawals_vault_addr_matching_with_wc(accounts):
    withdrawal_credentials = contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_addresss = extract_address_from_eth1_wc(str(withdrawal_credentials))
    assert withdrawal_credentials_addresss == WITHDRAWAL_VAULT_ADDRESS

    prepare_for_shapella_upgrade_voting(deployer_eoa, silent=True)
    upgrade_withdrawal_vault()

    withdrawal_credentials = contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_addresss = extract_address_from_eth1_wc(str(withdrawal_credentials))

    assert withdrawal_credentials_addresss == WITHDRAWAL_VAULT_ADDRESS
