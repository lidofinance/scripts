"""
Tests for voting ??/05/2023
"""
import pytest

from brownie import web3, interface, convert, reverts
from utils.config import (
    contracts,
    lido_dao_withdrawal_queue_implementation,
    lido_dao_withdrawal_vault_implementation,
    lido_dao_staking_router_implementation,
    lido_dao_accounting_oracle_implementation,
    lido_dao_validators_exit_bus_oracle_implementation,
    accounts,
)


petrification_mark = 115792089237316195423570985008687907853269984665640564039457584007913129639935


@pytest.fixture(scope="module")
def petrified_implementations(shapella_upgrade_template):
    return {
        # dao aragon app contracts
        "Lido": {
            "contract": interface.AppProxyUpgradeable(contracts.lido_v1.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoVoting": {
            "contract": interface.AppProxyUpgradeable(contracts.voting.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoFinance": {
            "contract": interface.AppProxyUpgradeable(contracts.finance.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoACL": {
            "contract": interface.AppProxyUpgradeable(contracts.acl.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoAgent": {
            "contract": interface.AppProxyUpgradeable(contracts.agent.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "NodeOperatorsRegistry": {
            "contract": interface.AppProxyUpgradeable(contracts.node_operators_registry_v1.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "LegacyOracle": {
            "contract": interface.AppProxyUpgradeable(contracts.node_operators_registry_v1.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoKernel": {
            "contract": interface.AppProxyUpgradeable(contracts.kernel.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "AppRepo": {
            "contract": interface.AppProxyUpgradeable(contracts.lido_app_repo.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "NosRepo": {
            "contract": interface.AppProxyUpgradeable(contracts.nos_app_repo.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "VotingRepo": {
            "contract": interface.AppProxyUpgradeable(contracts.voting_app_repo.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "OracleRepo": {
            "contract": interface.AppProxyUpgradeable(contracts.oracle_app_repo.address),
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        # contracts with dummy impl to be upgraded with template
        "Withdrawal_vault": {
            "contract": interface.WithdrawalVaultManager(contracts.withdrawal_vault.address),
            "proxy_type": "WithdrawalsManagerProxy",
            "implementation_type": "Dummy",
        },
        "LidoLocator": {
            "contract": interface.OssifiableProxy(contracts.lido_locator.address),
            "proxy_type": "OssifiableProxy",
            "implementation_type": "Dummy",
        },
        "StakingRouter": {
            "proxy_type": "OssifiableProxy",
            "implementation_type": "Dummy",
            "contract": interface.OssifiableProxy(contracts.staking_router.address),
        },
        "WithdrawalQueue": {
            "contract": interface.OssifiableProxy(contracts.withdrawal_queue.address),
            "proxy_type": "OssifiableProxy",
            "implementation_type": "Dummy",
        },
        "AccountingOracle": {
            "contract": interface.OssifiableProxy(contracts.accounting_oracle.address),
            "proxy_type": "OssifiableProxy",
            "implementation_type": "Dummy",
        },
        "ValidatorsExitBusOracle": {
            "contract": interface.OssifiableProxy(contracts.validators_exit_bus_oracle.address),
            "proxy_type": "OssifiableProxy",
            "implementation_type": "Dummy",
        },
        # pure implementations
        "WithdrawalQueueImplementation": {
            "contract": interface.WithdrawalQueueERC721(lido_dao_withdrawal_queue_implementation),
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "WithdrawalVaultImplementation": {
            "contract": interface.WithdrawalVault(lido_dao_withdrawal_vault_implementation),
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "StakingRouterImplementation": {
            "contract": interface.StakingRouter(lido_dao_staking_router_implementation),
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "AccountingOracleImplementation": {
            "contract": interface.AccountingOracle(lido_dao_accounting_oracle_implementation),
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "ValidatorsExitBusOracleImplementation": {
            "contract": interface.ValidatorsExitBusOracle(lido_dao_validators_exit_bus_oracle_implementation),
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "LidoLocatorImplementation": {
            "contract": interface.LidoLocator(lido_dao_validators_exit_bus_oracle_implementation),
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
    }


INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dead"

def test_is_petrified(petrified_implementations):
    for contract_name, contract_config in petrified_implementations.items():
        print("Petrified Contract: {0}".format(contract_name))
        implementation_address = None
        proxy_type = contract_config["proxy_type"]
        implementation_type = contract_config["implementation_type"]
        if proxy_type == "OssifiableProxy":
            implementation_address = contract_config["contract"].proxy__getImplementation()
        elif proxy_type == "WithdrawalsManagerProxy" or proxy_type == "AppProxyUpgradeable":
            implementation_address = contract_config["contract"].implementation()
        elif proxy_type == "Implementation":
            implementation_address = contract_config["contract"].address
        else:
            assert False, "unsupported proxy_type"

        assert implementation_address

        if implementation_type == "Versioned":
            # stub interface for versioned inherited contracts
            versioned = interface.WithdrawalVault(implementation_address)
            version = versioned.getContractVersion()
            assert version == petrification_mark
        elif implementation_type == "Dummy":
            # dummy implementation has no functions, try general initilizable interface
            dummyContract = interface.WithdrawalVault(implementation_address)
            with reverts():
                dummyContract.initialize({"from": accounts[0]})
        elif implementation_type == "AragonApp":
            aragonApp = interface.ACL(implementation_address)
            assert aragonApp.isPetrified()
        else:
            assert False, "implementation_type"


def test_stone(shapella_upgrade_template):
    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0
    assert contracts.lido.sharesOf(INITIAL_TOKEN_HOLDER) > 0
