"""
Vote 2026_05_13.

I. Extend Dual Governance Emergency Protection for one additional year
    1.1. Call setEmergencyProtectionEndDate(1813449600) on Emergency Protected Timelock 0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316

II. Grant MANAGE_SIGNING_KEYS role to Consensys
    1.2. Grant MANAGE_SIGNING_KEYS 75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee role to 0xF45C77EadD434612fCD93db978B3E36B0D58eC99 for Node Operator Consensys (ID = 21)

III. Increase limit from $250K per 3 months to $5M per 6 months on Alliance Ops stablecoins Easy Track factory
    1.3. Set limit to 5,000,000 stETH per 6 months on Alliance Ops stablecoins AllowedRecipientsRegistry 0x3B525F4c059F246Ca4aa995D21087204F30c9E2F

IV. Change number of epochs in VEBO reporting frame
    1.4. Grant MANAGE_FRAME_CONFIG_ROLE 0x921f40f434e049d23969cbe68d9cf3ac1013fbe8945da07963af6f3142de6afe role to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c on the VEBO Hash Consensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
    1.5. Set number of epochs in reporting frame to 45 on the VEBO Hash Consensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
    1.6. Revoke MANAGE_FRAME_CONFIG_ROLE 0x921f40f434e049d23969cbe68d9cf3ac1013fbe8945da07963af6f3142de6afe role from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c on the VEBO Hash Consensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
    1.7. Set time window constraint (13:00 - 16:30 UTC) for Dual Governance Proposal execution on Dual Governance Time Constraints 0x2a30F5aC03187674553024296bed35Aa49749DDa
"""

from brownie import interface
from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from utils.permissions import encode_permission_grant_p
from utils.permission_parameters import Param, Op, ArgumentValue
from utils.allowed_recipients_registry import set_limit_parameters

from utils.agent import agent_forward

# ============================== Addresses ===================================
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
NODE_OPERATORS_REGISTRY = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
ALLIANCE_OPS_STABLECOINS_REGISTRY = "0x3B525F4c059F246Ca4aa995D21087204F30c9E2F"
VEBO_HASH_CONSENSUS = "0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"
DUAL_GOVERNANCE_TIME_CONSTRAINTS = "0x2a30F5aC03187674553024296bed35Aa49749DDa"
ARAGON_AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"


# ============================== Constants ===================================
NEW_EMERGENCY_PROTECTION_END_DATE = 1813449600  # 2027-05-19 00:00:00 UTC

CONSENSYS_NO_ID = 21
CONSENSYS_NEW_MANAGER = "0xF45C77EadD434612fCD93db978B3E36B0D58eC99"

ALLIANCE_OPS_NEW_LIMIT = 5_000_000 * 10**18
ALLIANCE_OPS_NEW_PERIOD_DURATION_MONTHS = 6

VEBO_NEW_EPOCHS_PER_FRAME = 45

# HashConsensus roles
MANAGE_FRAME_CONFIG_ROLE = "0x921f40f434e049d23969cbe68d9cf3ac1013fbe8945da07963af6f3142de6afe"


# ============================= IPFS Description ==================================
# TODO IPFS description text
IPFS_DESCRIPTION = """
"""


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    vebo_hash_consensus = interface.HashConsensus(VEBO_HASH_CONSENSUS)
    time_constraints = interface.TimeConstraints(DUAL_GOVERNANCE_TIME_CONSTRAINTS)

    (_, _, fast_lane_length_slots) = vebo_hash_consensus.getFrameConfig()

    return [
        # 1.1. Call setEmergencyProtectionEndDate(1813449600) on Emergency Protected Timelock 0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316
        (
            timelock.address,
            timelock.setEmergencyProtectionEndDate.encode_input(NEW_EMERGENCY_PROTECTION_END_DATE),
        ),
        # 1.2. Grant MANAGE_SIGNING_KEYS 75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee role to 0xF45C77EadD434612fCD93db978B3E36B0D58eC99 for Node Operator Consensys (ID = 21)
        agent_forward([
            encode_permission_grant_p(
                target_app=NODE_OPERATORS_REGISTRY,
                permission_name="MANAGE_SIGNING_KEYS",
                grant_to=CONSENSYS_NEW_MANAGER,
                params=[Param(0, Op.EQ, ArgumentValue(CONSENSYS_NO_ID))],
            ),
        ]),
        # 1.3. Set limit to 5,000,000 stETH per 6 months on Alliance Ops stablecoins AllowedRecipientsRegistry 0x3B525F4c059F246Ca4aa995D21087204F30c9E2F
        agent_forward([
            set_limit_parameters(
                registry_address=ALLIANCE_OPS_STABLECOINS_REGISTRY,
                limit=ALLIANCE_OPS_NEW_LIMIT,
                period_duration_months=ALLIANCE_OPS_NEW_PERIOD_DURATION_MONTHS,
            ),
        ]),
        agent_forward([
            # 1.4. Grant MANAGE_FRAME_CONFIG_ROLE 0x921f40f434e049d23969cbe68d9cf3ac1013fbe8945da07963af6f3142de6afe role to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c on the VEBO Hash Consensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
            (
                vebo_hash_consensus.address,
                vebo_hash_consensus.grantRole.encode_input(MANAGE_FRAME_CONFIG_ROLE, ARAGON_AGENT),
            ),
            # 1.5. Set number of epochs in reporting frame to 45 on the VEBO Hash Consensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
            (
                vebo_hash_consensus.address,
                vebo_hash_consensus.setFrameConfig.encode_input(VEBO_NEW_EPOCHS_PER_FRAME, fast_lane_length_slots),
            ),
            # 1.6. Revoke MANAGE_FRAME_CONFIG_ROLE 0x921f40f434e049d23969cbe68d9cf3ac1013fbe8945da07963af6f3142de6afe role from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c on the VEBO Hash Consensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a
            (
                vebo_hash_consensus.address,
                vebo_hash_consensus.revokeRole.encode_input(MANAGE_FRAME_CONFIG_ROLE, ARAGON_AGENT),
            ),
            # 1.7. Set time window constraint (13:00 - 16:30 UTC) for Dual Governance Proposal execution on Dual Governance Time Constraints 0x2a30F5aC03187674553024296bed35Aa49749DDa
            (
                time_constraints.address,
                time_constraints.checkTimeWithinDayTimeAndEmit.encode_input(13 * 3600, 16.5 * 3600),
            ),
        ]),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    dg_items = get_dg_items()

    dg_call_script = submit_proposals([
        (
            dg_items,
            "Extend DG Emergency Protection by one year, "
            "grant MANAGE_SIGNING_KEYS for Consensys (NO ID = 21), "
            "raise Alliance Ops stablecoins Easy Track limit to 5M stETH / 6 months, "
            "change number of epochs in VEBO reporting frame to 45, and "
            "set time window constraint (13:00 - 16:30 UTC) for DG Proposal execution",
        )
    ])

    vote_desc_items, call_script_items = zip(
        (
            "1. Submit a Dual Governance proposal to extend DG Emergency Protection by one year, "
            "grant MANAGE_SIGNING_KEYS for Consensys (NO ID = 21), "
            "raise Alliance Ops stablecoins Easy Track limit to 5M stETH / 6 months, "
            "change number of epochs in VEBO reporting frame to 45, and "
            "set time window constraint (13:00 - 16:30 UTC) for DG Proposal execution",
            dg_call_script[0]
        ),
    )

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
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
