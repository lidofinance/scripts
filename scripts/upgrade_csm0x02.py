"""
Mainnet upgrade vote to activate 0x02 CSM, update curated module limits, and add CSM and LOL LDO Easy Track factories.

1. Submit a Dual Governance proposal to activate 0x02 CSM with a 0.01% stake share limit and 32 top-up queue limit,
   set CMv1 stake share limit to 0, and set Consensys target validators limit to 0 in CMv1 and CMv2 (soft mode).
    1.1. Restrict proposal execution time to 14:00-23:00 UTC on Dual Governance Time Constraints
    1.2.1. Add 0x02 CSM with name "Community Staking 0x02" to Staking Router:
           stake share limit 1 BP (0.01%), priority exit share threshold 240 BP (2.4%),
           module fee 200 BP (2%), treasury fee 800 BP (8%), maximum 30 deposits per block,
           minimum deposit block distance 25, withdrawal credentials type 0x02
    1.3.1. Grant REQUEST_BURN_MY_STETH_ROLE to 0x02 CSM Accounting on Burner
    1.4.1. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to 0x02 CSM Ejector on Triggerable Withdrawals Gateway
    1.5.1. Grant RESUME_ROLE to Aragon Agent on 0x02 CSM
    1.6.1. Enable 0x02 CSM
    1.7.1. Revoke RESUME_ROLE from Aragon Agent on 0x02 CSM
    1.8.1. Set 0x02 CSM HashConsensus initial epoch to 494340
    1.9.1. Register 0x02 CSM Module on CircuitBreaker with pauser CSM Committee
    1.10.1. Register 0x02 CSM Accounting on CircuitBreaker with pauser CSM Committee
    1.11.1. Register 0x02 CSM FeeOracle on CircuitBreaker with pauser CSM Committee
    1.12.1. Register 0x02 CSM Verifier on CircuitBreaker with pauser CSM Committee
    1.13.1. Register 0x02 CSM Ejector on CircuitBreaker with pauser CSM Committee
    1.14.1. Set CMv1 (module ID 1) stake share limit and priority exit share threshold to 0 on Staking Router:
            module fee 350 BP (3.5%), treasury fee 650 BP (6.5%), maximum 150 deposits per block,
            minimum deposit block distance 25
    1.15.1. Set target validators limit for Consensys (operator ID 21) in CMv1 (module ID 1)
            to 0 in soft mode (1) on Staking Router
    1.16.1. Set target validators limit for Consensys (operator ID 6) in CMv2 (module ID 4)
            to 0 in soft mode (1) on Staking Router
    1.17.1. Grant MANAGE_TOP_UP_QUEUE_ROLE to Aragon Agent on 0x02 CSM
    1.18.1. Set top-up queue limit to 32 on 0x02 CSM
    1.19.1. Revoke MANAGE_TOP_UP_QUEUE_ROLE from Aragon Agent on 0x02 CSM
2. Add ReportWithdrawalsForSlashedValidators EVM script factory for 0x02 CSM to Easy Track
3. Add SettleGeneralDelayedPenalty EVM script factory for 0x02 CSM to Easy Track
4. Add UpdateStakingModuleShareLimits EVM script factory for 0x02 CSM to Easy Track
5. Add LOL LDO TopUpAllowedRecipients EVM script factory to Easy Track
   for top-ups with a limit of 7.5M LDO per 12-month period
"""

from brownie import interface

from utils.agent import agent_forward
from utils.allowed_recipients_registry import create_top_up_allowed_recipient_permission
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
DUAL_GOVERNANCE_TIME_CONSTRAINTS = "0x2a30F5aC03187674553024296bed35Aa49749DDa"

# https://docs.lido.fi/deployed-contracts/#community-staking-module-0x02
CSM0X02_MODULE = "0x792Cd25e4aE3578375031FB55e048E163A804F7B"
CSM0X02_ACCOUNTING = "0x3696dDd942A9e156F5D4728505D1b9a32dCef900"
CSM0X02_FEE_ORACLE = "0x0fB5EC09Cc975d8E1aF43063e51882798814f311"
CSM0X02_HASH_CONSENSUS = "0xd5a965FAab2d02D3cC2286A9da42d09F0F2aE210"
CSM0X02_VERIFIER = "0x69b4C32a43565e768794D41b4A265F86dE61b861"
CSM0X02_EJECTOR = "0x2EE500885870b020e84E86a09A5d26D1EEec3E5E"

