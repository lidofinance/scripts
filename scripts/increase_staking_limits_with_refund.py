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
from utils.node_operators import encode_set_node_operator_staking_limit, get_node_operators
from utils.finance import encode_eth_transfer

from utils.config import (
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    curve_rewards_manager_address,
    get_deployer_account,
    prompt_bool
)


def pp(text, value):
    print(text, color.highlight(str(value)), end='')


def make_staking_limits_call_script(new_staking_limits, node_operators, registry):
    call_script = []
    for op in node_operators:
        if op['name'] in new_staking_limits:
            op_id = op['index']
            op_limit = new_staking_limits[op['name']]
            call_script.append(
                encode_set_node_operator_staking_limit(
                    id=op_id,
                    limit=op_limit,
                    registry=registry
                ),
            )

    assert len(new_staking_limits) == len(call_script) # defensive programming
    return call_script


def make_refunds_call_script(refunds_in_wei, node_operators, finance):
    call_script = []
    for op in node_operators:
        if op['name'] in refunds_in_wei:
            op_address = op['rewardAddress']
            op_refund = refunds_in_wei[op['name']]
            call_script.append(
                encode_eth_transfer(
                    recipient=op_address,
                    amount=op_refund,
                    reference=f'Gas refund',
                    finance=finance
                )
            )

    assert len(refunds_in_wei) == len(call_script) # defensive programming
    return call_script


def start_vote(tx_params):
    new_staking_limits = {
        'Staking Facilities': 4000,
        'Certus One': 4000,
        'P2P.ORG - P2P Validator': 4000,
        'Chorus One': 4000,
        'stakefish': 4000,
        'Blockscape': 4000,
        'DSRV': 4000,
        'Everstake': 4000,
        'SkillZ': 4000
    }

    refunds_in_wei = {
        'P2P.ORG - P2P Validator': 2371905796000000000,
        'Chorus One': 5119081503890094218,
        'Blockscape': 1216139293000000000,
        'DSRV': 2515620639800000000
    }

    finance = interface.Finance(lido_dao_finance_address)
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)

    print()
    pp('Using finance contract at address', lido_dao_finance_address)
    pp('Using NodeOperatorsRegistry at address', lido_dao_node_operators_registry)
    pp('Using voting contract at address', lido_dao_voting_address)
    print()

    print('Node Operators new staking limits:')
    for op_name, limit in new_staking_limits.items():
        pp('{:<30}'.format(op_name), limit)
    print()

    print('Node Operators refunds (ETH):')
    for op_name, refund in refunds_in_wei.items():
        pp('{:<30}'.format(op_name), refund / 10 ** 18)
    print()

    node_operators = get_node_operators(registry)

    staking_limits_script = make_staking_limits_call_script(new_staking_limits, node_operators, registry)
    refunds_script = make_refunds_call_script(refunds_in_wei, node_operators, finance)

    call_script = staking_limits_script + refunds_script

    print('Callscript:')
    for addr, action in call_script:
        pp(addr, action)
    print()

    print('Does it look good?')
    prompt_bool()

    return create_vote(
        voting=interface.Voting(lido_dao_voting_address),
        token_manager=interface.TokenManager(lido_dao_token_manager_address),
        vote_desc=(
            f'Omnibus vote: 1) increase staking limits for Node Operators, '
            f'2) refund gas spendings after withdrawal credentials change'
        ),
        evm_script=encode_call_script(call_script),
        tx_params=tx_params
    )


def main():
    (vote_id, _) = start_vote({'from': get_deployer_account()})
    print(f'Vote created: {vote_id}')
    time.sleep(5) # hack: waiting thread 2
