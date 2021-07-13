try:
    from brownie import interface
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


def set_console_globals(**kwargs):
    global interface
    interface = kwargs['interface']


import time
from brownie.utils import color
from utils.voting import create_vote
from utils.evm_script import encode_call_script
from utils.node_operators import encode_set_node_operator_staking_limit
from utils.permissions import encode_permission_revoke


from utils.config import (
    lido_dao_voting_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    lido_dao_steth_address,
    get_deployer_account,
    prompt_bool
)


from utils.withdrawal_credentials import (
    get_eth1_withdrawal_credentials,
    encode_set_withdrawal_credentials,
    colorize_withdrawal_credentials
)


def pp(text, value):
    print(text, color.highlight(value), end='')


def fetch_node_operators(registry):
    return [{**registry.getNodeOperator(i, True), **{'index': i}} for i in range(registry.getNodeOperatorsCount())]


def set_withdrawal_credentials_vote(tx_params):
    print('You are about ot launch a vote for withdrawal credentials change...')
    voting = interface.Voting(lido_dao_voting_address)
    token_manager = interface.TokenManager(lido_dao_token_manager_address)
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)
    lido = interface.Lido(lido_dao_steth_address)

    lido_dao_withdrawal_contract_address = '0xb9d7934878b5fb9610b3fe8a5e441e8fad7e293f'
    withdrawal_contract = interface.WithdrawalContractProxy(lido_dao_withdrawal_contract_address)

    node_operators = fetch_node_operators(registry)
    node_operators = list(filter(lambda op: op['stakingLimit'] > op['usedSigningKeys'], node_operators))

    if (withdrawal_contract.proxy_getAdmin() != voting.address):
        raise Exception('withdrawal_contract is not in a valid state')

    new_withdrawal_credentials = get_eth1_withdrawal_credentials(withdrawal_contract.address)

    print()
    pp('Using Lido/stETH contract at address', lido_dao_steth_address)
    pp('Using NodeOperatorsRegistry at address', lido_dao_node_operators_registry)
    pp('Using voting contract at address', voting.address)
    print()
    pp('Using withdrawal contract at address', lido_dao_withdrawal_contract_address)
    pp('Withdrawal contract admin', withdrawal_contract.proxy_getAdmin())

    print()
    print('Node Operators whose staking limits should be reduced:')
    for operator in node_operators:
        index = operator['index']
        name = operator['name']
        used = operator['usedSigningKeys']
        pp('{:<30}'.format(f'#{index} {name}'), str(used))

    print()
    print('New withdrawal credentials', colorize_withdrawal_credentials(new_withdrawal_credentials))

    call_script = []

    call_script.append(
        encode_set_withdrawal_credentials(
            withdrawal_credentials=new_withdrawal_credentials,
            lido=lido
        )
    )

    for operator in node_operators:
        index = operator['index']
        used = operator['usedSigningKeys']

        call_script.append(
            encode_set_node_operator_staking_limit(
                id=index,
                limit=used,
                registry=registry
            )
        )

    print()
    print('Callscript:')

    for addr, action in call_script:
        pp(addr, action)

    print()

    print('Does it look good?')
    prompt_bool()

    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=(
            f'1) set withdrawal_credentials to {new_withdrawal_credentials}, '
            f'2) reduce staking limits for node operators whose has approved keys but not used yet'
        ),
        evm_script=encode_call_script(call_script),
        tx_params=tx_params
    )

def main():
    (vote_id, _) = set_withdrawal_credentials_vote({'from': get_deployer_account()})
    print(f'Vote created: {vote_id}')
    time.sleep(5) # hack: waiting thread 2
