"""
Acceptance tests for TopUpGateway — a new contract added by the SRv3 upgrade
(deployed as an OssifiableProxy, wired into the upgraded LidoLocator).

Vote impact:
- coreUpgrade deploys the proxy with the UpgradeTemporaryAdmin as initial admin;
  initialize() sets the limits from upgrade-params-mainnet.toml [topUpGateway];
- UpgradeTemporaryAdmin grants PAUSE_ROLE to the CircuitBreaker and ResealManager,
  RESUME_ROLE to the ResealManager, TOP_UP_ROLE to the depositor, then hands
  DEFAULT_ADMIN_ROLE over to the Agent (see UpgradeTemplate._assert* checks);
- the vote registers the CircuitBreaker pauser for the gateway (item 1.18-adjacent,
  "Register CircuitBreaker pauser for TopUpGateway").
"""
import pytest
from brownie import interface, reverts, web3  # type: ignore
from brownie.convert.datatypes import HexString

from utils.config import (
    contracts,
    AGENT,
    CIRCUIT_BREAKER,
    RESEAL_MANAGER,
    CHAIN_SLOTS_PER_EPOCH,
    TOP_UP_GATEWAY,
    TOP_UP_GATEWAY_IMPL,
    TOP_UP_GATEWAY_DEPOSITOR,
    TOP_UP_GATEWAY_MAX_VALIDATORS_PER_TOP_UP,
    TOP_UP_GATEWAY_MIN_BLOCK_DISTANCE,
    TOP_UP_GATEWAY_MAX_ROOT_AGE,
    TOP_UP_GATEWAY_TARGET_BALANCE_GWEI,
    TOP_UP_GATEWAY_MIN_TOP_UP_GWEI,
)
from utils.evm_script import encode_error
from utils.test.helpers import access_control_unauthorized as unauthorized

DEFAULT_ADMIN_ROLE = "0x" + "00" * 32

# An empty TopUpData tuple, field order per the ABI:
# (moduleId, keyIndices, operatorIds, validatorIndices, beaconRootData, validatorWitness, pendingBalanceGwei)
EMPTY_TOP_UP_DATA = (0, [], [], [], (0, 0, 0), [], [])


@pytest.fixture(scope="module")
def contract() -> interface.TopUpGateway:
    return interface.TopUpGateway(TOP_UP_GATEWAY)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == TOP_UP_GATEWAY_IMPL
    assert proxy.proxy__getAdmin() == AGENT


def test_immutables(contract):
    # constructor args (impl): locator, gIndices, pivot slot, slots per epoch
    assert contract.SLOTS_PER_EPOCH() == CHAIN_SLOTS_PER_EPOCH
    assert contract.PIVOT_SLOT() == 0
    assert contract.GI_FIRST_VALIDATOR_PREV() == HexString(
        "0x0000000000000000000000000000000000000000000000000056000000000028", "bytes"
    )
    assert contract.GI_FIRST_VALIDATOR_CURR() == HexString(
        "0x0000000000000000000000000000000000000000000000000096000000000028", "bytes"
    )


def test_locator_wiring(contract):
    assert contracts.lido_locator.topUpGateway() == contract.address


def test_initialize(contract):
    # already initialized by the proxy constructor calldata
    # .call() — anvil does not surface custom-error data for reverted txs
    with reverts(encode_error("InvalidInitialization()")):
        contract.initialize.call(
            AGENT,
            TOP_UP_GATEWAY_MAX_VALIDATORS_PER_TOP_UP,
            TOP_UP_GATEWAY_MIN_BLOCK_DISTANCE,
            TOP_UP_GATEWAY_MAX_ROOT_AGE,
            TOP_UP_GATEWAY_TARGET_BALANCE_GWEI,
            TOP_UP_GATEWAY_MIN_TOP_UP_GWEI,
            {"from": contracts.voting},
        )


def test_petrified(contract):
    # the implementation calls _disableInitializers() in the constructor
    impl = interface.TopUpGateway(TOP_UP_GATEWAY_IMPL)
    with reverts(encode_error("InvalidInitialization()")):
        impl.initialize.call(
            AGENT,
            TOP_UP_GATEWAY_MAX_VALIDATORS_PER_TOP_UP,
            TOP_UP_GATEWAY_MIN_BLOCK_DISTANCE,
            TOP_UP_GATEWAY_MAX_ROOT_AGE,
            TOP_UP_GATEWAY_TARGET_BALANCE_GWEI,
            TOP_UP_GATEWAY_MIN_TOP_UP_GWEI,
            {"from": contracts.voting},
        )


