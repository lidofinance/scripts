"""
Mainnet vote to activate the CSM deployment for 0x02 withdrawal credentials.

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
ARAGON_AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
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

EASYTRACK_CSM0X02_REPORT_WITHDRAWALS_FACTORY = TODO_ADDRESS
EASYTRACK_CSM0X02_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY = TODO_ADDRESS
EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = TODO_ADDRESS

DEPLOYMENT_ADDRESSES = {
    "CSM0X02": CSM0X02,
    "CSM0X02_ACCOUNTING": CSM0X02_ACCOUNTING,
    "CSM0X02_FEE_ORACLE": CSM0X02_FEE_ORACLE,
    "CSM0X02_HASH_CONSENSUS": CSM0X02_HASH_CONSENSUS,
    "CSM0X02_VERIFIER": CSM0X02_VERIFIER,
    "CSM0X02_EJECTOR": CSM0X02_EJECTOR,
    "EASYTRACK_CSM0X02_REPORT_WITHDRAWALS_FACTORY": EASYTRACK_CSM0X02_REPORT_WITHDRAWALS_FACTORY,
    "EASYTRACK_CSM0X02_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY": EASYTRACK_CSM0X02_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY,
    "EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY": (
        EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY
    ),
}


# ============================== Parameters ==================================
CSM0X02_NAME = "Community Staking 0x02"

# Mirrors the current mainnet CSM module configuration.
CSM0X02_TARGET_SHARE_BP = 900
CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 1_080
CSM0X02_MODULE_FEE_BP = 600
CSM0X02_TREASURY_FEE_BP = 400
CSM0X02_MAX_DEPOSITS_PER_BLOCK = 30
CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE = 0x02

# TODO: Calculate for the expected mainnet vote date after a complete oracle frame.
CSM0X02_ORACLE_INITIAL_EPOCH = 0


# ============================= Description ==================================
IPFS_DESCRIPTION = """
1. **Submit a Dual Governance proposal to activate the CSM deployment for 0x02 withdrawal credentials on Ethereum mainnet**, including its Staking Router registration, protocol permissions, oracle schedule, and CircuitBreaker configuration. Items 1.1-1.12.
2. **Add the CSM 0x02 Easy Track factories** for reporting slashed withdrawals, settling general delayed penalties, and updating the module share limits. Items 2-4.
"""

DG_PROPOSAL_METADATA = "Activate the CSM deployment for 0x02 withdrawal credentials on Ethereum mainnet"
DG_SUBMISSION_DESCRIPTION = "1. Submit a Dual Governance proposal to activate CSM 0x02"


def validate_configuration() -> None:
    unresolved_addresses = [name for name, address in DEPLOYMENT_ADDRESSES.items() if address == TODO_ADDRESS]
    if unresolved_addresses:
        raise ValueError(f"Set deployment addresses before building the vote: {', '.join(unresolved_addresses)}")

    if CSM0X02_ORACLE_INITIAL_EPOCH <= 0:
        raise ValueError("Set CSM0X02_ORACLE_INITIAL_EPOCH before building the vote")


def get_dg_items() -> List[Tuple[str, str]]:
    validate_configuration()

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
    validate_configuration()

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
