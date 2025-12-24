import pytest

from brownie import reverts, accounts, chain, web3, Wei, interface  # type: ignore
from eth_hash.auto import keccak

from utils.test.exit_bus_data import LidoValidator
from utils.test.oracle_report_helpers import oracle_report, ZERO_BYTES32, wait_to_next_available_report_time, \
    prepare_exit_bus_report, reach_consensus
from brownie.network.account import Account

from eth_abi.abi import encode
from utils.evm_script import encode_error
from utils.test.helpers import almostEqEth, ETH
from utils.test.deposits_helpers import fill_deposit_buffer
from utils.config import (
    TRIGGERABLE_WITHDRAWALS_GATEWAY,
    GATE_SEAL_COMMITTEE,
    contracts,
    WITHDRAWAL_QUEUE,
    VALIDATORS_EXIT_BUS_ORACLE,
    GATE_SEAL,
    GATE_SEAL_PAUSE_DURATION,
    GATE_SEAL_EXPIRY_TIMESTAMP,
    CHAIN_SLOTS_PER_EPOCH,
    CHAIN_SECONDS_PER_SLOT,
    AO_EPOCHS_PER_FRAME,
    VAULT_HUB,
    PREDEPOSIT_GUARANTEE,
    GATE_SEAL_V3,
    RESEAL_MANAGER,
)


@pytest.fixture(scope="module")
def gate_seal_committee(accounts) -> Account:
    return accounts.at(GATE_SEAL_COMMITTEE, force=True)


def test_gate_seal_expiration(gate_seal_committee):
    assert not contracts.gate_seal.is_expired()
    time = chain.time()
    chain.sleep(GATE_SEAL_EXPIRY_TIMESTAMP - time + 1)
    chain.mine(1)
    assert contracts.gate_seal.is_expired()
    with reverts("gate seal: expired"):
        contracts.gate_seal.seal([WITHDRAWAL_QUEUE], {"from": gate_seal_committee})


def test_gate_seal_v3_expiration(gate_seal_committee):
    gate_seal_v3 = interface.GateSeal(GATE_SEAL_V3)

    assert not gate_seal_v3.is_expired()
    time = chain.time()
    expiry = gate_seal_v3.get_expiry_timestamp()
    chain.sleep(expiry - time + 1)
    chain.mine(1)

    assert gate_seal_v3.is_expired()
    with reverts("gate seal: expired"):
        gate_seal_v3.seal(gate_seal_v3.get_sealables(), {"from": gate_seal_committee})


def test_gate_seal_twg_veb_expiration(gate_seal_committee):
    assert not contracts.veb_twg_gate_seal.is_expired()
    time = chain.time()
    chain.sleep(GATE_SEAL_EXPIRY_TIMESTAMP - time + 1)
    chain.mine(1)
    assert contracts.veb_twg_gate_seal.is_expired()
    with reverts("gate seal: expired"):
        contracts.gate_seal.seal([TRIGGERABLE_WITHDRAWALS_GATEWAY, VALIDATORS_EXIT_BUS_ORACLE], {"from": gate_seal_committee})


