try:
    from brownie import interface
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")

def set_console_globals(**kwargs):
    global interface
    interface = kwargs['interface']

from utils.voting import create_vote
from utils.evm_script import encode_call_script
from utils.node_operators import encode_set_node_operator_staking_limit
from utils.finance import encode_token_transfer

from utils.config import (
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    curve_rewards_manager_address,
    get_deployer_account
)


def start_omnibus_vote(tx_params):
    finance = interface.Finance(lido_dao_finance_address)
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)
    evm_script = encode_call_script([
        encode_set_node_operator_staking_limit(id=5, limit=1000, registry=registry),
        encode_token_transfer(
            token_address=ldo_token_address,
            recipient=curve_rewards_manager_address,
            amount=(3_750_000 * 10**18),
            reference=f'Curve pool LP rewards: transfer to rewards distributor contract',
            finance=finance
        )
    ])
    return create_vote(
        voting=interface.Voting(lido_dao_voting_address),
        token_manager=interface.TokenManager(lido_dao_token_manager_address),
        vote_desc=(
            f'Omnibus vote: 1) set staking limit for Blockscape to 1000, '
            f'2) reseed Curve LP rewards manager contract with 3,750,000 LDO'
        ),
        evm_script=evm_script,
        tx_params=tx_params
    )

def main():
    (vote_id, _) = start_omnibus_vote({'from': get_deployer_account()})
    print(f'Vote created: {vote_id}')
    time.sleep(5) # hack: waiting thread 2
