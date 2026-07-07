"""
Acceptance tests for the consolidation pipeline added by the SRv3 upgrade:

- ConsolidationGateway — entry point for consolidation requests; deployed directly
  (no proxy), admin and limits are set in the constructor; wired into the upgraded
  LidoLocator; the vote registers a CircuitBreaker pauser for it (item 1.18).
- ConsolidationBus (OssifiableProxy) — queue/batch layer between the migrator and
  the gateway.
- ConsolidationMigrator (OssifiableProxy) — migrates Curated (module id 1)
  validators into Curated Module v2 (id 4); pairs are allowed via the EasyTrack
  AllowConsolidationPair factory and disallowed by the CMC committee.
"""

import pytest
from brownie import interface, reverts, web3  # type: ignore
from brownie.convert.datatypes import HexString

from utils.config import (
    contracts,
    AGENT,
    CIRCUIT_BREAKER,
    RESEAL_MANAGER,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    STAKING_ROUTER,
    CURATED_V2_STAKING_MODULE_ID,
    CONSOLIDATION_GATEWAY,
    CONSOLIDATION_GATEWAY_MAX_REQUESTS_LIMIT,
    CONSOLIDATION_GATEWAY_CONSOLIDATIONS_PER_FRAME,
    CONSOLIDATION_GATEWAY_FRAME_DURATION_IN_SEC,
    CONSOLIDATION_BUS,
    CONSOLIDATION_BUS_IMPL,
    CONSOLIDATION_BUS_BATCH_SIZE,
    CONSOLIDATION_BUS_MAX_GROUPS_IN_BATCH,
    CONSOLIDATION_BUS_EXECUTION_DELAY,
    CONSOLIDATION_MIGRATOR,
    CONSOLIDATION_MIGRATOR_IMPL,
    CONSOLIDATION_SOURCE_MODULE_ID,
    CONSOLIDATION_TARGET_MODULE_ID,
    CONSOLIDATION_COMMITTEE,
)
from utils.evm_script import encode_error
from utils.test.helpers import access_control_unauthorized as unauthorized

DEFAULT_ADMIN_ROLE = "0x" + "00" * 32
GI_FIRST_VALIDATOR = HexString("0x0000000000000000000000000000000000000000000000000096000000000028", "bytes")


@pytest.fixture(scope="module")
def gateway() -> interface.ConsolidationGateway:
    return interface.ConsolidationGateway(CONSOLIDATION_GATEWAY)


@pytest.fixture(scope="module")
def bus() -> interface.ConsolidationBus:
    return interface.ConsolidationBus(CONSOLIDATION_BUS)


@pytest.fixture(scope="module")
def migrator() -> interface.ConsolidationMigrator:
    return interface.ConsolidationMigrator(CONSOLIDATION_MIGRATOR)