def test_gate_seal_wq_scenario(steth_holder, gate_seal_committee, eth_whale):
    account = accounts.at(steth_holder, force=True)
    REQUESTS_COUNT = 2
    REQUEST_AMOUNT = ETH(1)
    REQUESTS_SUM = REQUESTS_COUNT * REQUEST_AMOUNT

    """ finalize all requests """
    unfinalized_steth = contracts.withdrawal_queue.unfinalizedStETH()

    while unfinalized_steth > 0:
        fill_deposit_buffer(unfinalized_steth // ETH(32) + 1)

        oracle_report(silent=True)
        unfinalized_steth = contracts.withdrawal_queue.unfinalizedStETH()

    """ requests to be finalized """
    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": steth_holder})
    request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], steth_holder, {"from": steth_holder}
    )
    claimable_request_ids = [event["requestId"] for event in request_tx.events["WithdrawalRequested"]]

    """ finalization """
    report_tx = oracle_report(silent=True)[0]

    # on second report requests will get finalized for sure
    if not report_tx.events.count("WithdrawalsFinalized") == 1:
        report_tx = oracle_report(silent=True)[0]

    while report_tx.events["WithdrawalsFinalized"][0]["to"] != claimable_request_ids[-1]:
        report_tx = oracle_report(silent=True)[0]
        assert report_tx.events.count("WithdrawalsFinalized") == 1

    post_report_statuses = contracts.withdrawal_queue.getWithdrawalStatus(claimable_request_ids, {"from": steth_holder})
    for i, _ in enumerate(claimable_request_ids):
        (_, _, _, _, isFinalized, isClaimed) = post_report_statuses[i]
        assert isFinalized
        assert not isClaimed

    """ requests to be left pending """
    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": steth_holder})
    request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], steth_holder, {"from": steth_holder}
    )
    pending_request_ids = [event["requestId"] for event in request_tx.events["WithdrawalRequested"]]

    """ sealing """
    sealables = [WITHDRAWAL_QUEUE]
    seal_tx = contracts.gate_seal.seal(sealables, {"from": gate_seal_committee})

    assert seal_tx.events.count("Sealed") == 1
    for i, seal_event in enumerate(seal_tx.events["Sealed"]):
        assert seal_event["gate_seal"] == GATE_SEAL
        assert seal_event["sealed_for"] == GATE_SEAL_PAUSE_DURATION
        assert seal_event["sealed_by"] == gate_seal_committee
        assert seal_event["sealable"] == sealables[i]
        assert seal_event["sealed_at"] == seal_tx.timestamp

    # brownie for some reason fails to decode second event
    # assert seal_tx.events.count("Paused") == 2
    for pause_event in seal_tx.events["Paused"]:
        assert pause_event["duration"] == GATE_SEAL_PAUSE_DURATION

    assert contracts.gate_seal.is_expired()
    with reverts("gate seal: expired"):
        seal_tx = contracts.gate_seal.seal(sealables, {"from": gate_seal_committee})

    assert contracts.withdrawal_queue.isPaused()
    assert contracts.withdrawal_queue.getResumeSinceTimestamp() == seal_tx.timestamp + GATE_SEAL_PAUSE_DURATION

    # reverts on requestWithdrawals
    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": steth_holder})
    with reverts(encode_error("ResumedExpected()")):
        contracts.withdrawal_queue.requestWithdrawals(
            [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], steth_holder, {"from": steth_holder}
        )

    # reverts on finalization attempt
    with reverts(encode_error("ResumedExpected()")):
        contracts.withdrawal_queue.finalize(1, 1, {"from": steth_holder})

    """ claim """
    assert contracts.withdrawal_queue.isPaused()
    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    hints = contracts.withdrawal_queue.findCheckpointHints(claimable_request_ids, 1, lastCheckpointIndex)
    claim_balance_before = account.balance()
    claim_tx = contracts.withdrawal_queue.claimWithdrawals(claimable_request_ids, hints, {"from": steth_holder})
    claim_balance_after = account.balance()

    assert contracts.withdrawal_queue.isPaused()

    assert almostEqEth(
        claim_balance_after - claim_balance_before + claim_tx.gas_used * claim_tx.gas_price, REQUESTS_SUM
    )
    assert claim_tx.events.count("WithdrawalClaimed") == REQUESTS_COUNT

    """ accounting oracle reports until we pass pause and claim"""
    MAX_REPORTS_UNTIL_RESUME = (
        GATE_SEAL_PAUSE_DURATION // (CHAIN_SECONDS_PER_SLOT * CHAIN_SLOTS_PER_EPOCH * AO_EPOCHS_PER_FRAME) + 2
    )
    reports_passed = 0
    while True:
        (report_tx, _) = oracle_report(silent=True)
        reports_passed += 1
        print(
            f"Oracle report {reports_passed} at {report_tx.timestamp}/{seal_tx.timestamp + GATE_SEAL_PAUSE_DURATION} seconds to resume"
        )
        if report_tx.events.count("WithdrawalsFinalized") == 1:
            break
        assert reports_passed <= MAX_REPORTS_UNTIL_RESUME

    assert not contracts.withdrawal_queue.isPaused()

    """ post seal claim """
    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    hints = contracts.withdrawal_queue.findCheckpointHints(pending_request_ids, 1, lastCheckpointIndex)
    claim_balance_before = account.balance()
    claim_tx = contracts.withdrawal_queue.claimWithdrawals(pending_request_ids, hints, {"from": steth_holder})
    claim_balance_after = account.balance()

    assert almostEqEth(
        claim_balance_after - claim_balance_before + claim_tx.gas_used * claim_tx.gas_price, REQUESTS_SUM
    )
    assert claim_tx.events.count("WithdrawalClaimed") == REQUESTS_COUNT


