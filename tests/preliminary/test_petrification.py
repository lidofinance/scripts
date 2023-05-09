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
    lido_dao_withdrawal_vault_implementation_v1,
    lido_dao_lido_locator_implementation,
    dummy_implementation_address,
    initial_dead_token_holder,
    accounts,
)


PETRIFICATION_MARK = 115792089237316195423570985008687907853269984665640564039457584007913129639935


@pytest.fixture(scope="module")
def petrified_implementations(shapella_upgrade_template):
    return {
        # dao aragon app contracts
        "Lido": {
            "contract_address": contracts.lido_v1.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoVoting": {
            "contract_address": contracts.voting.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoFinance": {
            "contract_address": contracts.finance.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoACL": {
            "contract_address": contracts.acl.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoAgent": {
            "contract_address": contracts.agent.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "NodeOperatorsRegistry": {
            "contract_address": contracts.node_operators_registry_v1.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "LegacyOracle": {
            "contract_address": contracts.legacy_oracle.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "DaoKernel": {
            "contract_address": contracts.kernel.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "AppRepo": {
            "contract_address": contracts.lido_app_repo.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "NosRepo": {
            "contract_address": contracts.nor_app_repo.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "VotingRepo": {
            "contract_address": contracts.voting_app_repo.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        "OracleRepo": {
            "contract_address": contracts.oracle_app_repo.address,
            "proxy_type": "AppProxyUpgradeable",
            "implementation_type": "AragonApp",
        },
        # contracts with dummy impl to be upgraded with template
        "Withdrawal_vault": {
            "contract_address": contracts.withdrawal_vault.address,
            "proxy_type": "WithdrawalsManagerProxy",
            "implementation_type": "WithdrawalVaultDummy",
        },
        # locator implementation is read-only
        "LidoLocator": {
            "contract_address": contracts.lido_locator.address,
            "proxy_type": "OssifiableProxy",
            "implementation_type": "LidoLocatorFixed",
        },
        "StakingRouter": {
            "contract_address": contracts.staking_router.address,
            "proxy_type": "OssifiableProxy",
            "implementation_type": "Dummy",
        },
        "WithdrawalQueue": {
            "contract_address": contracts.withdrawal_queue.address,
            "proxy_type": "OssifiableProxy",
            "implementation_type": "Dummy",
        },
        "AccountingOracle": {
            "contract_address": contracts.accounting_oracle.address,
            "proxy_type": "OssifiableProxy",
            "implementation_type": "Dummy",
        },
        "ValidatorsExitBusOracle": {
            "contract_address": contracts.validators_exit_bus_oracle.address,
            "proxy_type": "OssifiableProxy",
            "implementation_type": "Dummy",
        },
        # pure implementations
        "WithdrawalQueueImplementation": {
            "contract_address": lido_dao_withdrawal_queue_implementation,
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "WithdrawalVaultImplementation": {
            "contract_address": lido_dao_withdrawal_vault_implementation,
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "StakingRouterImplementation": {
            "contract_address": lido_dao_staking_router_implementation,
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "AccountingOracleImplementation": {
            "contract_address": lido_dao_accounting_oracle_implementation,
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "ValidatorsExitBusOracleImplementation": {
            "contract_address": lido_dao_validators_exit_bus_oracle_implementation,
            "proxy_type": "Implementation",
            "implementation_type": "Versioned",
        },
        "LidoLocatorImplementation": {
            "contract_address": lido_dao_lido_locator_implementation,
            "proxy_type": "Implementation",
            "implementation_type": "LidoLocatorFixed",
        },
    }


def test_is_petrified(petrified_implementations):
    for contract_name, contract_config in petrified_implementations.items():
        print("Petrified Contract: {0}".format(contract_name))

        implementation_address = None

        proxy_type = contract_config["proxy_type"]
        proxy_address = contract_config["contract_address"]
        implementation_type = contract_config["implementation_type"]

        # get implementation address from proxy
        if proxy_type == "AppProxyUpgradeable":
            implementation_address = interface.AppProxyUpgradeable(proxy_address).implementation()
        elif proxy_type == "WithdrawalsManagerProxy":
            implementation_address = interface.WithdrawalVaultManager(proxy_address).implementation()
        elif proxy_type == "OssifiableProxy":
            implementation_address = interface.OssifiableProxy(proxy_address).proxy__getImplementation()
        elif proxy_type == "Implementation":
            implementation_address = proxy_address
        else:
            assert False, "unsupported proxy_type"

        assert implementation_address

        # assert petrification depending on contract type
        if implementation_type == "AragonApp":
            assert interface.ACL(implementation_address).isPetrified()
        elif implementation_type == "WithdrawalVaultDummy":
            assert implementation_address == lido_dao_withdrawal_vault_implementation_v1
        elif implementation_type == "LidoLocatorFixed":
            assert implementation_address == lido_dao_lido_locator_implementation
        elif implementation_type == "Dummy":
            assert implementation_address == dummy_implementation_address
        elif implementation_type == "Versioned":
            assert interface.Versioned(implementation_address).getContractVersion() == PETRIFICATION_MARK
        else:
            assert False, "implementation_type"


def test_stone(shapella_upgrade_template):
    assert contracts.lido.balanceOf(initial_dead_token_holder) > 0
    assert contracts.lido.sharesOf(initial_dead_token_holder) > 0
