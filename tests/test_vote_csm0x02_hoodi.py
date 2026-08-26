from brownie import ZERO_ADDRESS, convert, interface, web3

from scripts.vote_csm0x02_hoodi import start_vote
from utils.mainnet_fork import pass_and_exec_dao_vote


# Hoodi governance
AGENT = "0x0534aA41907c9631fae990960bCC72d75fA7cfeD"
EASY_TRACK = "0x284D91a7D47850d21A6DEaaC6E538AC7E5E6fc2a"

# Vote targets
STAKING_ROUTER = "0xCc820558B39ee15C7C45B59390B503b83fb499A8"
BURNER = "0xb2c99cd38a2636a6281a849C8de938B3eF4A7C3D"
TRIGGERABLE_WITHDRAWALS_GATEWAY = "0x6679090D92b08a2a686eF8614feECD8cDFE209db"
CIRCUIT_BREAKER = "0x44a5789dFeDa59cD176Ab5709ec2F4829dE4d555"
CSM_COMMITTEE = "0x4AF43Ee34a6fcD1fEcA1e1F832124C763561dA53"

CSM0X02 = "0xbb7dd81FAC80f3Effa10eA8b973c15AE65a4CAf9"
CSM0X02_ACCOUNTING = "0x04A0294bF3306532309D7DD776D4A7eF502313e0"
CSM0X02_FEE_ORACLE = "0x9B8bBA11bbE1a351CC8dD1CFCa6719FF7274A208"
CSM0X02_HASH_CONSENSUS = "0x41142D077860906B0A7Debb270f1B8e7d1c8BF34"
CSM0X02_VERIFIER = "0xFdE0FD9aDa4E898D3b34Dd4EA3433b75f0B6dd30"
CSM0X02_EJECTOR = "0xf8a71C08DBe7D2efaD76D3951a3065B8cE20e4f0"

REPORT_WITHDRAWALS_FACTORY = "0x0b384D661101Fe7F56caa421547b243e03ED4E65"
SETTLE_GENERAL_DELAYED_PENALTY_FACTORY = "0x2eCf179d5e840e56054E214438008F19E46711bC"
UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x05F2F2eb01A8e8C20FDD07EAb93640cd8304aaC9"

# Expected deployment parameters are deliberately independent from the vote script.
CSM0X02_TARGET_SHARE_BP = 1_600
CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 2_100
CSM0X02_MODULE_FEE_BP = 600
CSM0X02_TREASURY_FEE_BP = 400
CSM0X02_MAX_DEPOSITS_PER_BLOCK = 30
CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE = 0x02
CSM0X02_ORACLE_INITIAL_EPOCH = 121_738


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
