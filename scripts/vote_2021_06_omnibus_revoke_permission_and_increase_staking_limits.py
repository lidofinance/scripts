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
    lido_dao_acl_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    get_deployer_account
)


def start_omnibus_vote(tx_params):
    acl = interface.ACL(lido_dao_acl_address)
    voting = interface.Voting(lido_dao_voting_address)
    finance = interface.Finance(lido_dao_finance_address)
    token_manager = interface.TokenManager(lido_dao_token_manager_address)
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)

    ldo_purchase_executor_address = '0x489F04EEff0ba8441D42736549A1f1d6ccA74775'

    evm_script = encode_call_script([
        encode_permission_revoke(
            target_app=token_manager,
            permission_name='ASSIGN_ROLE',
            revoke_from=ldo_purchase_executor_address,
            acl=acl
        ),
        encode_set_node_operator_staking_limit(id=5, limit=4000, registry=registry),
        encode_set_node_operator_staking_limit(id=7, limit=1000, registry=registry),
        encode_set_node_operator_staking_limit(id=8, limit=1500, registry=registry),
    ])

    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=(
            f'Omnibus vote: 1) revoke ASSIGN_ROLE from ldo-purchase-executor contract, '
            f'2) increase staking limits for node node operators #5,7,8'
        ),
        evm_script=evm_script,
        tx_params=tx_params
    )

def main():
    (vote_id, _) = start_omnibus_vote({'from': get_deployer_account()})
    print(f'Vote created: {vote_id}')
    time.sleep(5) # hack: waiting thread 2
