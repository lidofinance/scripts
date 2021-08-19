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
from utils.finance import encode_token_transfer
from utils.node_operators import encode_set_node_operator_staking_limit, get_node_operators
from utils.finance import encode_eth_transfer


from utils.config import (
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    get_deployer_account,
    prompt_bool
)


def pp(text, value):
    print(text, color.highlight(str(value)), end='')


def make_fund_deversifi_call_script(lido_finance_ops_multisig_address, ldo_for_deversifi_in_wei, finance):
    return encode_token_transfer(
            token_address=ldo_token_address,
            recipient=lido_finance_ops_multisig_address,
            amount=ldo_for_deversifi_in_wei,
            reference=f'DeversiFi payout: transfer to finance ops multisig',
            finance=finance
    )

def make_fund_curve_rewards_call_script(rewards_manager_address, ldo_for_rewards_in_wei, finance):
    return encode_token_transfer(
            token_address=ldo_token_address,
            recipient=rewards_manager_address,
            amount=ldo_for_rewards_in_wei,
            reference=f'Balancer pool LP rewards: transfer to rewards distributor contract',
            finance=finance
    )


def make_fund_LeXpunK_call_script(lido_LeXpunK_multisig_address, eth_in_wei, finance):
    return encode_eth_transfer(
        recipient=lido_LeXpunK_multisig_address,
        amount=eth_in_wei,
        reference=f'Fund LeXpunK DAO multisig',
        finance=finance
    )


def start_vote(tx_params, silent=False):
    lido_finance_ops_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    ldo_for_deversifi_in_wei = 92055343 * 10**16 # 920,553.43 LDO

    balancer_rewards_manager_address = '0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8'
    ldo_for_rewards_in_wei = 100000*10**18

    LeXpunK_ops_multisig_address = '0x316dAa88D931C7221e2E4039F6B793ba2b724180'
    LeXpunK_eth_in_wei = 333 * 10**18 # 1,000,000 USD (1 ETH = 3003 USD)

    finance = interface.Finance(lido_dao_finance_address)
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)

    node_operators = get_node_operators(registry)

    if not silent:
      print()
      pp('Using finance contract at address', lido_dao_finance_address)
      pp('Using voting contract at address', lido_dao_voting_address)
      pp('Using NodeOperatorsRegistry at address', lido_dao_node_operators_registry)
      pp('Using LDO token at address', ldo_token_address)
      print()

      print('Fund DeversiFi (refferal program) payout (LDO):')
      pp('{:<30}'.format(lido_finance_ops_multisig_address), ldo_for_deversifi_in_wei / 10 ** 18)
      print()

      print('Fund Balancer pool rewards (LDO):')
      pp('{:<30}'.format(balancer_rewards_manager_address), ldo_for_rewards_in_wei / 10 ** 18)
      print()

      print('Fund LeXpunKs (ETH):')
      pp('{:<30}'.format(LeXpunK_ops_multisig_address), LeXpunK_eth_in_wei / 10 ** 18)
      print()

      print('Set node operators limits:')
      pp('{:<30}'.format(node_operators[2]['name']), 3600)
      pp('{:<30}'.format(node_operators[5]['name']), 4500)
      pp('{:<30}'.format(node_operators[8]['name']), 4500)


    fund_referral_call_script = make_fund_deversifi_call_script(
        lido_finance_ops_multisig_address,
        ldo_for_deversifi_in_wei,
        finance
    )

    fund_balancer_rewards_call_script = make_fund_curve_rewards_call_script(
        balancer_rewards_manager_address,
        ldo_for_rewards_in_wei,
        finance
    )

    fund_LeXpunK_call_script = make_fund_LeXpunK_call_script(
        LeXpunK_ops_multisig_address,
        LeXpunK_eth_in_wei,
        finance
    )

    p2p_staking_limit = encode_set_node_operator_staking_limit(
        id=2,
        limit=3600,
        registry=registry
    )

    blockscape_staking_limit = encode_set_node_operator_staking_limit(
        id=5,
        limit=4500,
        registry=registry
    )

    skillz_staking_limit = encode_set_node_operator_staking_limit(
        id=8,
        limit=4500,
        registry=registry
    )

    call_script = [
        fund_balancer_rewards_call_script,
        fund_referral_call_script,
        fund_LeXpunK_call_script,
        p2p_staking_limit,
        blockscape_staking_limit,
        skillz_staking_limit
    ]

    if not silent:
      print('Callscriptfunds_in_wei')
      for addr, action in call_script:
          pp(addr, action)
      print()

      print('Does it look good?')
      prompt_bool()

    return create_vote(
        voting=interface.Voting(lido_dao_voting_address),
        token_manager=interface.TokenManager(lido_dao_token_manager_address),
        vote_desc=(
            f'Omnibus vote: 1) fund DeversiFi (refferal program second period) payout with 920,553.43 LDO, '
            f'2) seed Balancer LP rewards manager contract with 100,000 LDO, '
            f'3) fund LeXpunK DAO with 1,000,000 USD (333 ETH), '
            f'4) increase staking limits for Node Operators'
        ),
        evm_script=encode_call_script(call_script),
        tx_params=tx_params
    )


def main():
    (vote_id, _) = start_vote({'from': get_deployer_account(), 'gas_price': '50 gwei'})
    print(f'Vote created: {vote_id}')
    time.sleep(5) # hack: waiting thread 2
