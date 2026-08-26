"""
Hoodi vote to activate the CSM deployment for 0x02 withdrawal credentials.

1. Submit a Dual Governance proposal to activate CSM 0x02
1.1. Add CSM 0x02 to the Staking Router
1.2. Grant REQUEST_BURN_MY_STETH_ROLE on Burner to CSM 0x02 Accounting
1.3. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE on Triggerable Withdrawals Gateway to CSM 0x02 Ejector
1.4. Grant RESUME_ROLE on CSM 0x02 to Aragon Agent
1.5. Resume CSM 0x02
1.6. Revoke RESUME_ROLE on CSM 0x02 from Aragon Agent
1.7. Set the initial epoch on CSM 0x02 HashConsensus
1.8. Register CSM 0x02 on CircuitBreaker
1.9. Register CSM 0x02 Accounting on CircuitBreaker
1.10. Register CSM 0x02 FeeOracle on CircuitBreaker
1.11. Register CSM 0x02 Verifier on CircuitBreaker
1.12. Register CSM 0x02 Ejector on CircuitBreaker
2. Add ReportWithdrawalsForSlashedValidators for CSM 0x02 to Easy Track
3. Add SettleGeneralDelayedPenalty for CSM 0x02 to Easy Track
4. Add UpdateStakingModuleShareLimits for CSM 0x02 to Easy Track
"""

from typing import Dict, List, Tuple

from brownie import interface

from utils.agent import agent_forward
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.dual_governance import submit_proposals
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.voting import bake_vote_items, confirm_vote_script, create_vote


# ============================== Addresses ===================================
ARAGON_AGENT = "0x0534aA41907c9631fae990960bCC72d75fA7cfeD"
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

EASYTRACK_CSM0X02_REPORT_WITHDRAWALS_FACTORY = "0x0b384D661101Fe7F56caa421547b243e03ED4E65"
EASYTRACK_CSM0X02_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY = "0x2eCf179d5e840e56054E214438008F19E46711bC"
EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x05F2F2eb01A8e8C20FDD07EAb93640cd8304aaC9"


# ============================== Parameters ==================================
CSM0X02_NAME = "Community Staking 0x02"
CSM0X02_TARGET_SHARE_BP = 800
CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 1_000
CSM0X02_MODULE_FEE_BP = 200
CSM0X02_TREASURY_FEE_BP = 800
CSM0X02_MAX_DEPOSITS_PER_BLOCK = 30
CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE = 0x02

# Starts on 2026-09-09 13:33:12 UTC, after a full 14-day frame has passed since
# the expected 2026-08-26 12:00-13:00 UTC vote, with an extra 33-minute buffer.
# This keeps CSM, CSM 0x02, and Curated v2 reports on Monday, Wednesday, and Friday.
CSM0X02_ORACLE_INITIAL_EPOCH = 121_738


# ============================= Description ==================================
IPFS_DESCRIPTION = """
1. **Submit a Dual Governance proposal to activate the CSM deployment for 0x02 withdrawal credentials on Hoodi**, including its Staking Router registration, protocol permissions, oracle schedule, and CircuitBreaker configuration. Items 1.1-1.12.
2. **Add the CSM 0x02 Easy Track factories** for reporting slashed withdrawals, settling general delayed penalties, and updating the module share limits. Items 2-4.
"""

DG_PROPOSAL_METADATA = "Activate the CSM deployment for 0x02 withdrawal credentials on Hoodi"
DG_SUBMISSION_DESCRIPTION = "1. Submit a Dual Governance proposal to activate CSM 0x02"


def get_dg_items() -> List[Tuple[str, str]]:
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    burner = interface.Burner(BURNER)
    twg = interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)
    csm = interface.CSModule(CSM0X02)
    hash_consensus = interface.HashConsensus(CSM0X02_HASH_CONSENSUS)
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)

    return [
        agent_forward(
            [
                (
                    staking_router.address,
                    staking_router.addStakingModule.encode_input(
                        CSM0X02_NAME,
                        CSM0X02,
                        (
                            CSM0X02_TARGET_SHARE_BP,
                            CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP,
                            CSM0X02_MODULE_FEE_BP,
                            CSM0X02_TREASURY_FEE_BP,
                            CSM0X02_MAX_DEPOSITS_PER_BLOCK,
                            CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE,
                            CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE,
                        ),
                    ),
                )
            ]
        ),
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=burner,
                    role_name="REQUEST_BURN_MY_STETH_ROLE",
                    grant_to=CSM0X02_ACCOUNTING,
                )
            ]
        ),
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=twg,
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=CSM0X02_EJECTOR,
                )
            ]
        ),
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=csm,
                    role_name="RESUME_ROLE",
                    grant_to=ARAGON_AGENT,
                )
            ]
        ),
        agent_forward([(csm.address, csm.resume.encode_input())]),
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=csm,
                    role_name="RESUME_ROLE",
                    revoke_from=ARAGON_AGENT,
                )
            ]
        ),
        agent_forward(
            [
                (
                    hash_consensus.address,
                    hash_consensus.updateInitialEpoch.encode_input(CSM0X02_ORACLE_INITIAL_EPOCH),
                )
            ]
        ),
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02, CSM_COMMITTEE),
                )
            ]
        ),
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02_ACCOUNTING, CSM_COMMITTEE),
                )
            ]
        ),
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02_FEE_ORACLE, CSM_COMMITTEE),
                )
            ]
        ),
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02_VERIFIER, CSM_COMMITTEE),
                )
            ]
        ),
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02_EJECTOR, CSM_COMMITTEE),
                )
            ]
        ),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    csm = interface.CSModule(CSM0X02)
    staking_router = interface.StakingRouter(STAKING_ROUTER)

    dg_call_script = submit_proposals([(get_dg_items(), DG_PROPOSAL_METADATA)])

    vote_desc_items, call_script_items = zip(
        (
            DG_SUBMISSION_DESCRIPTION,
            dg_call_script[0],
        ),
        (
            "2. Add ReportWithdrawalsForSlashedValidators for CSM 0x02 to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_CSM0X02_REPORT_WITHDRAWALS_FACTORY,
                permissions=create_permissions(csm, "reportSlashedWithdrawnValidators"),
            ),
        ),
        (
            "3. Add SettleGeneralDelayedPenalty for CSM 0x02 to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_CSM0X02_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY,
                permissions=create_permissions(csm, "settleGeneralDelayedPenalty"),
            ),
        ),
        (
            "4. Add UpdateStakingModuleShareLimits for CSM 0x02 to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
                permissions=create_permissions(staking_router, "updateStakingModule"),
            ),
        ),
    )

    return list(vote_desc_items), list(call_script_items)


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
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
