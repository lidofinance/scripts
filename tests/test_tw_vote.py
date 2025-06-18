"""
Tests for triggerable withdrawals voting.
"""

from typing import Dict, Tuple, List, NamedTuple
from scripts.tw_vote import create_tw_vote
from brownie import interface, convert, web3, ZERO_ADDRESS
from utils.test.tx_tracing_helpers import *
# from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS
from utils.config import (
    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    WITHDRAWAL_VAULT_IMPL,
    LIDO_LOCATOR_IMPL,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    contracts,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str

def test_tw_vote(helpers, accounts, vote_ids_from_env, stranger):
    # Define constants and initial states
    app_manager_role = web3.keccak(text="APP_MANAGER_ROLE")
    vebo_consensus_version = 4
    ao_consensus_version = 4
    exit_events_lookback_window_in_slots = 7200
    nor_exit_deadline_in_sec = 30 * 60

    # --- Initial state checks ---

    # Assert VEBO implementation and configuration
    initial_vebo_consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    assert initial_vebo_consensus_version < vebo_consensus_version

    # Assert Accounting Oracle implementation and configuration
    initial_ao_consensus_version = contracts.accounting_oracle.getConsensusVersion()
    assert initial_ao_consensus_version < ao_consensus_version


    # Assert TWG role assignments initial state
    add_full_withdrawal_request_role = contracts.triggerable_withdrawals_gateway.ADD_FULL_WITHDRAWAL_REQUEST_ROLE()
    assert not contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.cs_ejector)
    assert not contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle)

    # Assert Staking Router permissions
    try:
        report_validator_exiting_status_role = contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE()
        report_validator_exit_triggered_role = contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE()
    except Exception as e:
        assert "Unknown typed error: 0x" in str(e), f"Unexpected error: {e}"
        report_validator_exiting_status_role = ZERO_ADDRESS
        report_validator_exit_triggered_role = ZERO_ADDRESS

    assert report_validator_exiting_status_role == ZERO_ADDRESS
    assert report_validator_exit_triggered_role == ZERO_ADDRESS

    # Assert APP_MANAGER_ROLE setting
    assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel, app_manager_role)

    # Assert Node Operator Registry and sDVT configuration

    assert contracts.node_operators_registry.getContractVersion() == 3
    assert contracts.simple_dvt.getContractVersion() == 3


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id = create_tw_vote(tx_params, silent=True)

    print(f"voteId = {vote_id}")

    # --- VALIDATE EXECUTION RESULTS ---

    # 1. Validate Lido Locator implementation was updated
    assert interface.OssifiableProxy(contracts.lido_locator).proxy__getImplementation() == LIDO_LOCATOR_IMPL

    # 2-3. Validate VEBO implementation was updated and configured
    assert interface.OssifiableProxy(contracts.validators_exit_bus_oracle).proxy__getImplementation() == VALIDATORS_EXIT_BUS_ORACLE_IMPL
    assert contracts.validators_exit_bus_oracle.getMaxValidatorsPerReport() == 600

    # # 4-5. Validate VEBO consensus version management
    assert contracts.validators_exit_bus_oracle.getConsensusVersion() == vebo_consensus_version

    # # 7-8. Validate TWG roles
    assert contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.cs_ejector)
    assert contracts.triggerable_withdrawals_gateway.hasRole(add_full_withdrawal_request_role, contracts.validators_exit_bus_oracle)

    # # 9-10. Validate Withdrawal Vault upgrade
    assert interface.WithdrawalContractProxy(contracts.withdrawal_vault).implementation() == WITHDRAWAL_VAULT_IMPL

    # # 11-13. Validate Accounting Oracle upgrade
    assert contracts.accounting_oracle.getConsensusVersion() == ao_consensus_version

    # # 14-16. Validate Staking Router upgrade
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXITING_STATUS_ROLE(), contracts.validator_exit_verifier)
    assert contracts.staking_router.hasRole(contracts.staking_router.REPORT_VALIDATOR_EXIT_TRIGGERED_ROLE(), contracts.triggerable_withdrawals_gateway)

    # # Check NOR and sDVT updates

    assert not contracts.acl.hasPermission(contracts.agent, contracts.kernel, app_manager_role)

    assert contracts.node_operators_registry.getContractVersion() == 4
    assert contracts.simple_dvt.getContractVersion() == 4

    assert contracts.node_operators_registry.exitDeadlineThreshold(0) == nor_exit_deadline_in_sec
    assert contracts.simple_dvt.exitDeadlineThreshold(0) == nor_exit_deadline_in_sec

    # 23-27. Validate Oracle Daemon Config changes
    assert convert.to_uint(contracts.oracle_daemon_config.get('EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS')) == exit_events_lookback_window_in_slots



