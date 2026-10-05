import pytest
from brownie import ZERO_ADDRESS, convert, interface, web3

from scripts.vote_csm0x02 import start_vote
from utils.mainnet_fork import pass_and_exec_dao_vote


# Mainnet governance
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"

# Vote targets
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
BURNER = "0xE76c52750019b80B43E36DF30bf4060EB73F573a"
TRIGGERABLE_WITHDRAWALS_GATEWAY = "0xDC00116a0D3E064427dA2600449cfD2566B3037B"
CIRCUIT_BREAKER = "0x6019CB557978296BA3C08a7B73225C0975DFB2F7"
CSM_COMMITTEE = "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f"

TODO_ADDRESS = "TODO"

# https://github.com/lidofinance/staking-modules/pull/899
CSM0X02 = "0x792Cd25e4aE3578375031FB55e048E163A804F7B"
CSM0X02_ACCOUNTING = "0x3696dDd942A9e156F5D4728505D1b9a32dCef900"
CSM0X02_FEE_ORACLE = "0x0fB5EC09Cc975d8E1aF43063e51882798814f311"
CSM0X02_HASH_CONSENSUS = "0xd5a965FAab2d02D3cC2286A9da42d09F0F2aE210"
CSM0X02_VERIFIER = "0x69b4C32a43565e768794D41b4A265F86dE61b861"
CSM0X02_EJECTOR = "0x2EE500885870b020e84E86a09A5d26D1EEec3E5E"

# https://github.com/lidofinance/easy-track/pull/139#pullrequestreview-5410616152
REPORT_WITHDRAWALS_FACTORY = "0x8D74020d8EACCdFf0366dAAFfb96e6c98CDFc112"
SETTLE_GENERAL_DELAYED_PENALTY_FACTORY = "0x0B676AdEABcf4A696187cfAb90290Aa3ac51aFA2"
UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x5b0De22E65C068430f6e769754D51133775408cc"

DEPLOYMENT_ADDRESSES = [
    CSM0X02,
    CSM0X02_ACCOUNTING,
    CSM0X02_FEE_ORACLE,
    CSM0X02_HASH_CONSENSUS,
    CSM0X02_VERIFIER,
    CSM0X02_EJECTOR,
    REPORT_WITHDRAWALS_FACTORY,
    SETTLE_GENERAL_DELAYED_PENALTY_FACTORY,
    UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
]

# Expected deployment parameters are deliberately independent from the vote script.
CSM0X02_NAME = "Community Staking 0x02"
CSM0X02_TARGET_SHARE_BP = 200
CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 240
CSM0X02_MODULE_FEE_BP = 200
CSM0X02_TREASURY_FEE_BP = 800
CSM0X02_MAX_DEPOSITS_PER_BLOCK = 30
CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE = 0x02

CURATED_V1_MODULE_ID = 1
CURATED_V2_MODULE_ID = 4
CONSENSYS_V1_NODE_OPERATOR_ID = 21
CONSENSYS_V2_NODE_OPERATOR_ID = 6
CURATED_V1_ADDRESS = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
CURATED_V2_ADDRESS = "0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1"

# TODO: Calculate for the expected mainnet vote date after a complete oracle frame.
CSM0X02_ORACLE_INITIAL_EPOCH = 0


def _selector(signature: str) -> str:
    return web3.keccak(text=signature).hex()[:10]


def _permission(contract_address: str, signature: str) -> str:
    return convert.to_address(contract_address).lower() + _selector(signature).removeprefix("0x")


def _assert_module_config(staking_router, module_id: int) -> None:
    module = staking_router.getStakingModuleStateConfig(module_id)

    assert staking_router.getStakingModule(module_id)["name"] == CSM0X02_NAME
    assert module["moduleAddress"] == CSM0X02
    assert module["stakeShareLimit"] == CSM0X02_TARGET_SHARE_BP
    assert module["priorityExitShareThreshold"] == CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP
    assert module["moduleFee"] == CSM0X02_MODULE_FEE_BP
    assert module["treasuryFee"] == CSM0X02_TREASURY_FEE_BP
    assert module["withdrawalCredentialsType"] == CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE
    assert staking_router.getStakingModuleMaxDepositsPerBlock(module_id) == CSM0X02_MAX_DEPOSITS_PER_BLOCK
    assert staking_router.getStakingModuleMinDepositBlockDistance(module_id) == CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE


