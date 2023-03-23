from brownie import interface, web3, chain
from utils.config import contracts, guardians

from test_upgrade_shapella_goerli import oracle_app_id


def test_accounting_oracle_state():
    # address in locator
    assert contracts.lido_locator.accountingOracle() == contracts.accounting_oracle

    # AppProxyUpgradeable
    assert (
        interface.OssifiableProxy(contracts.accounting_oracle).proxy__getImplementation()
        == "0x8C55A49639b456F98E1A8D7DAa3b29B378CADc8b"
    )

    # Roles
    # permissions is tested in test_permissions
    # but roles can have a wrong keccak
    assert (
        contracts.accounting_oracle.DEFAULT_ADMIN_ROLE()
        == "0x0000000000000000000000000000000000000000000000000000000000000000"
    )
    assert contracts.accounting_oracle.SUBMIT_DATA_ROLE() == web3.keccak(text="SUBMIT_DATA_ROLE").hex()
    assert (
        contracts.accounting_oracle.MANAGE_CONSENSUS_CONTRACT_ROLE()
        == web3.keccak(text="MANAGE_CONSENSUS_CONTRACT_ROLE").hex()
    )
    assert (
        contracts.accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE()
        == web3.keccak(text="MANAGE_CONSENSUS_VERSION_ROLE").hex()
    )

    # Constants
    assert contracts.accounting_oracle.LIDO() == contracts.lido
    assert contracts.accounting_oracle.LOCATOR() == contracts.lido_locator
    assert contracts.accounting_oracle.LEGACY_ORACLE() == contracts.legacy_oracle
    assert contracts.accounting_oracle.EXTRA_DATA_FORMAT_EMPTY() == 0
    assert contracts.accounting_oracle.EXTRA_DATA_FORMAT_LIST() == 1
    assert contracts.accounting_oracle.EXTRA_DATA_TYPE_STUCK_VALIDATORS() == 1
    assert contracts.accounting_oracle.EXTRA_DATA_TYPE_EXITED_VALIDATORS() == 2
    assert contracts.accounting_oracle.SECONDS_PER_SLOT() == 12
    assert contracts.accounting_oracle.GENESIS_TIME() == 1616508000

    # consensus version
    assert contracts.accounting_oracle.getConsensusVersion() == 1

    # Versioned
    assert contracts.accounting_oracle.getContractVersion() == 1

    # Processing state
    state = contracts.accounting_oracle.getProcessingState()
    assert state["currentFrameRefSlot"] > 5254400
    assert state["processingDeadlineTime"] == 0
    assert state["mainDataHash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert state["mainDataSubmitted"] == False
    assert state["extraDataHash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert state["extraDataFormat"] == 0
    assert state["extraDataSubmitted"] == False
    assert state["extraDataItemsCount"] == 0
    assert state["extraDataItemsSubmitted"] == 0

    assert contracts.accounting_oracle.getLastProcessingRefSlot() == 5254400

    # Consensus
    assert contracts.accounting_oracle.getConsensusContract() == "0x8EA83346E60261DdF1fA3B64056B096e337541b2"
    report = contracts.accounting_oracle.getConsensusReport()
    assert report["hash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert report["refSlot"] == 5254400
    assert report["processingDeadlineTime"] == 0
    assert report["processingStarted"] == False


def test_deposit_security_module_state():
    # address in locator
    assert contracts.lido_locator.depositSecurityModule() == contracts.deposit_security_module

    assert contracts.deposit_security_module.getOwner() == contracts.agent

    # Constants
    assert contracts.deposit_security_module.LIDO() == contracts.lido
    assert contracts.deposit_security_module.DEPOSIT_CONTRACT() == "0xff50ed3d0ec03aC01D4C79aAd74928BFF48a7b2b"
    assert contracts.deposit_security_module.STAKING_ROUTER() == contracts.staking_router
    assert contracts.deposit_security_module.PAUSE_MESSAGE_PREFIX() == "0x39acbf79283b8870cb37759cd96364cacb1465f74fb35e70990411fff054fec0"
    assert contracts.deposit_security_module.ATTEST_MESSAGE_PREFIX() == "0x9c8f4b970da39223460d0221dc6580b494021c2aefa5c066432baeecf943e380"

    # state
    assert contracts.deposit_security_module.getMaxDeposits() == 150
    assert contracts.deposit_security_module.getMinDepositBlockDistance() == 1200

    assert contracts.deposit_security_module.getGuardians() == guardians
    assert contracts.deposit_security_module.getGuardianQuorum() == 1

    for guardian in guardians:
        assert contracts.deposit_security_module.getGuardianIndex(guardian) >= 0
        assert contracts.deposit_security_module.isGuardian(guardian) == True

    assert contracts.deposit_security_module.getPauseIntentValidityPeriodBlocks() == 10

def test_el_rewards_vault_state():
    # address in locator
    assert contracts.lido_locator.elRewardsVault() == contracts.execution_layer_rewards_vault

    # Constants
    assert contracts.execution_layer_rewards_vault.LIDO() == contracts.lido
    assert contracts.execution_layer_rewards_vault.TREASURY() == contracts.agent
