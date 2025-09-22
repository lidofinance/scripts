import pytest
from brownie import interface, reverts  # type: ignore

from configs.config_mainnet import (
    CS_MODULE_ID, CS_MODULE_MODULE_FEE_BP,
    CS_MODULE_TREASURY_FEE_BP, CS_MODULE_TARGET_SHARE_BP, CS_MODULE_NAME, CS_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD,
    CS_MODULE_MAX_DEPOSITS_PER_BLOCK, CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
)
from utils.config import (
    contracts,
    STAKING_ROUTER,
    STAKING_ROUTER_IMPL,
    STAKING_ROUTER_VERSION,
    CHAIN_DEPOSIT_CONTRACT,
    WITHDRAWAL_VAULT,
    SR_MODULES_FEE_BP,
    SR_TREASURY_FEE_BP,
    SR_MODULES_FEE_E20,
    SR_TREASURY_FEE_E20,
    SR_BASE_PRECISION_E20,
    CURATED_STAKING_MODULE_NAME,
    CURATED_STAKING_MODULE_ID,
    CURATED_STAKING_MODULE_TARGET_SHARE_BP,
    CURATED_STAKING_MODULE_MODULE_FEE_BP,
    CURATED_STAKING_MODULE_TREASURY_FEE_BP,
    CURATED_STAKING_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD,
    CURATED_STAKING_MODULE_MAX_DEPOSITS_PER_BLOCK,
    CURATED_STAKING_MODULE_MIN_DEPOSITS_BLOCK_DISTANCE,
    WITHDRAWAL_CREDENTIALS,
    SIMPLE_DVT_MODULE_ID,
    SIMPLE_DVT_MODULE_MODULE_FEE_BP,
    SIMPLE_DVT_MODULE_NAME,
    SIMPLE_DVT_MODULE_TARGET_SHARE_BP,
    SIMPLE_DVT_MODULE_TREASURY_FEE_BP,
    SIMPLE_DVT_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD,
    SIMPLE_DVT_MODULE_MAX_DEPOSITS_PER_BLOCK,
    SIMPLE_DVT_MODULE_MIN_DEPOSITS_BLOCK_DISTANCE

)
from utils.evm_script import encode_error


@pytest.fixture(scope="module")
def contract() -> interface.StakingRouter:
    return interface.StakingRouter(STAKING_ROUTER)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == STAKING_ROUTER_IMPL
    assert proxy.proxy__getAdmin() == contracts.agent.address


def test_links(contract):
    assert contract.getLido() == contracts.lido
    assert contract.DEPOSIT_CONTRACT() == CHAIN_DEPOSIT_CONTRACT


def test_versioned(contract):
    assert contract.getContractVersion() == STAKING_ROUTER_VERSION


def test_initialize(contract):
    with reverts(encode_error("NonZeroContractVersionOnInit()")):
        contract.initialize(
            contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0),
            contracts.lido,
            WITHDRAWAL_CREDENTIALS,
            {"from": contracts.voting},
        )

def test_finalize_upgrade(contract):
    with reverts(encode_error(
                "UnexpectedContractVersion(uint256,uint256)",
                [3, 2],
            )):
        contract.finalizeUpgrade_v3(
            {"from": contracts.voting},
        )

def test_petrified(contract):
    impl = interface.StakingRouter(STAKING_ROUTER_IMPL)
    with reverts(encode_error("NonZeroContractVersionOnInit()")):
        impl.initialize(
            contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0),
            contracts.lido,
            WITHDRAWAL_CREDENTIALS,
            {"from": contracts.voting},
        )


def test_constants(contract):
    assert contract.FEE_PRECISION_POINTS() == 100 * 10**18
    assert contract.MAX_STAKING_MODULES_COUNT() == 32
    assert contract.MAX_STAKING_MODULE_NAME_LENGTH() == 31
    assert contract.TOTAL_BASIS_POINTS() == 10000


