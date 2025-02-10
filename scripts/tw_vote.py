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