# https://docs.lido.fi/deployed-contracts/#easy-track-factories-for-staking-modules
EASYTRACK_CSM0X02_REPORT_WITHDRAWALS_FACTORY = "0x8D74020d8EACCdFf0366dAAFfb96e6c98CDFc112"
EASYTRACK_CSM0X02_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY = "0x0B676AdEABcf4A696187cfAb90290Aa3ac51aFA2"
EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x5b0De22E65C068430f6e769754D51133775408cc"

# https://docs.lido.fi/deployed-contracts/#easy-track-factories-for-staking-modules
LOL_LDO_REGISTRY = "0xf1e9c3bD021ED1419Dd3b37f9b6E49Eb662877Fe"
LOL_LDO_TOP_UP_FACTORY = "0xa3e98cb26F1277B623Edb95cee3bd33269b305F7"

# ============================== Parameters ==================================
# Execute only after the current AccountingOracle report is fully processed,
# including all extra-data chunks, and before the next reference slot.
# This daily window only checks time; report completion must be checked before enactment.
TIME_WINDOW_FROM = 14 * 3600
TIME_WINDOW_TO = 23 * 3600

CSM0X02_NAME = "Community Staking 0x02"

# Initial bootstrap share: 0.01% (1 basis point).
CSM0X02_TARGET_SHARE_BP = 1
CSM0X02_TOP_UP_QUEUE_LIMIT = 32
# Keep the planned 2.4% priority-exit threshold unchanged during bootstrap.
# It was set using the same multiplier used for CSM 0x01 applied to the planned 2% share.
CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 240
# 2% NO / 8% DAO with the deployment's defaultRewardShareBP = 10000.
CSM0X02_MODULE_FEE_BP = 200
CSM0X02_TREASURY_FEE_BP = 800
# Keep the current CSM 0x01 deposit limits.
CSM0X02_MAX_DEPOSITS_PER_BLOCK = 30
CSM0X02_MIN_DEPOSIT_BLOCK_DISTANCE = 25
CSM0X02_WITHDRAWAL_CREDENTIALS_TYPE = 0x02

CURATED_V1_MODULE_ID = 1
CURATED_V2_MODULE_ID = 4
CONSENSYS_V1_NODE_OPERATOR_ID = 21
CONSENSYS_V2_NODE_OPERATOR_ID = 6
NO_TARGET_LIMIT_SOFT_MODE = 1

# Zero the priority-exit threshold to prioritize exits from CMv1.
# Keep the current mainnet CMv1 fees and deposit limits unchanged.
CURATED_V1_TARGET_SHARE_BP = 0
CURATED_V1_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 0
CURATED_V1_MODULE_FEE_BP = 350
CURATED_V1_TREASURY_FEE_BP = 650
CURATED_V1_MAX_DEPOSITS_PER_BLOCK = 150
CURATED_V1_MIN_DEPOSIT_BLOCK_DISTANCE = 25

# First report window opens on 2026-12-07 at 13:36:23 UTC (Monday).
# Its full 6,300-epoch (28-day) observation period starts on 2026-11-09 at 13:36:23 UTC,
# after the expected 2026-10-23 DG enactment for a vote launched on 2026-10-14.
# This places reports midway between CSM 0x01 windows and about a week from CMv2 windows.
# So the resulting report schedule for staking modules is:
# Week   |        1 |        2 |        3 |        4 |        5 |        6 |        7 |
# -------+----------+----------+----------+----------+----------+----------+----------+
# Module | 0x01 CSM |   CMv2   | 0x02 CSM |   CMv2   | 0x01 CSM |   CMv2   | 0x02 CSM |
CSM0X02_ORACLE_INITIAL_EPOCH = 494_340


