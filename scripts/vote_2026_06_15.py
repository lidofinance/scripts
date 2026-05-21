"""
Vote 2026_06_15

1. Submit a Dual Governance proposal to migrate 11 pausable contracts from legacy GateSeals to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 per LIP-34

# ===== WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 =====
1.1. Revoke PAUSE_ROLE from GateSeal 0x8A854C4E750CDf24f138f34A9061b2f556066912 on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1
1.2. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1
1.3. Register WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1 on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C

# ===== ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e =====
1.4. Revoke PAUSE_ROLE from GateSeal 0xA6BC802fAa064414AA62117B4a53D27fFfF741F1 on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e
1.5. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e
1.6. Register ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C

# ===== TriggerableWithdrawalsGateway 0xDC00116a0D3E064427dA2600449cfD2566B3037B =====
1.7. Revoke PAUSE_ROLE from GateSeal 0xA6BC802fAa064414AA62117B4a53D27fFfF741F1 on TriggerableWithdrawalsGateway 0xDC00116a0D3E064427dA2600449cfD2566B3037B
1.8. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on TriggerableWithdrawalsGateway 0xDC00116a0D3E064427dA2600449cfD2566B3037B
1.9. Register TriggerableWithdrawalsGateway 0xDC00116a0D3E064427dA2600449cfD2566B3037B on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C

# ===== VaultHub 0x1d201BE093d847f6446530Efb0E8Fb426d176709 =====
1.10. Revoke PAUSE_ROLE from GateSeal 0x881dAd714679A6FeaA636446A0499101375A365c on VaultHub 0x1d201BE093d847f6446530Efb0E8Fb426d176709
1.11. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on VaultHub 0x1d201BE093d847f6446530Efb0E8Fb426d176709
1.12. Register VaultHub 0x1d201BE093d847f6446530Efb0E8Fb426d176709 on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C

# ===== PredepositGuarantee 0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3 =====
1.13. Revoke PAUSE_ROLE from GateSeal 0x881dAd714679A6FeaA636446A0499101375A365c on PredepositGuarantee 0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3
1.14. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on PredepositGuarantee 0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3
1.15. Register PredepositGuarantee 0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3 on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C

# ===== CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F =====
1.16. Revoke PAUSE_ROLE from GateSeal 0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3 on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F
1.17. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F
1.18. Register CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f

# ===== CSAccounting 0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da =====
1.19. Revoke PAUSE_ROLE from GateSeal 0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3 on CSAccounting 0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da
1.20. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on CSAccounting 0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da
1.21. Register CSAccounting 0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f

# ===== CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB =====
1.22. Revoke PAUSE_ROLE from GateSeal 0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3 on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB
1.23. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB
1.24. Register CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f

# ===== CSVerifierV2 0xdC5FE1782B6943f318E05230d688713a560063DC =====
1.25. Revoke PAUSE_ROLE from GateSeal 0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3 on CSVerifierV2 0xdC5FE1782B6943f318E05230d688713a560063DC
1.26. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on CSVerifierV2 0xdC5FE1782B6943f318E05230d688713a560063DC
1.27. Register CSVerifierV2 0xdC5FE1782B6943f318E05230d688713a560063DC on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f

# ===== CSVettedGate 0xB314D4A76C457c93150d308787939063F4Cc67E0 =====
1.28. Revoke PAUSE_ROLE from GateSeal 0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3 on CSVettedGate 0xB314D4A76C457c93150d308787939063F4Cc67E0
1.29. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on CSVettedGate 0xB314D4A76C457c93150d308787939063F4Cc67E0
1.30. Register CSVettedGate 0xB314D4A76C457c93150d308787939063F4Cc67E0 on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f

# ===== CSEjector 0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C =====
1.31. Revoke PAUSE_ROLE from GateSeal 0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3 on CSEjector 0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C
1.32. Grant PAUSE_ROLE to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 on CSEjector 0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C
1.33. Register CSEjector 0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f

Vote #{vote number} passed & executed on {date+time}, block {blockNumber}.
"""

from typing import Dict, List, NamedTuple, Tuple

from brownie import interface