def test_staking_modules(contract):
    assert contract.getStakingModulesCount() == 3

    assert contract.getStakingModuleIds() == [CURATED_STAKING_MODULE_ID, SIMPLE_DVT_MODULE_ID, CS_MODULE_ID]
    assert contract.getStakingModuleIsActive(CURATED_STAKING_MODULE_ID) == True
    assert contract.getStakingModuleIsStopped(CURATED_STAKING_MODULE_ID) == False
    assert contract.getStakingModuleIsDepositsPaused(CURATED_STAKING_MODULE_ID) == False
    assert contract.getStakingModuleNonce(CURATED_STAKING_MODULE_ID) >= 7260
    assert contract.getStakingModuleStatus(CURATED_STAKING_MODULE_ID) == 0

    assert contract.getStakingModuleIsActive(SIMPLE_DVT_MODULE_ID) == True
    assert contract.getStakingModuleIsStopped(SIMPLE_DVT_MODULE_ID) == False
    assert contract.getStakingModuleIsDepositsPaused(SIMPLE_DVT_MODULE_ID) == False
    assert contract.getStakingModuleNonce(SIMPLE_DVT_MODULE_ID) >= 0
    assert contract.getStakingModuleStatus(SIMPLE_DVT_MODULE_ID) == 0

    assert contract.getStakingModuleIsActive(CS_MODULE_ID) == True
    assert contract.getStakingModuleIsStopped(CS_MODULE_ID) == False
    assert contract.getStakingModuleIsDepositsPaused(CS_MODULE_ID) == False
    assert contract.getStakingModuleNonce(CS_MODULE_ID) >= 0
    assert contract.getStakingModuleStatus(CS_MODULE_ID) == 0

    curated_module = contract.getStakingModule(CURATED_STAKING_MODULE_ID)
    assert curated_module["id"] == CURATED_STAKING_MODULE_ID
    assert curated_module["stakingModuleAddress"] == contracts.node_operators_registry
    assert curated_module["stakingModuleFee"] == CURATED_STAKING_MODULE_MODULE_FEE_BP
    assert curated_module["treasuryFee"] == CURATED_STAKING_MODULE_TREASURY_FEE_BP
    assert curated_module["stakeShareLimit"] == CURATED_STAKING_MODULE_TARGET_SHARE_BP
    assert curated_module["status"] == 0
    assert curated_module["name"] == CURATED_STAKING_MODULE_NAME
    assert curated_module["lastDepositAt"] >= 1679672628
    assert curated_module["lastDepositBlock"] >= 8705383
    assert curated_module["exitedValidatorsCount"] >= 145
    assert curated_module["priorityExitShareThreshold"] == CURATED_STAKING_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD
    assert curated_module["maxDepositsPerBlock"] == CURATED_STAKING_MODULE_MAX_DEPOSITS_PER_BLOCK
    assert curated_module["minDepositBlockDistance"] == CURATED_STAKING_MODULE_MIN_DEPOSITS_BLOCK_DISTANCE

    simple_dvt_module = contract.getStakingModule(SIMPLE_DVT_MODULE_ID)
    assert simple_dvt_module["id"] == SIMPLE_DVT_MODULE_ID
    assert simple_dvt_module["stakingModuleAddress"] == contracts.simple_dvt
    assert simple_dvt_module["stakingModuleFee"] == SIMPLE_DVT_MODULE_MODULE_FEE_BP
    assert simple_dvt_module["treasuryFee"] == SIMPLE_DVT_MODULE_TREASURY_FEE_BP
    assert simple_dvt_module["stakeShareLimit"] == SIMPLE_DVT_MODULE_TARGET_SHARE_BP
    assert simple_dvt_module["status"] == 0
    assert simple_dvt_module["name"] == SIMPLE_DVT_MODULE_NAME
    assert simple_dvt_module["lastDepositAt"] > 0
    assert simple_dvt_module["lastDepositBlock"] > 0
    assert simple_dvt_module["exitedValidatorsCount"] >= 0
    assert simple_dvt_module["priorityExitShareThreshold"] == SIMPLE_DVT_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD
    assert simple_dvt_module["maxDepositsPerBlock"] == SIMPLE_DVT_MODULE_MAX_DEPOSITS_PER_BLOCK
    assert simple_dvt_module["minDepositBlockDistance"] == SIMPLE_DVT_MODULE_MIN_DEPOSITS_BLOCK_DISTANCE

    community_staking_module = contract.getStakingModule(CS_MODULE_ID)
    assert community_staking_module["id"] == CS_MODULE_ID
    assert community_staking_module["stakingModuleAddress"] == contracts.csm
    assert community_staking_module["stakingModuleFee"] == CS_MODULE_MODULE_FEE_BP
    assert community_staking_module["treasuryFee"] == CS_MODULE_TREASURY_FEE_BP
    assert community_staking_module["stakeShareLimit"] == CS_MODULE_TARGET_SHARE_BP
    assert community_staking_module["status"] == 0
    assert community_staking_module["name"] == CS_MODULE_NAME
    assert community_staking_module["lastDepositAt"] > 0
    assert community_staking_module["lastDepositBlock"] > 0
    assert community_staking_module["exitedValidatorsCount"] >= 0
    assert community_staking_module["priorityExitShareThreshold"] == CS_MODULE_PRIORITY_EXIT_SHARE_THRESHOLD
    assert community_staking_module["maxDepositsPerBlock"] == CS_MODULE_MAX_DEPOSITS_PER_BLOCK
    assert community_staking_module["minDepositBlockDistance"] == CS_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE

    fee_aggregate_distribution = contract.getStakingFeeAggregateDistribution()
    assert fee_aggregate_distribution["modulesFee"] <= SR_MODULES_FEE_E20
    assert fee_aggregate_distribution["treasuryFee"] >= SR_TREASURY_FEE_E20
    assert fee_aggregate_distribution["basePrecision"] == SR_BASE_PRECISION_E20

    fee_aggregate_distribution_e4 = contract.getStakingFeeAggregateDistributionE4Precision()
    assert fee_aggregate_distribution_e4["modulesFee"] <= SR_MODULES_FEE_BP
    assert fee_aggregate_distribution_e4["treasuryFee"] >= SR_TREASURY_FEE_BP

    assert contract.getTotalFeeE4Precision() <= 1000

    assert contract.getStakingModuleActiveValidatorsCount(1) >= 3521

    assert contract.getWithdrawalCredentials().hex().startswith("01")
    assert contract.getWithdrawalCredentials().hex().endswith(WITHDRAWAL_VAULT[2:].lower())
    assert f"0x{contract.getWithdrawalCredentials().hex()}" == WITHDRAWAL_CREDENTIALS
