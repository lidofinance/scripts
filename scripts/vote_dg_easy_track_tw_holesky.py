"""
Vote XX/06/2025 [HOLESKY]

1. Grant SUBMIT_REPORT_HASH_ROLE role to the EasyTrack EVM Script Executor
2. Connect TRIGGERABLE_WITHDRAWALS_GATEWAY to Dual Governance tiebreaker
3. Add `SubmitValidatorsExitRequestHashes` (SDVT) EVM script factory to Easy Track
4. Add `SubmitValidatorsExitRequestHashes` (Curated Module) EVM script factory to Easy Track
"""
import time

from typing import Any, Dict
from typing import Tuple, Optional
from utils.config import (
    AGENT,
    contracts,
    get_deployer_account,
    get_priority_fee,
    get_is_live
)
from utils.vote_item_builder import VoteItem, build_executable_vote_items
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.voting import confirm_vote_script, create_vote, bake_vote_items
from utils.permissions import encode_oz_grant_role
from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
)
from typing import Optional, Tuple, Dict
from utils.config import contracts



TRIGGERABLE_WITHDRAWALS_GATEWAY = "0x4FD4113f2B92856B59BC3be77f2943B7F4eaa9a5"

EASYTRACK_EVMSCRIPT_EXECUTOR = "0x2819B65021E13CEEB9AC33E77DB32c7e64e7520D"

EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x4aB23f409F8F6EdeF321C735e941E4670804a1B4"
EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x7A1c5af4625dc1160a7c67d00335B6Ad492bE53f"

DESCRIPTION = "Add Triggerable Withdrawals Gateway to Dual Governance and new Easy Tracks (HOLESKY)"

def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[Any]]:
    voting_unprepared_items = [
        (
            f"Grant SUBMIT_REPORT_HASH_ROLE on Validator Exit Bus Oracle to the EasyTrack EVM Script Executor",
            VoteItem.agent(
                *encode_oz_grant_role(
                    contract=contracts.validators_exit_bus_oracle,
                    role_name="SUBMIT_REPORT_HASH_ROLE",
                    grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
                ),
            ),
        ),
        (
            "Connect TRIGGERABLE_WITHDRAWALS_GATEWAY to Dual Governance tiebreaker",
            VoteItem.admin(
                contracts.dual_governance.address,
                contracts.dual_governance.addTiebreakerSealableWithdrawalBlocker.encode_input(
                    TRIGGERABLE_WITHDRAWALS_GATEWAY
                ),
            )
        ),
        (
            f"Add `SubmitValidatorsExitRequestHashes` (SDVT) EVM script factory with address `{EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY}` to Easy Track `{contracts.easy_track.address}`",
            VoteItem.voting(
                *add_evmscript_factory(
                    factory=EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                    permissions=(create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")),
                )
            )
        ),
        (
            f"Add `SubmitValidatorsExitRequestHashes` (Curated Module) EVM script factory with address `{EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY}` to Easy Track `{contracts.easy_track.address}`",
            VoteItem.voting(
                *add_evmscript_factory(
                    factory=EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                    permissions=(create_permissions(contracts.validators_exit_bus_oracle, "submitExitRequestsHash")),
                )
            )
        )
    ]

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)


    vote_items = build_executable_vote_items(voting_unprepared_items)
    assert confirm_vote_script(vote_items, silent, desc_ipfs)

    return create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)



def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