@pytest.mark.skipif(
    TODO_ADDRESS in DEPLOYMENT_ADDRESSES or CSM0X02_ORACLE_INITIAL_EPOCH <= 0,
    reason="Set mainnet CSM 0x02 deployment addresses and initial oracle epoch",
)
def test_vote(ldo_holder):
    easy_track = interface.EasyTrack(EASY_TRACK)

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    burner = interface.Burner(BURNER)
    twg = interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)
    csm = interface.CSModule(CSM0X02)
    hash_consensus = interface.HashConsensus(CSM0X02_HASH_CONSENSUS)
    curated_v1 = interface.NodeOperatorsRegistry(CURATED_V1_ADDRESS)
    curated_v2 = interface.CuratedModule(CURATED_V2_ADDRESS)

    curated_v1_config_before = staking_router.getStakingModuleStateConfig(CURATED_V1_MODULE_ID).dict()
    curated_v1_deposits_before = staking_router.getStakingModuleStateDeposits(CURATED_V1_MODULE_ID).dict()
    assert curated_v1.getNodeOperator(CONSENSYS_V1_NODE_OPERATOR_ID, True)["name"] == "Consensys"
    assert curated_v2.getNodeOperator(CONSENSYS_V2_NODE_OPERATOR_ID)["managerAddress"] == (
        "0xF45C77EadD434612fCD93db978B3E36B0D58eC99"
    )

    factories = [
        REPORT_WITHDRAWALS_FACTORY,
        SETTLE_GENERAL_DELAYED_PENALTY_FACTORY,
        UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
    ]
    factory_permissions = [
        _permission(CSM0X02, "reportSlashedWithdrawnValidators((uint256,uint256,uint256,uint256,bool)[])"),
        _permission(CSM0X02, "settleGeneralDelayedPenalty(uint256[],uint256[])"),
        (
            _permission(UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY, "validateParams((uint16,uint16,uint16,uint16))")
            + _permission(STAKING_ROUTER, "updateModuleShares(uint256,uint16,uint16)")[2:]
        ),
    ]
    circuit_breaker_targets = [CSM0X02, CSM0X02_ACCOUNTING, CSM0X02_FEE_ORACLE, CSM0X02_VERIFIER, CSM0X02_EJECTOR]

    modules_count_before = staking_router.getStakingModulesCount()
    module_id = modules_count_before + 1

    # The deployment contracts exist, but none of the activation effects is applied yet.
    assert not staking_router.hasStakingModule(module_id)
    assert not burner.hasRole(burner.REQUEST_BURN_MY_STETH_ROLE(), CSM0X02_ACCOUNTING)
    assert not twg.hasRole(twg.ADD_FULL_WITHDRAWAL_REQUEST_ROLE(), CSM0X02_EJECTOR)
    assert csm.isPaused()
    assert not csm.hasRole(csm.RESUME_ROLE(), AGENT)
    assert hash_consensus.getFrameConfig()[0] != CSM0X02_ORACLE_INITIAL_EPOCH
    for target in circuit_breaker_targets:
        assert circuit_breaker.getPauser(target) == ZERO_ADDRESS
    for factory in factories:
        assert factory not in easy_track.getEVMScriptFactories()

    vote_id, _ = start_vote({"from": ldo_holder}, silent=True)
    pass_and_exec_dao_vote(vote_id)

    for factory, permissions in zip(factories, factory_permissions):
        assert factory in easy_track.getEVMScriptFactories()
        assert bytes(easy_track.evmScriptFactoryPermissions(factory)) == bytes.fromhex(permissions.removeprefix("0x"))

    assert staking_router.getStakingModulesCount() == module_id
    assert staking_router.hasStakingModule(module_id)
    _assert_module_config(staking_router, module_id)

    curated_v1_config_after = staking_router.getStakingModuleStateConfig(CURATED_V1_MODULE_ID).dict()
    assert curated_v1_config_after == {**curated_v1_config_before, "stakeShareLimit": 0}
    curated_v1_deposits_after = staking_router.getStakingModuleStateDeposits(CURATED_V1_MODULE_ID).dict()
    assert curated_v1_deposits_after["maxDepositsPerBlock"] == curated_v1_deposits_before["maxDepositsPerBlock"]
    assert curated_v1_deposits_after["minDepositBlockDistance"] == curated_v1_deposits_before["minDepositBlockDistance"]
    for module, operator_id in (
        (curated_v1, CONSENSYS_V1_NODE_OPERATOR_ID),
        (curated_v2, CONSENSYS_V2_NODE_OPERATOR_ID),
    ):
        operator = module.getNodeOperatorSummary(operator_id)
        assert operator["targetLimitMode"] == 1
        assert operator["targetValidatorsCount"] == 0
        assert operator["depositableValidatorsCount"] == 0

    assert burner.hasRole(burner.REQUEST_BURN_MY_STETH_ROLE(), CSM0X02_ACCOUNTING)
    assert twg.hasRole(twg.ADD_FULL_WITHDRAWAL_REQUEST_ROLE(), CSM0X02_EJECTOR)
    assert not csm.isPaused()
    assert not csm.hasRole(csm.RESUME_ROLE(), AGENT)
    assert hash_consensus.getFrameConfig()[0] == CSM0X02_ORACLE_INITIAL_EPOCH
    for target in circuit_breaker_targets:
        assert circuit_breaker.getPauser(target) == CSM_COMMITTEE