# ============================= Description ==================================
IPFS_DESCRIPTION = """
# 0x02 CSM, CMv1 stakeShareLimit -> 0, Consensys target limit → 0, LDO Liquidity ET Factory

1. **Activate the Community Staking Module for 0x02 withdrawal credentials**, as per [Snapshot decision](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0xed2a3b1f796cefdd531abe14ba01363b2da7887434cefdd54ba71ffb6dff59a7). Audits: CSMv3 and CMv2 — [Statemind](https://github.com/lidofinance/audits/blob/main/Statemind%20Lido%20CSM%20v3%20and%20CM%20v2%20Audit%20Report%2006-2026.pdf), [Certora](https://github.com/lidofinance/audits/blob/main/Certora%20Lido%20CSM%20v3%20and%20CM%20v2%20Audit%20Report%20-%2006-2026.pdf); Easy Track factories — [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20Easy%20Track%20Factories%20(SRv3%20CSMv3%20CMv2)%20Security%20Audit%20Report%2007-2026.pdf) | Deployment verification — MixBytes: [0x02 CSM](https://github.com/lidofinance/audits/blob/main/Lido%20CSM%200x02%20Deployment%20Verification%20Report.pdf), [0x02 CSM Easy Track factories](https://github.com/lidofinance/audits/blob/main/Lido%20Easy%20Track%20Factories%20CSM%200x02%20Deployment%20Verification%20Report.pdf)
    - Restrict proposal execution to 14:00-23:00 UTC. Item 1.1.
    - Register, enable and configure 0x02 CSM with an initial stake share limit of 0.01% and top-up queue limit of 32. Items 1.2.1 - 1.8.1, 1.17.1 - 1.19.1.
    - Register 0x02 CSM Module, Accounting, FeeOracle, Verifier and Ejector on CircuitBreaker with the [CSM Committee](https://docs.lido.fi/multisigs/committees#29-community-staking-module-committee) as pauser. Items 1.9.1 - 1.13.1.
    - Add 0x02 CSM Easy Track factories to report withdrawals for slashed validators, settle delayed penalties, and update share limit. Items 2 - 4.
2. **Set CMv1 stake share limit and priority exit share threshold to 0**, as per [Snapshot decision](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x7b07bc31f0b38b69a117473031bc126becc70b9fa37246b53d9fe5a841c814f5). Item 1.14.1
3. **Set Consensys target validators limit to 0 in CMv1 and CMv2 (soft mode)**, as [proposed on the forum](https://research.lido.fi/t/security-disclosure-metamask-staking-precautionary-out-of-order-exits/11961/2). Items 1.15.1 - 1.16.1.
4. **Add LOL LDO Easy Track factory for top-ups with a limit of 7.5M LDO per 12-month period**, under the [Snapshot-approved liquidity mandate](https://snapshot.box/#/s:lido-snapshot.eth/proposal/0x71b50a792e4606e593ff4502b1753aa3fb894a0bf994d6a5f1d42cee9c94a594). Item 5.
"""

DG_PROPOSAL_METADATA = (
    "Activate 0x02 CSM with a 0.01% stake share limit and 32 top-up queue limit, set CMv1 stake share limit to 0, "
    "set Consensys target validators limit to 0 in CMv1 and CMv2 (soft mode)"
)
DG_SUBMISSION_DESCRIPTION = (
    "1. Submit a Dual Governance proposal to activate 0x02 CSM with a 0.01% stake share limit and 32 top-up queue limit, "
    "set CMv1 stake share limit to 0, set Consensys target validators limit to 0 in CMv1 and CMv2 (soft mode)"
)


