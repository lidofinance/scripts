import pytest
from brownie import interface, web3  # type: ignore

from utils.config import (
    AGENT,
    CIRCUIT_BREAKER,
    CIRCUIT_BREAKER_COMMITTEE,
    CIRCUIT_BREAKER_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MAX_PAUSE_DURATION,
    CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MIN_PAUSE_DURATION,
    CIRCUIT_BREAKER_PAUSE_DURATION,
    CONSOLIDATION_GATEWAY,
    CS_ACCOUNTING_ADDRESS,
    CS_EJECTOR_ADDRESS,
    CS_FEE_ORACLE_ADDRESS,
    CS_IDENTIFIED_DVT_CLUSTER_GATE_ADDRESS,
    CS_VERIFIER_ADDRESS,
    CS_VETTED_GATE_ADDRESS,
    CSM_ADDRESS,
    CSM_COMMITTEE_MS,
    CURATED_V2_ACCOUNTING,
    CURATED_V2_CIRCUIT_BREAKER_PAUSER,
    CURATED_V2_EJECTOR,
    CURATED_V2_FEE_ORACLE,
    CURATED_V2_STAKING_MODULE_ADDRESS,
    CURATED_V2_VERIFIER,
    GATE_SEAL_COMMITTEE,
    PREDEPOSIT_GUARANTEE,
    RESEAL_MANAGER,
    TOP_UP_GATEWAY,
    TRIGGERABLE_WITHDRAWALS_GATEWAY,
    VALIDATORS_EXIT_BUS_ORACLE,
    VAULT_HUB,
    WITHDRAWAL_QUEUE,
)


EXPECTED_PAUSABLES = [
    (WITHDRAWAL_QUEUE, GATE_SEAL_COMMITTEE),
    (VALIDATORS_EXIT_BUS_ORACLE, GATE_SEAL_COMMITTEE),
    (TRIGGERABLE_WITHDRAWALS_GATEWAY, GATE_SEAL_COMMITTEE),
    (VAULT_HUB, GATE_SEAL_COMMITTEE),
    (PREDEPOSIT_GUARANTEE, GATE_SEAL_COMMITTEE),
    (CONSOLIDATION_GATEWAY, CIRCUIT_BREAKER_COMMITTEE),
    (TOP_UP_GATEWAY, CIRCUIT_BREAKER_COMMITTEE),
    (CSM_ADDRESS, CSM_COMMITTEE_MS),
    (CS_ACCOUNTING_ADDRESS, CSM_COMMITTEE_MS),
    (CS_FEE_ORACLE_ADDRESS, CSM_COMMITTEE_MS),
    (CS_VERIFIER_ADDRESS, CSM_COMMITTEE_MS),
    (CS_VETTED_GATE_ADDRESS, CSM_COMMITTEE_MS),
    (CS_EJECTOR_ADDRESS, CSM_COMMITTEE_MS),
    (CS_IDENTIFIED_DVT_CLUSTER_GATE_ADDRESS, CSM_COMMITTEE_MS),
    (CURATED_V2_STAKING_MODULE_ADDRESS, CURATED_V2_CIRCUIT_BREAKER_PAUSER),
    (CURATED_V2_ACCOUNTING, CURATED_V2_CIRCUIT_BREAKER_PAUSER),
    (CURATED_V2_FEE_ORACLE, CURATED_V2_CIRCUIT_BREAKER_PAUSER),
    (CURATED_V2_VERIFIER, CURATED_V2_CIRCUIT_BREAKER_PAUSER),
    (CURATED_V2_EJECTOR, CURATED_V2_CIRCUIT_BREAKER_PAUSER),
]


@pytest.fixture(scope="module")
def circuit_breaker():
    return interface.CircuitBreaker(CIRCUIT_BREAKER)


