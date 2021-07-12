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
from utils.permissions import encode_permission_revoke


from utils.config import (
    lido_dao_voting_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    lido_dao_steth_address,
    get_deployer_account
)


from utils.withdrawal_credentials import (
    get_eth1_withdrawal_credentials,
    encode_set_withdrawal_credentials
)


def set_withdrawal_credentials_vote(tx_params):
    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(lido_dao_token_manager_address)
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)
    lido = interface.Lido(lido_dao_steth_address)

    lido_dao_withdrawal_contract_address = '0xb9d7934878b5fb9610b3fe8a5e441e8fad7e293f'
    withdrawal_contract = interface.WithdrawalContractProxy(lido_dao_withdrawal_contract_address)

    if (withdrawal_contract.proxy_getAdmin() != voting.address):
        raise Exception('withdrawal_contract is not in a valid state')

    new_withdrawal_credentials = get_eth1_withdrawal_credentials(withdrawal_contract.address)

    evm_script = encode_call_script([
        encode_set_withdrawal_credentials(
            withdrawal_credentials=new_withdrawal_credentials,
            lido=lido
        ),
        encode_set_node_operator_staking_limit(id=0, limit=2500, registry=registry),
        encode_set_node_operator_staking_limit(id=1, limit=1000, registry=registry),
        encode_set_node_operator_staking_limit(id=2, limit=3386, registry=registry),
        encode_set_node_operator_staking_limit(id=3, limit=3073, registry=registry),
        encode_set_node_operator_staking_limit(id=4, limit=3000, registry=registry),
        encode_set_node_operator_staking_limit(id=5, limit=3073, registry=registry),
        encode_set_node_operator_staking_limit(id=6, limit=100, registry=registry),
        encode_set_node_operator_staking_limit(id=7, limit=1000, registry=registry),
        encode_set_node_operator_staking_limit(id=9, limit=1500, registry=registry),
    ])

    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=(
            f'1) set withdrawal_credentials to {new_withdrawal_credentials}, '
            f'2) set staking limits for all node operators to the current values'
        ),
        evm_script=evm_script,
        tx_params=tx_params
    )

def main():
    (vote_id, _) = set_withdrawal_credentials_vote({'from': get_deployer_account()})
    print(f'Vote created: {vote_id}')
    time.sleep(5) # hack: waiting thread 2
