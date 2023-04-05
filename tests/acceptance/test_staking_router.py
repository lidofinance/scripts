import pytest
from brownie import interface  # type: ignore

from utils.config import contracts, lido_dao_staking_router, deposit_contract, lido_dao_withdrawal_vault


@pytest.fixture(scope="module")
def contract() -> interface.StakingRouter:
    return interface.StakingRouter(lido_dao_staking_router)


def test_links(contract):
    assert contract.getLido() == contracts.lido
    assert contract.DEPOSIT_CONTRACT() == deposit_contract


def test_versioned(contract):
    assert contract.getContractVersion() == 1


def test_constants(contract):
    assert contract.FEE_PRECISION_POINTS() == 100 * 10**18
    assert contract.MAX_STAKING_MODULES_COUNT() == 32
    assert contract.MAX_STAKING_MODULE_NAME_LENGTH() == 31
    assert contract.TOTAL_BASIS_POINTS() == 10000


def test_staking_modules(contract):
    assert contract.getStakingModulesCount() == 1

    assert contract.getStakingModuleIds() == [1]
    assert contract.getStakingModuleIsActive(1) == True
    assert contract.getStakingModuleIsStopped(1) == False
    assert contract.getStakingModuleIsDepositsPaused(1) == False
    assert contract.getStakingModuleNonce(1) >= 7260
    assert contract.getStakingModuleStatus(1) == 0

    curated_module = contract.getStakingModule(1)
    assert curated_module["id"] == 1
    assert curated_module["stakingModuleAddress"] == contracts.node_operators_registry
    assert curated_module["stakingModuleFee"] == 500
    assert curated_module["treasuryFee"] == 500
    assert curated_module["targetShare"] == 10000
    assert curated_module["status"] == 0
    assert curated_module["name"] == "curated-onchain-v1"
    assert curated_module["lastDepositAt"] >= 1679672628
    assert curated_module["lastDepositBlock"] >= 8705383
    assert curated_module["exitedValidatorsCount"] == 0

    fee_aggregate_distribution = contract.getStakingFeeAggregateDistribution()
    assert fee_aggregate_distribution["modulesFee"] == 5 * 10**18
    assert fee_aggregate_distribution["treasuryFee"] == 5 * 10**18
    assert fee_aggregate_distribution["basePrecision"] == 100 * 10**18

    fee_aggregate_distribution = contract.getStakingFeeAggregateDistribution()
    assert fee_aggregate_distribution["modulesFee"] == 5 * 10**18
    assert fee_aggregate_distribution["treasuryFee"] == 5 * 10**18
    assert fee_aggregate_distribution["basePrecision"] == 100 * 10**18

    fee_aggregate_distribution_e4 = contract.getStakingFeeAggregateDistributionE4Precision()
    assert fee_aggregate_distribution_e4["modulesFee"] == 500
    assert fee_aggregate_distribution_e4["treasuryFee"] == 500

    assert contract.getTotalFeeE4Precision() == 1000

    assert contract.getStakingModuleActiveValidatorsCount(1) >= 3521

    assert contract.getWithdrawalCredentials().hex().startswith("01")
    assert contract.getWithdrawalCredentials().hex().endswith(lido_dao_withdrawal_vault[2:].lower())
