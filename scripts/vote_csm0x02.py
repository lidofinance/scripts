"""
Mainnet vote to activate the CSM deployment for 0x02 withdrawal credentials.

1. Submit a Dual Governance proposal to activate CSM 0x02, update curated module limits,
   and reconfigure a.DI governance forwarding to BNB Chain
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
1.13. Set the CMv1 stake share limit to 0
1.14. Set the Consensys operator target limit to 0 in CMv1 (soft mode)
1.15. Set the Consensys operator target limit to 0 in CMv2 (soft mode)
1.16. Forward an a.DI message to the BNB Chain CrossChainExecutor with an action set for the BNB Chain
      CrossChainController: disallow the Wormhole adapter and require 2 confirmations for messages from Ethereum
1.17. Disable the Wormhole adapter for BNB Chain on the Ethereum CrossChainController
2. Add ReportWithdrawalsForSlashedValidators for CSM 0x02 to Easy Track
3. Add SettleGeneralDelayedPenalty for CSM 0x02 to Easy Track
4. Add UpdateStakingModuleShareLimits for CSM 0x02 to Easy Track
"""

from typing import Dict, List, Tuple

from brownie import interface
from eth_abi import encode

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

CSM0X02 = "0x792Cd25e4aE3578375031FB55e048E163A804F7B"
CSM0X02_ACCOUNTING = "0x3696dDd942A9e156F5D4728505D1b9a32dCef900"
CSM0X02_FEE_ORACLE = "0x0fB5EC09Cc975d8E1aF43063e51882798814f311"
CSM0X02_HASH_CONSENSUS = "0xd5a965FAab2d02D3cC2286A9da42d09F0F2aE210"
CSM0X02_VERIFIER = "0x69b4C32a43565e768794D41b4A265F86dE61b861"
CSM0X02_EJECTOR = "0x2EE500885870b020e84E86a09A5d26D1EEec3E5E"

EASYTRACK_CSM0X02_REPORT_WITHDRAWALS_FACTORY = "0x8D74020d8EACCdFf0366dAAFfb96e6c98CDFc112"
EASYTRACK_CSM0X02_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY = "0x0B676AdEABcf4A696187cfAb90290Aa3ac51aFA2"
EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x5b0De22E65C068430f6e769754D51133775408cc"

# a.DI governance forwarding to BNB Chain
# https://docs.lido.fi/deployed-contracts/#adi-governance-forwarding-eth
# https://docs.lido.fi/deployed-contracts/#adi-governance-forwarding-bsc
ETHEREUM_CROSS_CHAIN_CONTROLLER = "0x93559892D3C7F66DE4570132d68b69BD3c369A7C"
ETHEREUM_WORMHOLE_ADAPTER = "0xEDc0D2cb2289BBa1587424dd42bDD1ca7eAbDF17"
BNB_CROSS_CHAIN_CONTROLLER = "0x40C4464fCa8caCd550C33B39d674fC257966022F"
BNB_CROSS_CHAIN_EXECUTOR = "0x8E5175D17f74d1D512de59b2f5d5A5d8177A123d"
BNB_WORMHOLE_ADAPTER = "0xBb1E43408BbF2C767Ff3Bd5bBC34E183CC1Ef119"

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

# Initial share: 2%.
CSM0X02_TARGET_SHARE_BP = 200
# Match the current CSM 0x01 priority-exit multiplier: 1080 / 900 = 1.2.
# https://etherscan.io/tx/0x2d418e0fc5f9276ad33cf4e525285f4d480f2beb9b71ea1fe3cc5b4ca4d7876f#eventlog
CSM0X02_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 240
# 2% NO / 8% DAO with the deployment's defaultRewardShareBP = 10000.
# https://snapshot.box/#/s:lido-snapshot.eth/proposal/0xed2a3b1f796cefdd531abe14ba01363b2da7887434cefdd54ba71ffb6dff59a7
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

# Period 2: stop new deposits into CMv1 while consolidations continue.
# https://research.lido.fi/t/future-of-the-curated-module-cmv2-landscape/10929/45
# Keep the other current mainnet CMv1 router parameters unchanged.
CURATED_V1_TARGET_SHARE_BP = 0
CURATED_V1_PRIORITY_EXIT_SHARE_THRESHOLD_BP = 10_000
CURATED_V1_MODULE_FEE_BP = 350
CURATED_V1_TREASURY_FEE_BP = 650
CURATED_V1_MAX_DEPOSITS_PER_BLOCK = 150
CURATED_V1_MIN_DEPOSIT_BLOCK_DISTANCE = 25

# First report window opens on 2026-12-07 at 13:36:23 UTC (Monday).
# Its full 6,300-epoch (28-day) observation period starts on 2026-11-09 at 13:36:23 UTC,
# after the expected 2026-10-24 DG enactment for a vote launched on 2026-10-15.
# This places reports midway between CSM 0x01 windows and about a week from CMv2 windows.
CSM0X02_ORACLE_INITIAL_EPOCH = 494_340

# Wormhole shut down its Standard Relayer on 2026-04-01 and no longer delivers Lido DAO messages to BNB Chain.
# Remove the Wormhole adapter on both chains and lower the BNB Chain quorum from 3 of 4 bridges to 2 of 3.
# https://github.com/lidofinance/aave-delivery-infrastructure/issues/12
ETHEREUM_CHAIN_ID = 1
BNB_CHAIN_ID = 56
BNB_REQUIRED_CONFIRMATIONS = 2
# Gas limit for each bridge's delivery on BNB Chain. The delivery that completes the quorum also queues the action
# set on the CrossChainExecutor and needs about 880,000 gas; with less, that delivery reverts.
BNB_MESSAGE_GAS_LIMIT = 1_200_000
ADI_FORUM_POST_URL = (
    "https://research.lido.fi/t/reconfigure-bsc-governance-forwarding-after-wormhole-auto-delivery-shutdown/11980"
)