def get_dg_items() -> list[tuple[str, str]]:
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    burner = interface.Burner(BURNER)
    twg = interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)
    csm = interface.CSModule(CSM0X02_MODULE)
    hash_consensus = interface.HashConsensus(CSM0X02_HASH_CONSENSUS)
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)
    time_constraints = interface.TimeConstraints(DUAL_GOVERNANCE_TIME_CONSTRAINTS)

    return [
        # 1.1. Restrict proposal execution time to 14:00-23:00 UTC on Dual Governance Time Constraints.
        (
            time_constraints.address,
            time_constraints.checkTimeWithinDayTimeAndEmit.encode_input(TIME_WINDOW_FROM, TIME_WINDOW_TO),
        ),
        # 1.2.1. Add 0x02 CSM with name "Community Staking 0x02" to Staking Router:
        # stake share limit 1 BP (0.01%), priority exit share threshold 240 BP (2.4%),
        # module fee 200 BP (2%), treasury fee 800 BP (8%), maximum 30 deposits per block,
        # minimum deposit block distance 25, withdrawal credentials type 0x02.
        agent_forward(
            [
                (
                    staking_router.address,
                    staking_router.addStakingModule.encode_input(
                        CSM0X02_NAME,
                        CSM0X02_MODULE,
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
        # 1.3.1. Grant REQUEST_BURN_MY_STETH_ROLE to 0x02 CSM Accounting on Burner.
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=burner,
                    role_name="REQUEST_BURN_MY_STETH_ROLE",
                    grant_to=CSM0X02_ACCOUNTING,
                )
            ]
        ),
        # 1.4.1. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to 0x02 CSM Ejector on Triggerable Withdrawals Gateway.
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=twg,
                    role_name="ADD_FULL_WITHDRAWAL_REQUEST_ROLE",
                    grant_to=CSM0X02_EJECTOR,
                )
            ]
        ),
        # 1.5.1. Grant RESUME_ROLE to Aragon Agent on 0x02 CSM.
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=csm,
                    role_name="RESUME_ROLE",
                    grant_to=ARAGON_AGENT,
                )
            ]
        ),
        # 1.6.1. Enable 0x02 CSM.
        agent_forward([(csm.address, csm.resume.encode_input())]),
        # 1.7.1. Revoke RESUME_ROLE from Aragon Agent on 0x02 CSM.
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=csm,
                    role_name="RESUME_ROLE",
                    revoke_from=ARAGON_AGENT,
                )
            ]
        ),
        # 1.8.1. Set 0x02 CSM HashConsensus initial epoch to 494340.
        agent_forward(
            [
                (
                    hash_consensus.address,
                    hash_consensus.updateInitialEpoch.encode_input(CSM0X02_ORACLE_INITIAL_EPOCH),
                )
            ]
        ),
        # 1.9.1. Register 0x02 CSM Module on CircuitBreaker with pauser CSM Committee.
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02_MODULE, CSM_COMMITTEE),
                )
            ]
        ),
        # 1.10.1. Register 0x02 CSM Accounting on CircuitBreaker with pauser CSM Committee.
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02_ACCOUNTING, CSM_COMMITTEE),
                )
            ]
        ),
        # 1.11.1. Register 0x02 CSM FeeOracle on CircuitBreaker with pauser CSM Committee.
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02_FEE_ORACLE, CSM_COMMITTEE),
                )
            ]
        ),
        # 1.12.1. Register 0x02 CSM Verifier on CircuitBreaker with pauser CSM Committee.
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02_VERIFIER, CSM_COMMITTEE),
                )
            ]
        ),
        # 1.13.1. Register 0x02 CSM Ejector on CircuitBreaker with pauser CSM Committee.
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CSM0X02_EJECTOR, CSM_COMMITTEE),
                )
            ]
        ),
        # 1.14.1. Set CMv1 (module ID 1) stake share limit and priority exit share threshold to 0 on Staking Router:
        # module fee 350 BP (3.5%), treasury fee 650 BP (6.5%), maximum 150 deposits per block,
        # minimum deposit block distance 25.
        agent_forward(
            [
                (
                    staking_router.address,
                    staking_router.updateStakingModule.encode_input(
                        CURATED_V1_MODULE_ID,
                        CURATED_V1_TARGET_SHARE_BP,
                        CURATED_V1_PRIORITY_EXIT_SHARE_THRESHOLD_BP,
                        CURATED_V1_MODULE_FEE_BP,
                        CURATED_V1_TREASURY_FEE_BP,
                        CURATED_V1_MAX_DEPOSITS_PER_BLOCK,
                        CURATED_V1_MIN_DEPOSIT_BLOCK_DISTANCE,
                    ),
                )
            ]
        ),
        # 1.15.1. Set target validators limit for Consensys (operator ID 21) in CMv1 (module ID 1)
        # to 0 in soft mode (1) on Staking Router.
        agent_forward(
            [
                (
                    staking_router.address,
                    staking_router.updateTargetValidatorsLimits.encode_input(
                        CURATED_V1_MODULE_ID, CONSENSYS_V1_NODE_OPERATOR_ID, NO_TARGET_LIMIT_SOFT_MODE, 0
                    ),
                )
            ]
        ),
        # 1.16.1. Set target validators limit for Consensys (operator ID 6) in CMv2 (module ID 4)
        # to 0 in soft mode (1) on Staking Router.
        agent_forward(
            [
                (
                    staking_router.address,
                    staking_router.updateTargetValidatorsLimits.encode_input(
                        CURATED_V2_MODULE_ID, CONSENSYS_V2_NODE_OPERATOR_ID, NO_TARGET_LIMIT_SOFT_MODE, 0
                    ),
                )
            ]
        ),
        # 1.17.1. Grant MANAGE_TOP_UP_QUEUE_ROLE to Aragon Agent on 0x02 CSM.
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=csm,
                    role_name="MANAGE_TOP_UP_QUEUE_ROLE",
                    grant_to=ARAGON_AGENT,
                )
            ]
        ),
        # 1.18.1. Set top-up queue limit to 32 on 0x02 CSM.
        agent_forward([(csm.address, csm.setTopUpQueueLimit.encode_input(CSM0X02_TOP_UP_QUEUE_LIMIT))]),
        # 1.19.1. Revoke MANAGE_TOP_UP_QUEUE_ROLE from Aragon Agent on 0x02 CSM.
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=csm,
                    role_name="MANAGE_TOP_UP_QUEUE_ROLE",
                    revoke_from=ARAGON_AGENT,
                )
            ]
        ),
    ]