def test_gate_seal_twg_veb_scenario(steth_holder, gate_seal_committee, eth_whale):
    account = accounts.at(steth_holder, force=True)
    REQUESTS_COUNT = 2
    REQUEST_AMOUNT = ETH(1)
    REQUESTS_SUM = REQUESTS_COUNT * REQUEST_AMOUNT

    """ finalize all requests """
    unfinalized_steth = contracts.withdrawal_queue.unfinalizedStETH()

    while unfinalized_steth > 0:
        fill_deposit_buffer(unfinalized_steth // ETH(32) + 1)

        oracle_report(silent=True)
        unfinalized_steth = contracts.withdrawal_queue.unfinalizedStETH()

    """ requests to be finalized """
    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": steth_holder})
    request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], steth_holder, {"from": steth_holder}
    )
    claimable_request_ids = [event["requestId"] for event in request_tx.events["WithdrawalRequested"]]

    """ finalization """
    report_tx = oracle_report(silent=True)[0]

    # on second report requests will get finalized for sure
    if not report_tx.events.count("WithdrawalsFinalized") == 1:
        report_tx = oracle_report(silent=True)[0]

    while report_tx.events["WithdrawalsFinalized"][0]["to"] != claimable_request_ids[-1]:
        report_tx = oracle_report(silent=True)[0]
        assert report_tx.events.count("WithdrawalsFinalized") == 1

    post_report_statuses = contracts.withdrawal_queue.getWithdrawalStatus(claimable_request_ids, {"from": steth_holder})
    for i, _ in enumerate(claimable_request_ids):
        (_, _, _, _, isFinalized, isClaimed) = post_report_statuses[i]
        assert isFinalized
        assert not isClaimed

    """ requests to be left pending """
    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": steth_holder})
    request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], steth_holder, {"from": steth_holder}
    )
    pending_request_ids = [event["requestId"] for event in request_tx.events["WithdrawalRequested"]]

    """ sealing """
    sealables = [TRIGGERABLE_WITHDRAWALS_GATEWAY, VALIDATORS_EXIT_BUS_ORACLE]
    seal_tx = contracts.veb_twg_gate_seal.seal(sealables, {"from": gate_seal_committee})

    assert seal_tx.events.count("Sealed") == 2
    for i, seal_event in enumerate(seal_tx.events["Sealed"]):
        assert seal_event["gate_seal"] == contracts.veb_twg_gate_seal.address
        assert seal_event["sealed_for"] == GATE_SEAL_PAUSE_DURATION
        assert seal_event["sealed_by"] == gate_seal_committee
        assert seal_event["sealable"] == sealables[i]
        assert seal_event["sealed_at"] == seal_tx.timestamp

    # brownie for some reason fails to decode second event
    # assert seal_tx.events.count("Paused") == 2
    for pause_event in seal_tx.events["Paused"]:
        assert pause_event["duration"] == GATE_SEAL_PAUSE_DURATION

    assert contracts.veb_twg_gate_seal.is_expired()
    with reverts("gate seal: expired"):
        seal_tx = contracts.veb_twg_gate_seal.seal(sealables, {"from": gate_seal_committee})

    assert contracts.triggerable_withdrawals_gateway.isPaused()
    assert contracts.triggerable_withdrawals_gateway.getResumeSinceTimestamp() == seal_tx.timestamp + GATE_SEAL_PAUSE_DURATION

    assert contracts.validators_exit_bus_oracle.isPaused()
    assert (
        contracts.validators_exit_bus_oracle.getResumeSinceTimestamp() == seal_tx.timestamp + GATE_SEAL_PAUSE_DURATION
    )

    value = Wei('1 ether')
    # reverts on VEBO report
    with reverts(encode_error("ResumedExpected()")):
        contracts.validators_exit_bus_oracle.submitReportData((1, 1, 1, 1, ZERO_BYTES32), 1, {"from": steth_holder})

    # reverts on VEBO triggerExits
    with reverts(encode_error("ResumedExpected()")):
        contracts.validators_exit_bus_oracle.triggerExits(("0x0000000000000000000000000000000000000000000", 1), [1, 2, 3], steth_holder, {"from": steth_holder, 'value': value})

    """ claim """
    assert contracts.triggerable_withdrawals_gateway.isPaused()
    assert contracts.validators_exit_bus_oracle.isPaused()

    """ accounting oracle reports until we pass pause and claim"""
    MAX_REPORTS_UNTIL_RESUME = (
        GATE_SEAL_PAUSE_DURATION // (CHAIN_SECONDS_PER_SLOT * CHAIN_SLOTS_PER_EPOCH * AO_EPOCHS_PER_FRAME) + 2
    )
    reports_passed = 0
    for i in range(MAX_REPORTS_UNTIL_RESUME):
        (report_tx, _) = oracle_report(silent=False)
        print(
            f"Oracle report {reports_passed} at {report_tx.timestamp}/{seal_tx.timestamp + GATE_SEAL_PAUSE_DURATION} seconds to resume"
        )

    assert not contracts.triggerable_withdrawals_gateway.isPaused()
    assert not contracts.validators_exit_bus_oracle.isPaused()

    """ post seal """
    unreachable_cl_validator_index = 100_000_000
    no_global_index = (module_id, no_id) = (1, 33)
    validator_key = contracts.node_operators_registry.getSigningKey(no_id, 1)[0]

    validator = LidoValidator(index=unreachable_cl_validator_index, pubkey=validator_key)

    ref_slot = _wait_for_next_ref_slot()
    report, report_hash = prepare_exit_bus_report([(no_global_index, validator)], ref_slot)
    consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()

    submitter = reach_consensus(
        ref_slot, report_hash, consensus_version, contracts.hash_consensus_for_validators_exit_bus_oracle
    )
    hash = web3.keccak(encode(['bytes', 'uint256'], [report[4], 1]))
    (_,_,_, vebInitLimit1, vebInitLimit2) = contracts.validators_exit_bus_oracle.getExitRequestLimitFullInfo()
    contracts.validators_exit_bus_oracle.submitExitRequestsHash(hash, {"from": "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"})
    contracts.validators_exit_bus_oracle.submitExitRequestsData((report[4], 1), {"from": submitter})
    (
        twgInitMaxExitRequestLimit1,
        twgInitExitsPerFrameLimit1,
        twgInitFrameDurationInSeconds1,
        twgInitPrevExitRequestsLimit1,
        twgInitCurrentRequestLimit2
    ) = contracts.triggerable_withdrawals_gateway.getExitRequestLimitFullInfo()
    tx = contracts.validators_exit_bus_oracle.triggerExits((report[4], 1), [0], steth_holder, {"from": steth_holder, 'value': value})

    (
        twgMaxExitRequestLimit1,
        twgExitsPerFrameLimit1,
        twgFrameDurationInSeconds1,
        twgPrevExitRequestsLimit1,
        twgCurrentRequestLimit2
    ) = contracts.triggerable_withdrawals_gateway.getExitRequestLimitFullInfo()
    (_,_,_, vebLimit1, vebLimit2) = contracts.validators_exit_bus_oracle.getExitRequestLimitFullInfo()
    assert vebLimit1 < vebInitLimit1
    assert vebLimit2 < vebInitLimit2
    assert twgPrevExitRequestsLimit1 == twgCurrentRequestLimit2
    assert twgCurrentRequestLimit2 < twgInitCurrentRequestLimit2
    assert len(tx.events["WithdrawalRequestAdded"]['request']) == 56  # 48 + 8
    pubkey_bytes = tx.events["WithdrawalRequestAdded"]['request'][:48]
    _ = int.from_bytes(tx.events["WithdrawalRequestAdded"]['request'][48:], byteorder="big", signed=False)

    pubkey_hex = "0x" + pubkey_bytes.hex()
    assert validator_key == pubkey_hex


