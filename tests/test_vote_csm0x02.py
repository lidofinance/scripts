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

CSM0X02 = TODO_ADDRESS
CSM0X02_ACCOUNTING = TODO_ADDRESS
CSM0X02_FEE_ORACLE = TODO_ADDRESS
CSM0X02_HASH_CONSENSUS = TODO_ADDRESS
CSM0X02_VERIFIER = TODO_ADDRESS
CSM0X02_EJECTOR = TODO_ADDRESS

REPORT_WITHDRAWALS_FACTORY = TODO_ADDRESS
SETTLE_GENERAL_DELAYED_PENALTY_FACTORY = TODO_ADDRESS
UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = TODO_ADDRESS

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
CSM0X02_TARGET_SHARE_BP = 900
CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 1_080
CSM0X02_MODULE_FEE_BP = 600
CSM0X02_TREASURY_FEE_BP = 400
CSM0X02_MAX_DEPOSITS_PER_BLOCK = 30
CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE = 0x02

# TODO: Calculate for the expected mainnet vote date after a complete oracle frame.
CSM0X02_ORACLE_INITIAL_EPOCH = 0


def _selector(signature: str) -> str:
    return web3.keccak(text=signature).hex()[:10]


def _permission(contract_address: str, signature: str) -> str:
    return convert.to_address(contract_address).lower() + _selector(signature).removeprefix("0x")


def _assert_module_config(staking_router, module_id: int) -> None:
    module = staking_router.getStakingModuleStateConfig(module_id)

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

    factories = [
        REPORT_WITHDRAWALS_FACTORY,
        SETTLE_GENERAL_DELAYED_PENALTY_FACTORY,
        UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
    ]
    factory_permissions = [
        _permission(CSM0X02, "reportSlashedWithdrawnValidators((uint256,uint256,uint256,uint256,bool)[])"),
        _permission(CSM0X02, "settleGeneralDelayedPenalty(uint256[],uint256[])"),
        _permission(STAKING_ROUTER, "updateStakingModule(uint256,uint256,uint256,uint256,uint256,uint256,uint256)"),
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

    assert burner.hasRole(burner.REQUEST_BURN_MY_STETH_ROLE(), CSM0X02_ACCOUNTING)
    assert twg.hasRole(twg.ADD_FULL_WITHDRAWAL_REQUEST_ROLE(), CSM0X02_EJECTOR)
    assert not csm.isPaused()
    assert not csm.hasRole(csm.RESUME_ROLE(), AGENT)
    assert hash_consensus.getFrameConfig()[0] == CSM0X02_ORACLE_INITIAL_EPOCH
    for target in circuit_breaker_targets:
        assert circuit_breaker.getPauser(target) == CSM_COMMITTEE