def get_vote_items() -> tuple[list[str], list[tuple[str, str]]]:
    csm = interface.CSModule(CSM0X02_MODULE)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    update_staking_module_share_limits_factory = interface.UpdateStakingModuleShareLimits(
        EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY
    )

    dg_call_script, *_ = submit_proposals([(get_dg_items(), DG_PROPOSAL_METADATA)])

    vote_desc_items, call_script_items = zip(
        (
            DG_SUBMISSION_DESCRIPTION,
            dg_call_script,
        ),
        (
            "2. Add ReportWithdrawalsForSlashedValidators EVM script factory for 0x02 CSM to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_CSM0X02_REPORT_WITHDRAWALS_FACTORY,
                permissions=create_permissions(csm, "reportSlashedWithdrawnValidators"),
            ),
        ),
        (
            "3. Add SettleGeneralDelayedPenalty EVM script factory for 0x02 CSM to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_CSM0X02_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY,
                permissions=create_permissions(csm, "settleGeneralDelayedPenalty"),
            ),
        ),
        (
            "4. Add UpdateStakingModuleShareLimits EVM script factory for 0x02 CSM to Easy Track",
            add_evmscript_factory(
                factory=EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
                permissions=(
                    create_permissions(update_staking_module_share_limits_factory, "validateParams")
                    + create_permissions(staking_router, "updateModuleShares")[2:]
                ),
            ),
        ),
        (
            "5. Add LOL LDO TopUpAllowedRecipients EVM script factory to Easy Track "
            "for top-ups with a limit of 7.5M LDO per 12-month period",
            add_evmscript_factory(
                factory=LOL_LDO_TOP_UP_FACTORY,
                permissions=create_top_up_allowed_recipient_permission(registry_address=LOL_LDO_REGISTRY),
            ),
        ),
    )

    return list(vote_desc_items), list(call_script_items)


def start_vote(tx_params: dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )
    if not confirm_vote_script(vote_items, silent, desc_ipfs):
        raise SystemExit(1)

    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)


def main():
    tx_params: dict[str, str] = {"from": get_deployer_account().address}
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