def test_gate_seal_v3_vaults_scenario(gate_seal_committee):
    gate_seal_v3 = interface.GateSeal(GATE_SEAL_V3)

    assert not gate_seal_v3.is_expired()

    sealables = gate_seal_v3.get_sealables()
    assert len(sealables) == 2
    assert contracts.vault_hub.address in sealables
    assert contracts.predeposit_guarantee.address in sealables

    pause_duration = gate_seal_v3.get_seal_duration_seconds()

    # TODO remove this after PDG unpause
    reseal_manager_account = accounts.at(RESEAL_MANAGER, force=True)
    contracts.predeposit_guarantee.resume({"from": reseal_manager_account})

    assert not contracts.vault_hub.isPaused()
    assert not contracts.predeposit_guarantee.isPaused()

    seal_tx = gate_seal_v3.seal(sealables, {"from": gate_seal_committee})

    assert seal_tx.events.count("Sealed") == len(sealables)
    for i, seal_event in enumerate(seal_tx.events["Sealed"]):
        assert seal_event["gate_seal"] == gate_seal_v3.address
        assert seal_event["sealed_for"] == pause_duration
        assert seal_event["sealed_by"] == gate_seal_committee
        assert seal_event["sealable"] == sealables[i]
        assert seal_event["sealed_at"] == seal_tx.timestamp

    for pause_event in seal_tx.events["Paused"]:
        assert pause_event["duration"] == pause_duration

    assert gate_seal_v3.is_expired()
    with reverts("gate seal: expired"):
        gate_seal_v3.seal(sealables, {"from": gate_seal_committee})

    assert contracts.vault_hub.isPaused()
    assert (
        contracts.vault_hub.getResumeSinceTimestamp()
        == seal_tx.timestamp + pause_duration
    )

    assert contracts.predeposit_guarantee.isPaused()
    assert (
        contracts.predeposit_guarantee.getResumeSinceTimestamp()
        == seal_tx.timestamp + pause_duration
    )

    chain.sleep(pause_duration + 1)
    chain.mine(1)

    assert not contracts.vault_hub.isPaused()
    assert not contracts.predeposit_guarantee.isPaused()

def _wait_for_next_ref_slot():
    wait_to_next_available_report_time(contracts.hash_consensus_for_validators_exit_bus_oracle)
    ref_slot, _ = contracts.hash_consensus_for_validators_exit_bus_oracle.getCurrentFrame()
    return ref_slot