class TestConsolidationGateway:
    def test_locator_wiring(self, gateway):
        assert contracts.lido_locator.consolidationGateway() == gateway.address

    def test_immutables(self, gateway):
        # constructor args (upgrade-params-mainnet.toml [consolidationGateway])
        assert gateway.GI_FIRST_VALIDATOR_PREV() == GI_FIRST_VALIDATOR
        assert gateway.GI_FIRST_VALIDATOR_CURR() == GI_FIRST_VALIDATOR
        assert gateway.PIVOT_SLOT() == 0

    def test_limits(self, gateway):
        (
            max_requests_limit,
            consolidations_per_frame,
            frame_duration_in_sec,
            _prev_limit,
            current_limit,
        ) = gateway.getConsolidationRequestLimitFullInfo()
        assert max_requests_limit == CONSOLIDATION_GATEWAY_MAX_REQUESTS_LIMIT
        assert consolidations_per_frame == CONSOLIDATION_GATEWAY_CONSOLIDATIONS_PER_FRAME
        assert frame_duration_in_sec == CONSOLIDATION_GATEWAY_FRAME_DURATION_IN_SEC
        assert current_limit <= max_requests_limit

    def test_initial_state(self, gateway):
        assert not gateway.isPaused()

    def test_roles(self, gateway):
        """Mirrors UpgradeTemplate checks + item 1.18 (CircuitBreaker pauser)."""
        pause_role = web3.keccak(text="PAUSE_ROLE")
        resume_role = web3.keccak(text="RESUME_ROLE")
        add_request_role = web3.keccak(text="ADD_CONSOLIDATION_REQUEST_ROLE")
        exit_limit_manager_role = web3.keccak(text="EXIT_LIMIT_MANAGER_ROLE")

        # DEFAULT_ADMIN_ROLE: only the Agent (temporary admin renounced)
        assert gateway.getRoleMemberCount(DEFAULT_ADMIN_ROLE) == 1
        assert gateway.getRoleMember(DEFAULT_ADMIN_ROLE, 0) == AGENT

        # PAUSE_ROLE: CircuitBreaker + ResealManager
        assert gateway.getRoleMemberCount(pause_role) == 2
        assert {
            gateway.getRoleMember(pause_role, 0),
            gateway.getRoleMember(pause_role, 1),
        } == {CIRCUIT_BREAKER, RESEAL_MANAGER}

        # RESUME_ROLE: only the ResealManager
        assert gateway.getRoleMemberCount(resume_role) == 1
        assert gateway.getRoleMember(resume_role, 0) == RESEAL_MANAGER

        # ADD_CONSOLIDATION_REQUEST_ROLE: only the ConsolidationBus
        assert gateway.getRoleMemberCount(add_request_role) == 1
        assert gateway.getRoleMember(add_request_role, 0) == CONSOLIDATION_BUS

        # EXIT_LIMIT_MANAGER_ROLE: not granted to anyone by the upgrade
        assert gateway.getRoleMemberCount(exit_limit_manager_role) == 0

    def test_acl(self, gateway, stranger):
        # .call() — anvil does not surface custom-error data for reverted txs
        # the main gated entry point (bus-only)
        with reverts(unauthorized(stranger, "ADD_CONSOLIDATION_REQUEST_ROLE")):
            gateway.addConsolidationRequests.call([], stranger, {"from": stranger})

        # 1 sec: a zero duration would revert with ZeroPauseDuration before the ACL check
        with reverts(unauthorized(stranger, "PAUSE_ROLE")):
            gateway.pauseFor.call(1, {"from": stranger})

        with reverts(unauthorized(stranger, "RESUME_ROLE")):
            gateway.resume.call({"from": stranger})

        # NB: EXIT_LIMIT_MANAGER_ROLE has no holders, so this reverts for anyone;
        # kept as a smoke check that the method is not open
        with reverts(unauthorized(stranger, "EXIT_LIMIT_MANAGER_ROLE")):
            gateway.setConsolidationRequestLimit.call(1, 1, 1, {"from": stranger})


class TestConsolidationBus:
    def test_proxy(self, bus):
        proxy = interface.OssifiableProxy(bus)
        assert proxy.proxy__getImplementation() == CONSOLIDATION_BUS_IMPL
        assert proxy.proxy__getAdmin() == AGENT

    def test_state(self, bus):
        # immutable, points back to the gateway (checked by the template too)
        assert bus.getConsolidationGateway() == CONSOLIDATION_GATEWAY
        # initialize() params — upgrade-params-mainnet.toml [consolidationBus]
        assert bus.batchSize() == CONSOLIDATION_BUS_BATCH_SIZE
        assert bus.maxGroupsInBatch() == CONSOLIDATION_BUS_MAX_GROUPS_IN_BATCH
        assert bus.executionDelay() == CONSOLIDATION_BUS_EXECUTION_DELAY

    def test_initialize(self, bus):
        with reverts(encode_error("InvalidInitialization()")):
            bus.initialize.call(
                AGENT,
                CONSOLIDATION_BUS_BATCH_SIZE,
                CONSOLIDATION_BUS_MAX_GROUPS_IN_BATCH,
                CONSOLIDATION_BUS_EXECUTION_DELAY,
                {"from": contracts.voting},
            )

    def test_petrified(self):
        # the implementation calls _disableInitializers() in the constructor
        impl = interface.ConsolidationBus(CONSOLIDATION_BUS_IMPL)
        with reverts(encode_error("InvalidInitialization()")):
            impl.initialize.call(
                AGENT,
                CONSOLIDATION_BUS_BATCH_SIZE,
                CONSOLIDATION_BUS_MAX_GROUPS_IN_BATCH,
                CONSOLIDATION_BUS_EXECUTION_DELAY,
                {"from": contracts.voting},
            )

    def test_roles(self, bus):
        publish_role = web3.keccak(text="PUBLISH_ROLE")
        remove_role = web3.keccak(text="REMOVE_ROLE")
        manage_role = web3.keccak(text="MANAGE_ROLE")

        assert bus.getRoleMemberCount(DEFAULT_ADMIN_ROLE) == 1
        assert bus.getRoleMember(DEFAULT_ADMIN_ROLE, 0) == AGENT

        # PUBLISH_ROLE: only the ConsolidationMigrator
        assert bus.getRoleMemberCount(publish_role) == 1
        assert bus.getRoleMember(publish_role, 0) == CONSOLIDATION_MIGRATOR

        # REMOVE_ROLE: only the CMC committee
        assert bus.getRoleMemberCount(remove_role) == 1
        assert bus.getRoleMember(remove_role, 0) == CONSOLIDATION_COMMITTEE

        # MANAGE_ROLE: not granted to anyone by the upgrade
        assert bus.getRoleMemberCount(manage_role) == 0

    def test_acl(self, bus, stranger):
        # the main gated entry point (PUBLISH_ROLE, migrator-only)
        with reverts(unauthorized(stranger, "PUBLISH_ROLE")):
            bus.addConsolidationRequests.call([], {"from": stranger})

        with reverts(unauthorized(stranger, "REMOVE_ROLE")):
            bus.removeBatches.call([], {"from": stranger})

        # NB: MANAGE_ROLE has no holders, so these revert for anyone;
        # kept as a smoke check that the setters are not open
        with reverts(unauthorized(stranger, "MANAGE_ROLE")):
            bus.setBatchSize.call(1, {"from": stranger})
        with reverts(unauthorized(stranger, "MANAGE_ROLE")):
            bus.setMaxGroupsInBatch.call(1, {"from": stranger})
        with reverts(unauthorized(stranger, "MANAGE_ROLE")):
            bus.setExecutionDelay.call(1, {"from": stranger})