# ============================= Description ==================================
IPFS_DESCRIPTION = f"""
1. **Submit a Dual Governance proposal to activate the CSM deployment for 0x02 withdrawal credentials on Ethereum mainnet**, including its Staking Router registration, protocol permissions, oracle schedule, and CircuitBreaker configuration; set the CMv1 stake share limit to 0 to transition to Period 2 of the deposits and consolidations plan; and set the Consensys operator target limits to 0 in both curated modules (soft mode). Items 1.1-1.15.
2. **Remove the Wormhole adapter from a.DI governance forwarding to BNB Chain and lower the BNB Chain quorum from 3 of 4 bridges to 2 of 3**, [as proposed on the forum]({ADI_FORUM_POST_URL}). Wormhole shut down its Standard Relayer on April 1, 2026, so only CCIP, LayerZero, and Hyperlane still deliver Lido DAO messages to BNB Chain. Items 1.16-1.17.
3. **Add the CSM 0x02 Easy Track factories** for reporting slashed withdrawals, settling general delayed penalties, and updating the module share limits. Items 2-4.
"""

DG_PROPOSAL_METADATA = (
    "Activate CSM 0x02, set CMv1 stake share limit to 0, set Consensys target limits to 0 in CMv1 and CMv2, "
    "remove the Wormhole adapter from a.DI forwarding to BNB Chain, and set the BNB Chain quorum to 2 of 3 bridges"
)
DG_SUBMISSION_DESCRIPTION = (
    "1. Submit a Dual Governance proposal to activate CSM 0x02, update curated module limits, "
    "and reconfigure a.DI governance forwarding to BNB Chain"
)


def validate_configuration() -> None:
    unresolved_addresses = [name for name, address in DEPLOYMENT_ADDRESSES.items() if address == TODO_ADDRESS]
    if unresolved_addresses:
        raise ValueError(f"Set deployment addresses before building the vote: {', '.join(unresolved_addresses)}")

    if CSM0X02_ORACLE_INITIAL_EPOCH <= 0:
        raise ValueError("Set CSM0X02_ORACLE_INITIAL_EPOCH before building the vote")


def encode_bnb_actions_set() -> bytes:
    """
    ABI-encode the action set the BNB Chain CrossChainExecutor queues once the a.DI message is confirmed.

    The executor decodes (targets, values, signatures, calldatas, withDelegatecalls) and, for a non-empty
    signature, calls the target with the signature's selector followed by the given calldata.
    """
    bnb_ccc = interface.CrossChainController(ETHEREUM_CROSS_CHAIN_CONTROLLER)  # Same ABI on both chains.

    actions = [
        # Stop accepting Wormhole deliveries from Ethereum on the BNB Chain CrossChainController.
        (
            "disallowReceiverBridgeAdapters((address,uint256[])[])",
            bnb_ccc.disallowReceiverBridgeAdapters.encode_input([(BNB_WORMHOLE_ADAPTER, [ETHEREUM_CHAIN_ID])]),
        ),
        # Require 2 bridge confirmations for messages from Ethereum.
        (
            "updateConfirmations((uint256,uint8)[])",
            bnb_ccc.updateConfirmations.encode_input([(ETHEREUM_CHAIN_ID, BNB_REQUIRED_CONFIRMATIONS)]),
        ),
    ]

    return encode(
        ["address[]", "uint256[]", "string[]", "bytes[]", "bool[]"],
        [
            [BNB_CROSS_CHAIN_CONTROLLER] * len(actions),
            [0] * len(actions),
            [signature for signature, _ in actions],
            [bytes.fromhex(calldata.removeprefix("0x")[8:]) for _, calldata in actions],  # Strip the selector.
            [False] * len(actions),
        ],
    )


def get_dg_items() -> List[Tuple[str, str]]:
    validate_configuration()

    staking_router = interface.StakingRouter(STAKING_ROUTER)
    burner = interface.Burner(BURNER)
    twg = interface.TriggerableWithdrawalsGateway(TRIGGERABLE_WITHDRAWALS_GATEWAY)
    csm = interface.CSModule(CSM0X02)
    hash_consensus = interface.HashConsensus(CSM0X02_HASH_CONSENSUS)
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)
    ethereum_ccc = interface.CrossChainController(ETHEREUM_CROSS_CHAIN_CONTROLLER)

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
        # Forward before disabling the Wormhole adapter: this message still needs 3 of 4 confirmations on BNB Chain,
        # and its Wormhole copy can be redeemed manually if one of the other three bridges fails to deliver it.
        agent_forward(
            [
                (
                    ethereum_ccc.address,
                    ethereum_ccc.forwardMessage.encode_input(
                        BNB_CHAIN_ID, BNB_CROSS_CHAIN_EXECUTOR, BNB_MESSAGE_GAS_LIMIT, encode_bnb_actions_set()
                    ),
                )
            ]
        ),
        agent_forward(
            [
                (
                    ethereum_ccc.address,
                    ethereum_ccc.disableBridgeAdapters.encode_input([(ETHEREUM_WORMHOLE_ADAPTER, [BNB_CHAIN_ID])]),
                )
            ]
        ),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    validate_configuration()

    csm = interface.CSModule(CSM0X02)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    update_staking_module_share_limits_factory = interface.UpdateStakingModuleShareLimits(
        EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY
    )

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
                permissions=(
                    create_permissions(update_staking_module_share_limits_factory, "validateParams")
                    + create_permissions(staking_router, "updateModuleShares")[2:]
                ),
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