def test_initial_values(circuit_breaker):
    assert circuit_breaker.ADMIN() == AGENT, f"ADMIN: expected {AGENT}, got {circuit_breaker.ADMIN()}"

    assert (
        circuit_breaker.MIN_PAUSE_DURATION() == CIRCUIT_BREAKER_MIN_PAUSE_DURATION
    ), f"MIN_PAUSE_DURATION: expected {CIRCUIT_BREAKER_MIN_PAUSE_DURATION}, got {circuit_breaker.MIN_PAUSE_DURATION()}"
    assert (
        circuit_breaker.MAX_PAUSE_DURATION() == CIRCUIT_BREAKER_MAX_PAUSE_DURATION
    ), f"MAX_PAUSE_DURATION: expected {CIRCUIT_BREAKER_MAX_PAUSE_DURATION}, got {circuit_breaker.MAX_PAUSE_DURATION()}"
    assert (
        circuit_breaker.MIN_HEARTBEAT_INTERVAL() == CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL
    ), f"MIN_HEARTBEAT_INTERVAL: expected {CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL}, got {circuit_breaker.MIN_HEARTBEAT_INTERVAL()}"
    assert (
        circuit_breaker.MAX_HEARTBEAT_INTERVAL() == CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL
    ), f"MAX_HEARTBEAT_INTERVAL: expected {CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL}, got {circuit_breaker.MAX_HEARTBEAT_INTERVAL()}"
    assert (
        circuit_breaker.pauseDuration() == CIRCUIT_BREAKER_PAUSE_DURATION
    ), f"pauseDuration: expected {CIRCUIT_BREAKER_PAUSE_DURATION}, got {circuit_breaker.pauseDuration()}"
    assert (
        circuit_breaker.heartbeatInterval() == CIRCUIT_BREAKER_HEARTBEAT_INTERVAL
    ), f"heartbeatInterval: expected {CIRCUIT_BREAKER_HEARTBEAT_INTERVAL}, got {circuit_breaker.heartbeatInterval()}"

    assert (
        0 < CIRCUIT_BREAKER_MIN_PAUSE_DURATION <= CIRCUIT_BREAKER_PAUSE_DURATION <= CIRCUIT_BREAKER_MAX_PAUSE_DURATION
    ), (
        f"pause duration bounds broken: "
        f"min={CIRCUIT_BREAKER_MIN_PAUSE_DURATION}, "
        f"initial={CIRCUIT_BREAKER_PAUSE_DURATION}, "
        f"max={CIRCUIT_BREAKER_MAX_PAUSE_DURATION}"
    )
    assert (
        0
        < CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL
        <= CIRCUIT_BREAKER_HEARTBEAT_INTERVAL
        <= CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL
    ), (
        f"heartbeat interval bounds broken: "
        f"min={CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL}, "
        f"initial={CIRCUIT_BREAKER_HEARTBEAT_INTERVAL}, "
        f"max={CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL}"
    )


def test_pausables_set(circuit_breaker):
    actual = sorted(addr.lower() for addr in circuit_breaker.getPausables())
    expected = sorted(p.lower() for p, _ in EXPECTED_PAUSABLES)
    assert actual == expected, (
        f"pausables mismatch: missing {sorted(set(expected) - set(actual))}, "
        f"extra {sorted(set(actual) - set(expected))}"
    )


@pytest.mark.parametrize("pausable, expected_pauser", EXPECTED_PAUSABLES)
def test_pauser_assignment(circuit_breaker, pausable, expected_pauser):
    assert (
        circuit_breaker.getPauser(pausable).lower() == expected_pauser.lower()
    ), f"pauser for {pausable}: expected {expected_pauser}, got {circuit_breaker.getPauser(pausable)}"


def test_pausable_counts_per_pauser(circuit_breaker):
    expected_counts = {}
    for _, pauser in EXPECTED_PAUSABLES:
        expected_counts[pauser.lower()] = expected_counts.get(pauser.lower(), 0) + 1

    for pauser, expected in expected_counts.items():
        assert (
            circuit_breaker.getPausableCount(pauser) == expected
        ), f"pausable count for pauser {pauser}: expected {expected}, got {circuit_breaker.getPausableCount(pauser)}"


@pytest.mark.parametrize("pausable, _pauser", EXPECTED_PAUSABLES)
def test_pause_role_holders(_pauser, pausable):
    pausable_contract = interface.IPausableUntilWithRoles(pausable)
    pause_role = str(pausable_contract.PAUSE_ROLE())
    assert (
        pausable_contract.getRoleMemberCount(pause_role) == 2
    ), f"PAUSE_ROLE holder count on {pausable}: expected 2, got {pausable_contract.getRoleMemberCount(pause_role)}"
    holders = {
        pausable_contract.getRoleMember(pause_role, 0).lower(),
        pausable_contract.getRoleMember(pause_role, 1).lower(),
    }
    expected_holders = {CIRCUIT_BREAKER.lower(), RESEAL_MANAGER.lower()}
    assert (
        holders == expected_holders
    ), f"PAUSE_ROLE holders on {pausable}: expected {sorted(expected_holders)}, got {sorted(holders)}"


@pytest.mark.parametrize("pausable, _pauser", EXPECTED_PAUSABLES)
def test_resume_role_holder(_pauser, pausable):
    pausable_contract = interface.IPausableUntilWithRoles(pausable)
    resume_role = str(pausable_contract.RESUME_ROLE())
    assert (
        pausable_contract.getRoleMemberCount(resume_role) == 1
    ), f"RESUME_ROLE holder count on {pausable}: expected 1, got {pausable_contract.getRoleMemberCount(resume_role)}"
    assert (
        pausable_contract.getRoleMember(resume_role, 0).lower() == RESEAL_MANAGER.lower()
    ), f"RESUME_ROLE holder on {pausable}: expected {RESEAL_MANAGER}, got {pausable_contract.getRoleMember(resume_role, 0)}"


@pytest.mark.parametrize("pauser", sorted({p for _, p in EXPECTED_PAUSABLES}))
def test_pauser_is_live(circuit_breaker, pauser):
    assert circuit_breaker.isPauserLive(pauser), f"pauser {pauser} not live"
    expiry = circuit_breaker.heartbeatExpiry(pauser)
    block_timestamp = web3.eth.get_block("latest")["timestamp"]
    assert (
        expiry > block_timestamp
    ), f"pauser {pauser} heartbeat expired: expiry={expiry}, block.timestamp={block_timestamp}"