class TestConsolidationMigrator:
    def test_proxy(self, migrator):
        proxy = interface.OssifiableProxy(migrator)
        assert proxy.proxy__getImplementation() == CONSOLIDATION_MIGRATOR_IMPL
        assert proxy.proxy__getAdmin() == AGENT

    def test_state(self, migrator):
        # immutables (constructor args)
        assert migrator.getStakingRouter() == STAKING_ROUTER
        assert migrator.getConsolidationBus() == CONSOLIDATION_BUS
        assert migrator.sourceModuleId() == CONSOLIDATION_SOURCE_MODULE_ID
        # the template checks targetModuleId == the freshly added CMv2 module id
        assert migrator.targetModuleId() == CONSOLIDATION_TARGET_MODULE_ID
        assert migrator.targetModuleId() == CURATED_V2_STAKING_MODULE_ID

    def test_initialize(self, migrator):
        with reverts(encode_error("InvalidInitialization()")):
            migrator.initialize.call(AGENT, {"from": contracts.voting})

    def test_petrified(self):
        impl = interface.ConsolidationMigrator(CONSOLIDATION_MIGRATOR_IMPL)
        with reverts(encode_error("InvalidInitialization()")):
            impl.initialize.call(AGENT, {"from": contracts.voting})

    def test_roles(self, migrator):
        allow_pair_role = web3.keccak(text="ALLOW_PAIR_ROLE")
        disallow_pair_role = web3.keccak(text="DISALLOW_PAIR_ROLE")

        assert migrator.getRoleMemberCount(DEFAULT_ADMIN_ROLE) == 1
        assert migrator.getRoleMember(DEFAULT_ADMIN_ROLE, 0) == AGENT

        # ALLOW_PAIR_ROLE: only the EasyTrack EVMScript executor
        # (pairs are allowed via the AllowConsolidationPair ET factory, vote item 5)
        assert migrator.getRoleMemberCount(allow_pair_role) == 1
        assert migrator.getRoleMember(allow_pair_role, 0) == EASYTRACK_EVMSCRIPT_EXECUTOR

        # DISALLOW_PAIR_ROLE: only the CMC committee
        assert migrator.getRoleMemberCount(disallow_pair_role) == 1
        assert migrator.getRoleMember(disallow_pair_role, 0) == CONSOLIDATION_COMMITTEE

    def test_acl(self, migrator, stranger):
        # granted to the EasyTrack EVMScript executor only
        with reverts(unauthorized(stranger, "ALLOW_PAIR_ROLE")):
            migrator.allowPair.call(1, 1, stranger, {"from": stranger})

        # granted to the CMC committee only
        with reverts(unauthorized(stranger, "DISALLOW_PAIR_ROLE")):
            migrator.disallowPair.call(1, 1, {"from": stranger})