def test_limits(contract):
    # values set by initialize() from upgrade-params-mainnet.toml [topUpGateway]
    assert contract.getMaxValidatorsPerTopUp() == TOP_UP_GATEWAY_MAX_VALIDATORS_PER_TOP_UP
    assert contract.getMinBlockDistance() == TOP_UP_GATEWAY_MIN_BLOCK_DISTANCE
    assert contract.getMaxRootAge() == TOP_UP_GATEWAY_MAX_ROOT_AGE
    assert contract.getTargetBalanceGwei() == TOP_UP_GATEWAY_TARGET_BALANCE_GWEI
    assert contract.getMinTopUpGwei() == TOP_UP_GATEWAY_MIN_TOP_UP_GWEI


def test_initial_state(contract):
    assert not contract.isPaused()
    # no top-ups have happened yet
    assert contract.getLastTopUpTimestamp() == 0
    assert contract.isBlockDistancePassed()


def test_roles(contract):
    """Mirrors UpgradeTemplate post-upgrade checks (_assertSingleOZRoleHolder & co)."""
    top_up_role = web3.keccak(text="TOP_UP_ROLE")
    manage_limits_role = web3.keccak(text="MANAGE_LIMITS_ROLE")
    pause_role = web3.keccak(text="PAUSE_ROLE")
    resume_role = web3.keccak(text="RESUME_ROLE")

    # DEFAULT_ADMIN_ROLE: only the Agent (temporary admin renounced)
    assert contract.getRoleMemberCount(DEFAULT_ADMIN_ROLE) == 1
    assert contract.getRoleMember(DEFAULT_ADMIN_ROLE, 0) == AGENT

    # PAUSE_ROLE: CircuitBreaker + ResealManager
    assert contract.getRoleMemberCount(pause_role) == 2
    assert {
        contract.getRoleMember(pause_role, 0),
        contract.getRoleMember(pause_role, 1),
    } == {CIRCUIT_BREAKER, RESEAL_MANAGER}

    # RESUME_ROLE: only the ResealManager
    assert contract.getRoleMemberCount(resume_role) == 1
    assert contract.getRoleMember(resume_role, 0) == RESEAL_MANAGER

    # TOP_UP_ROLE: only the depositor
    assert contract.getRoleMemberCount(top_up_role) == 1
    assert contract.getRoleMember(top_up_role, 0) == TOP_UP_GATEWAY_DEPOSITOR

    # MANAGE_LIMITS_ROLE: not granted to anyone by the upgrade
    assert contract.getRoleMemberCount(manage_limits_role) == 0


def test_acl(contract, stranger):
    # .call() — anvil does not surface custom-error data for reverted txs
    # the main gated entry point (TOP_UP_ROLE, depositor-only)
    with reverts(unauthorized(stranger, "TOP_UP_ROLE")):
        contract.topUp.call(EMPTY_TOP_UP_DATA, {"from": stranger})

    # NB: MANAGE_LIMITS_ROLE has no holders, so these revert for anyone;
    # kept as a smoke check that the setters are not open
    with reverts(unauthorized(stranger, "MANAGE_LIMITS_ROLE")):
        contract.setMaxValidatorsPerTopUp.call(1, {"from": stranger})

    with reverts(unauthorized(stranger, "MANAGE_LIMITS_ROLE")):
        contract.setMinBlockDistance.call(1, {"from": stranger})

    with reverts(unauthorized(stranger, "MANAGE_LIMITS_ROLE")):
        contract.setTopUpBalanceLimits.call(1, 1, {"from": stranger})

    with reverts(unauthorized(stranger, "MANAGE_LIMITS_ROLE")):
        contract.setMaxRootAge.call(1, {"from": stranger})

    # 1 sec: a zero duration would revert with ZeroPauseDuration instead
    with reverts(unauthorized(stranger, "PAUSE_ROLE")):
        contract.pauseFor.call(1, {"from": stranger})

    with reverts(unauthorized(stranger, "RESUME_ROLE")):
        contract.resume.call({"from": stranger})
