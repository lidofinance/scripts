import time
from brownie.utils import color
from utils.voting import create_vote
from utils.evm_script import encode_call_script
from utils.finance import encode_token_transfer
from utils.node_operators import encode_set_node_operator_staking_limit

from utils.config import (
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_node_operators_registry,
    get_deployer_account,
    prompt_bool
)

try:
    from brownie import interface
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


def set_console_globals(**kwargs):
    global interface
    interface = kwargs['interface']


def pp(text, value):
    print(text, color.highlight(str(value)), end='')


def make_fund_sushi_rewards_call_script(rewards_manager_address, ldo_for_rewards_in_wei, finance):
    return encode_token_transfer(
        token_address=ldo_token_address,
        recipient=rewards_manager_address,
        amount=ldo_for_rewards_in_wei,
        reference=f'Sushi wstETH<>DAI pool LP rewards: transfer to finance ops multisig',
        finance=finance
    )


def start_vote(tx_params, silent=False):
    lido_finance_ops_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    ldo_for_rewards_in_wei = 200_000 * 10 ** 18

    finance = interface.Finance(lido_dao_finance_address)
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)

    if not silent:
        print()
        pp('Using finance contract at address', lido_dao_finance_address)
        pp('Using voting contract at address', lido_dao_voting_address)
        pp('Using node operators registry at address', lido_dao_node_operators_registry)
        print()

    if not silent:
        print('Fund Curve pool rewards (LDO):')
        pp('{:<30}'.format(lido_finance_ops_multisig_address), ldo_for_rewards_in_wei / 10 ** 18)
        print()

    fund_sushi_call_script = make_fund_sushi_rewards_call_script(lido_finance_ops_multisig_address,
                                                                 ldo_for_rewards_in_wei, finance)
    increase_staking_facilities_limit = encode_set_node_operator_staking_limit(id=0, limit=3500, registry=registry)
    increase_dsrv_limit = encode_set_node_operator_staking_limit(id=6, limit=2000, registry=registry)
    increase_everstake_limit = encode_set_node_operator_staking_limit(id=7, limit=2200, registry=registry)
    increase_skillz_limit = encode_set_node_operator_staking_limit(id=8, limit=3001, registry=registry)

    call_script = [fund_sushi_call_script, increase_staking_facilities_limit, increase_dsrv_limit,
                   increase_everstake_limit, increase_skillz_limit]

    if not silent:
        print('Callscriptfunds_in_wei')
        for addr, action in call_script:
            pp(addr, action)
        print()

    if not silent:
        print('Does it look good?')
        prompt_bool()

    return create_vote(
        vote_desc=(
            f'Omnibus vote: 1) fund Sushi LP rewards with 200,000 LDO, '
            f'2) increase Staking Facilities key limit to 3500'
            f'3) increase DSRV key limit to 2000'
            f'4) increase Everstake key limit to 2200'
            f'5) increase SkillZ key limit to 3001'
        ),
        evm_script=encode_call_script(call_script),
        tx_params=tx_params
    )


def main():
    (vote_id, _) = start_vote({'from': get_deployer_account(), 'gas_price': '45 gwei', 'gas_limit': '2000000'})
    print(f'Vote created: {vote_id}')
    time.sleep(5)  # hack: waiting thread 2