from utils.agent import agent_forward
from utils.config import (
    CIRCUIT_BREAKER,
    CS_ACCOUNTING_ADDRESS,
    CS_EJECTOR_ADDRESS,
    CS_FEE_ORACLE_ADDRESS,
    CS_GATE_SEAL_V2_ADDRESS,
    CS_VERIFIER_V2_ADDRESS,
    CS_VETTED_GATE_ADDRESS,
    CSM_ADDRESS,
    CSM_COMMITTEE_MS,
    GATE_SEAL,
    GATE_SEAL_COMMITTEE,
    GATE_SEAL_V3,
    PREDEPOSIT_GUARANTEE,
    TRIGGERABLE_WITHDRAWALS_GATEWAY,
    VALIDATORS_EXIT_BUS_ORACLE,
    VAULT_HUB,
    VEB_TWG_GATE_SEAL,
    WITHDRAWAL_QUEUE,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.dual_governance import submit_proposals
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

# ============================== Description =================================
DG_PROPOSAL_METADATA = (
    "Migrate 11 pausable contracts from legacy GateSeals to CircuitBreaker "
    "0x6019CB557978296BA3C08a7B73225C0975DFB2F7 per LIP-34"
)
DG_SUBMISSION_DESCRIPTION = (
    "1. Submit a Dual Governance proposal to migrate 11 pausable contracts from "
    "legacy GateSeals to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 per LIP-34"
)

IPFS_DESCRIPTION = """
Migrate 11 pausable contracts from legacy GateSeals to CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 per [LIP-34](https://github.com/lidofinance/lido-improvement-proposals/blob/develop/LIPS/lip-34.md) ([forum](https://research.lido.fi/t/circuitbreaker-programmable-panic-layer/11400)). For each pausable: revoke `PAUSE_ROLE` from its legacy GateSeal, grant it to CircuitBreaker, register the pausable on CircuitBreaker with the previous sealing committee as pauser.

1. **WithdrawalQueue 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1**. Pauser: 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C. Items 1.1-1.3.
2. **ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e**. Pauser: 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C. Items 1.4-1.6.
3. **TriggerableWithdrawalsGateway 0xDC00116a0D3E064427dA2600449cfD2566B3037B**. Pauser: 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C. Items 1.7-1.9.
4. **VaultHub 0x1d201BE093d847f6446530Efb0E8Fb426d176709**. Pauser: 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C. Items 1.10-1.12.
5. **PredepositGuarantee 0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3**. Pauser: 0x8772E3a2D86B9347A2688f9bc1808A6d8917760C. Items 1.13-1.15.
6. **CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F**. Pauser: 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f. Items 1.16-1.18.
7. **CSAccounting 0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da**. Pauser: 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f. Items 1.19-1.21.
8. **CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB**. Pauser: 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f. Items 1.22-1.24.
9. **CSVerifierV2 0xdC5FE1782B6943f318E05230d688713a560063DC**. Pauser: 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f. Items 1.25-1.27.
10. **CSVettedGate 0xB314D4A76C457c93150d308787939063F4Cc67E0**. Pauser: 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f. Items 1.28-1.30.
11. **CSEjector 0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C**. Pauser: 0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f. Items 1.31-1.33.
"""

# ============================== Migration ==============================
class MigrationTarget(NamedTuple):
    pausable: str
    pauser: str
    gate_seal: str


MIGRATION_TARGETS: List[MigrationTarget] = [
    MigrationTarget(WITHDRAWAL_QUEUE,                GATE_SEAL_COMMITTEE, GATE_SEAL),
    MigrationTarget(VALIDATORS_EXIT_BUS_ORACLE,      GATE_SEAL_COMMITTEE, VEB_TWG_GATE_SEAL),
    MigrationTarget(TRIGGERABLE_WITHDRAWALS_GATEWAY, GATE_SEAL_COMMITTEE, VEB_TWG_GATE_SEAL),
    MigrationTarget(VAULT_HUB,                       GATE_SEAL_COMMITTEE, GATE_SEAL_V3),
    MigrationTarget(PREDEPOSIT_GUARANTEE,            GATE_SEAL_COMMITTEE, GATE_SEAL_V3),
    MigrationTarget(CSM_ADDRESS,                     CSM_COMMITTEE_MS,    CS_GATE_SEAL_V2_ADDRESS),
    MigrationTarget(CS_ACCOUNTING_ADDRESS,           CSM_COMMITTEE_MS,    CS_GATE_SEAL_V2_ADDRESS),
    MigrationTarget(CS_FEE_ORACLE_ADDRESS,           CSM_COMMITTEE_MS,    CS_GATE_SEAL_V2_ADDRESS),
    MigrationTarget(CS_VERIFIER_V2_ADDRESS,          CSM_COMMITTEE_MS,    CS_GATE_SEAL_V2_ADDRESS),
    MigrationTarget(CS_VETTED_GATE_ADDRESS,          CSM_COMMITTEE_MS,    CS_GATE_SEAL_V2_ADDRESS),
    MigrationTarget(CS_EJECTOR_ADDRESS,              CSM_COMMITTEE_MS,    CS_GATE_SEAL_V2_ADDRESS),
]


# ============================== Call encoder ===============================
def encode_migration_calls(
    target: MigrationTarget,
    circuit_breaker: interface.CircuitBreaker,
) -> List[Tuple[str, str]]:
    pausable = interface.IPausableUntilWithRoles(target.pausable)
    pause_role = str(pausable.PAUSE_ROLE())
    return [
        agent_forward([(pausable.address, pausable.revokeRole.encode_input(pause_role, target.gate_seal))]),
        agent_forward([(pausable.address, pausable.grantRole.encode_input(pause_role, circuit_breaker.address))]),
        agent_forward(
            [(circuit_breaker.address, circuit_breaker.registerPauser.encode_input(pausable.address, target.pauser))]
        ),
    ]


# ================== Verify: hardcoded vs. on-chain ====================
def assert_target_matches_chain(target: MigrationTarget) -> None:
    gate_seal = interface.GateSeal(target.gate_seal)
    pausable_addr = target.pausable.lower()

    expected_pauser = target.pauser.lower()
    sealing_committee = str(gate_seal.get_sealing_committee()).lower()
    assert sealing_committee == expected_pauser, (
        f"Pauser mismatch on GateSeal {target.gate_seal}: "
        f"expected {expected_pauser}, got on-chain sealing committee {sealing_committee}"
    )

    sealables = {str(s).lower() for s in gate_seal.get_sealables()}
    assert pausable_addr in sealables, (
        f"Pausable {pausable_addr} not in GateSeal {target.gate_seal} sealables ({sorted(sealables)})"
    )


# ================================== Main ====================================
def get_dg_items() -> List[Tuple[str, str]]:
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)
    items: List[Tuple[str, str]] = []
    for target in MIGRATION_TARGETS:
        assert_target_matches_chain(target)
        items.extend(encode_migration_calls(target, circuit_breaker))
    return items


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    dg_items = get_dg_items()
    dg_call_script = submit_proposals([(dg_items, DG_PROPOSAL_METADATA)])

    vote_desc_items = [DG_SUBMISSION_DESCRIPTION]
    call_script_items = [dg_call_script[0]]

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent
        else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
