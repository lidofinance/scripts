"""
    Triggerable withdrawals voting baking and sending.

    Contains next steps:
        1. Update VEBO implementation
        # 2. Call finalize upgrade on VEBO  # TODO
        3. Update VEBO consensus version to `4`
        4. Update WithdrawalVault implementation
        # 5. Call finalize upgrade on WV  # TODO
        6. Grant ADD_FULL_WITHDRAWAL_REQUEST_ROLE to the VEBO in WithdrawalVault
        7. Update AO consensus version to `4`
"""

from scripts.triggerable_withdrawals.vote_body import create_tw_vote
from utils.config import get_deployer_account, get_priority_fee


def main():
    print('Start baking vote.')

    tx_params = {
        "from": get_deployer_account(),
        "priority_fee": get_priority_fee(),
    }

    vote_id, _ = create_tw_vote(tx_params=tx_params, silent=True)

    if vote_id:
        print(f'Vote [{vote_id}] created.')

