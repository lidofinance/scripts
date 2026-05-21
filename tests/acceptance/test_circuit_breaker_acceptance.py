import pytest
from brownie import interface, web3  # type: ignore

from utils.config import (
    AGENT,
    CIRCUIT_BREAKER,
    CIRCUIT_BREAKER_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MAX_PAUSE_DURATION,
    CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MIN_PAUSE_DURATION,
    CIRCUIT_BREAKER_PAUSE_DURATION,
    CS_ACCOUNTING_ADDRESS,
    CS_EJECTOR_ADDRESS,
    CS_FEE_ORACLE_ADDRESS,
    CS_VERIFIER_V2_ADDRESS,
    CS_VETTED_GATE_ADDRESS,
    CSM_ADDRESS,
    CSM_COMMITTEE_MS,
    GATE_SEAL_COMMITTEE,
    PREDEPOSIT_GUARANTEE,
    RESEAL_MANAGER,
    TRIGGERABLE_WITHDRAWALS_GATEWAY,
    VALIDATORS_EXIT_BUS_ORACLE,
    VAULT_HUB,
    WITHDRAWAL_QUEUE,
    contracts,
)




# Steady-state configuration: every pausable governed by CircuitBreaker and the
# multisig that may pause it. Pulled directly from LIP-34; no notion of "before
# the migration vote" lives here.
EXPECTED_PAUSABLES = [
    (WITHDRAWAL_QUEUE, GATE_SEAL_COMMITTEE),
    (VALIDATORS_EXIT_BUS_ORACLE, GATE_SEAL_COMMITTEE),
    (TRIGGERABLE_WITHDRAWALS_GATEWAY, GATE_SEAL_COMMITTEE),
    (VAULT_HUB, GATE_SEAL_COMMITTEE),
    (PREDEPOSIT_GUARANTEE, GATE_SEAL_COMMITTEE),
    (CSM_ADDRESS, CSM_COMMITTEE_MS),
    (CS_ACCOUNTING_ADDRESS, CSM_COMMITTEE_MS),
    (CS_FEE_ORACLE_ADDRESS, CSM_COMMITTEE_MS),
    (CS_VERIFIER_V2_ADDRESS, CSM_COMMITTEE_MS),
    (CS_VETTED_GATE_ADDRESS, CSM_COMMITTEE_MS),
    (CS_EJECTOR_ADDRESS, CSM_COMMITTEE_MS),
]


@pytest.fixture(scope="module")
def circuit_breaker():
    return interface.CircuitBreaker(CIRCUIT_BREAKER)


def test_admin(circuit_breaker):
    assert circuit_breaker.ADMIN() == AGENT


def test_bounds_and_initial_values(circuit_breaker):
    min_pause = circuit_breaker.MIN_PAUSE_DURATION()
    max_pause = circuit_breaker.MAX_PAUSE_DURATION()
    min_heartbeat = circuit_breaker.MIN_HEARTBEAT_INTERVAL()
    max_heartbeat = circuit_breaker.MAX_HEARTBEAT_INTERVAL()
    pause_duration = circuit_breaker.pauseDuration()
    heartbeat_interval = circuit_breaker.heartbeatInterval()

    assert min_pause == CIRCUIT_BREAKER_MIN_PAUSE_DURATION
    assert max_pause == CIRCUIT_BREAKER_MAX_PAUSE_DURATION
    assert min_heartbeat == CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL
    assert max_heartbeat == CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL
    assert pause_duration == CIRCUIT_BREAKER_PAUSE_DURATION
    assert heartbeat_interval == CIRCUIT_BREAKER_HEARTBEAT_INTERVAL

    assert 0 < min_pause <= pause_duration <= max_pause
    assert 0 < min_heartbeat <= heartbeat_interval <= max_heartbeat


def test_pausables_set(circuit_breaker):
    on_chain = circuit_breaker.getPausables()
    assert len(on_chain) == len(set(on_chain)), f"getPausables() has duplicates: {on_chain}"
    assert {addr.lower() for addr in on_chain} == {p.lower() for p, _ in EXPECTED_PAUSABLES}


@pytest.mark.parametrize("pausable, expected_pauser", EXPECTED_PAUSABLES)
def test_pauser_assignment(circuit_breaker, pausable, expected_pauser):
    assert circuit_breaker.getPauser(pausable).lower() == expected_pauser.lower()


def test_pausable_counts_per_pauser(circuit_breaker):
    expected_counts = {}
    for _, pauser in EXPECTED_PAUSABLES:
        expected_counts[pauser.lower()] = expected_counts.get(pauser.lower(), 0) + 1

    for pauser, expected in expected_counts.items():
        assert circuit_breaker.getPausableCount(pauser) == expected, (
            f"getPausableCount({pauser}) expected {expected}"
        )

    total = sum(expected_counts.values())
    assert total == len(EXPECTED_PAUSABLES)


@pytest.mark.parametrize("pausable, _pauser", EXPECTED_PAUSABLES)
def test_pause_role_holders(_pauser, pausable):
    pausable_contract = interface.IPausableUntilWithRoles(pausable)
    pause_role = str(pausable_contract.PAUSE_ROLE())
    assert pausable_contract.getRoleMemberCount(pause_role) == 2
    holders = {
        pausable_contract.getRoleMember(pause_role, 0).lower(),
        pausable_contract.getRoleMember(pause_role, 1).lower(),
    }
    assert holders == {CIRCUIT_BREAKER.lower(), RESEAL_MANAGER.lower()}


@pytest.mark.parametrize("pausable, _pauser", EXPECTED_PAUSABLES)
def test_resume_role_holder(_pauser, pausable):
    pausable_contract = interface.IPausableUntilWithRoles(pausable)
    resume_role = str(pausable_contract.RESUME_ROLE())
    assert pausable_contract.getRoleMemberCount(resume_role) == 1
    assert pausable_contract.getRoleMember(resume_role, 0).lower() == RESEAL_MANAGER.lower()


@pytest.mark.parametrize("pauser", sorted({p for _, p in EXPECTED_PAUSABLES}))
def test_pauser_is_live(circuit_breaker, pauser):
    assert circuit_breaker.isPauserLive(pauser), f"{pauser} not live"
    expiry = circuit_breaker.heartbeatExpiry(pauser)
    block_timestamp = web3.eth.get_block("latest")["timestamp"]
    assert expiry > block_timestamp, (
        f"heartbeatExpiry({pauser}) = {expiry} <= block.timestamp = {block_timestamp}"
    )
