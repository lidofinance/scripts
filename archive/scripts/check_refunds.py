try:
    from brownie import interface, accounts
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


import os
from utils.mainnet_fork import chain_snapshot, pass_and_exec_dao_vote
from utils.config import get_is_live
from brownie.utils import color
from utils.node_operators import get_node_operators

from utils.config import (
    lido_dao_voting_address,
    lido_dao_node_operators_registry,
    lido_dao_steth_address
)

from utils.withdrawal_credentials import (
    get_eth1_withdrawal_credentials,
    encode_set_withdrawal_credentials,
    colorize_withdrawal_credentials,
    extract_address_from_eth1_wc
)


def pp(text, value):
    print(text, color.highlight(str(value)), end='')


def ok(text, highlighted_text = None):
    hl_color = '\x1b[38;5;141m'
    ok_green = '\033[92m'
    gray_color = '\x1b[0;m'
    end_of_color = '\033[0m'

    result = f'{ok_green}[ok]{end_of_color} {text}'

    if highlighted_text:
        result += f'{hl_color}{highlighted_text}{end_of_color}'

    print(result)


def get_ops_balances(node_operators):
    balances = []
    for op in node_operators:
        op_addr = accounts.at(op['rewardAddress'], force=True)
        balances.append(op_addr.balance())

    return balances


def main():
    if get_is_live():
        print('Running on a live network, cannot check allocations reception.')
        print('Run on a mainnet fork to do this.')
        return

    refunds_in_wei = {
        'P2P.ORG - P2P Validator': 2371905796000000000,
        'Chorus One': 5119081503890094218,
        'Blockscape': 1216139293000000000,
        'DSRV': 2515620639800000000
    }

    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)
    node_operators = get_node_operators(registry)
    lido = interface.Lido(lido_dao_steth_address)

    print('Node Operators refunds (ETH):')
    for op_name, refund in refunds_in_wei.items():
        pp('{:<30}'.format(op_name), refund / 10 ** 18)
    print()

    balances_before = get_ops_balances(node_operators)

    with chain_snapshot():
        if 'VOTE_ID' in os.environ:
            vote_id = os.environ['VOTE_ID']
            pass_and_exec_dao_vote(int(vote_id))

        balances_after = get_ops_balances(node_operators)

        print('Node Operators balances diff (ETH):')
        for i in range(len(node_operators)):
            op = node_operators[i]
            pp('{:<30}'.format(op['name']), (balances_after[i] - balances_before[i]) / 10 ** 18)
        print()

        node_operators = get_node_operators(registry)

        print('Node Operators new staking limits:')
        for i in range(len(node_operators)):
            op = node_operators[i]
            pp('{:<30}'.format(op['name']), op['stakingLimit'])
        print()

        current_lido_balance = lido.balance()
        assert current_lido_balance > 32 * 10 ** 18
        ok('Lido has greater than 32 Eth in the buffer')

        tx = lido.depositBufferedEther({'from': accounts[0]})

        print()
        print(tx.info())
        print()

    print('All good!')
