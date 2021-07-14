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


def main():
    if get_is_live():
        print('Running on a live network, cannot check allocations reception.')
        print('Run on a mainnet fork to do this.')
        return

    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)
    lido = interface.Lido(lido_dao_steth_address)

    prev_withdrawal_credentials = lido.getWithdrawalCredentials()
    pp('Previous withdrawal credentials', prev_withdrawal_credentials)

    with chain_snapshot():
        current_lido_balance = lido.balance()
        assert current_lido_balance > 32 * 10 ** 18
        ok('Lido has greater than 32 Eth in the buffer')

        lido.depositBufferedEther({'from': accounts[0]})
        lido_balance_after_deposit = lido.balance()

        assert current_lido_balance > lido_balance_after_deposit
        ok('depositBufferedEther call triggers a deposit, lido balance after deposit is less then before')

    with chain_snapshot():
        if 'VOTE_ID' in os.environ:
            vote_id = os.environ['VOTE_ID']
            pass_and_exec_dao_vote(int(vote_id))

        run_checks(registry, lido, prev_withdrawal_credentials)

    print('All good!')


def run_checks(registry, lido, prev_withdrawal_credentials):
    print()

    withdrawal_credentials = lido.getWithdrawalCredentials()
    pp('Current withdrawal credentials', withdrawal_credentials)

    assert withdrawal_credentials != prev_withdrawal_credentials
    ok('Withdrawal crenedtials has been changed')

    withdrawal_contract_address = extract_address_from_eth1_wc(str(withdrawal_credentials))
    ok('Withdrawal crenedtials are valid')

    withdrawal_contract = interface.WithdrawalContractProxy(withdrawal_contract_address)

    print()
    pp('Withdrawal contract address derived from WC', withdrawal_contract_address)
    pp('Withdrawal contract admin', withdrawal_contract.proxy_getAdmin())

    assert lido_dao_voting_address == withdrawal_contract.proxy_getAdmin()
    ok('Withdrawal contract admin assigned to the voting')

    print()
    print('Node Operators                keys used / staking limit:')
    node_operators = get_node_operators(registry)
    for op in node_operators:
        op_name = op['name']
        op_limit = op['stakingLimit']
        op_used = op['usedSigningKeys']

        assert op_limit <= op_used
        foramtted_op_name = '{:<30}'.format(op_name)
        ok(f'{foramtted_op_name}', f'{op_used} / {op_limit}')

    ok('All Node Operator staking limits are good')
    print()

    current_lido_balance = lido.balance()
    assert current_lido_balance > 32 * 10 ** 18
    ok('Lido has greater than 32 Eth in the buffer')

    lido.depositBufferedEther({'from': accounts[0]})
    lido_balance_after_deposit = lido.balance()

    assert current_lido_balance == lido_balance_after_deposit
    ok('depositBufferedEther call does not trigger a deposit')

