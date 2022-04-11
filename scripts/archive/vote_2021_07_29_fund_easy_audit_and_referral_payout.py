import time
from brownie.utils import color
from utils.voting import create_vote
from utils.evm_script import encode_call_script
from utils.finance import encode_eth_transfer, encode_token_transfer

from utils.config import (
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
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


def make_fund_audit_call_script(lido_finance_ops_multisig_address, funds_in_wei, finance):
    return encode_eth_transfer(
        recipient=lido_finance_ops_multisig_address,
        amount=funds_in_wei,
        reference=f'Easy tracks audit funding',
        finance=finance
    )


def make_fund_referral_call_script(lido_finance_ops_multisig_address, ldo_for_referrals_in_wei, finance):
    return encode_token_transfer(
        token_address=ldo_token_address,
        recipient=lido_finance_ops_multisig_address,
        amount=ldo_for_referrals_in_wei,
        reference=f'Referral program rewards: transfer to finance ops multisig',
        finance=finance
    )


def start_vote(tx_params, silent=False):
    lido_finance_ops_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    audit_fee_in_wei = 39917465927900000000
    ldo_for_referrals_in_wei = 250_000 * 10 ** 18

    finance = interface.Finance(lido_dao_finance_address)

    if not silent:
        print()
        pp('Using finance contract at address', lido_dao_finance_address)
        pp('Using voting contract at address', lido_dao_voting_address)
        print()

    if not silent:
        print('Fund Easy tracks audit (ETH):')
        pp('{:<30}'.format(lido_finance_ops_multisig_address), audit_fee_in_wei / 10 ** 18)
        print()

    if not silent:
        print('Fund referral program payout (LDO):')
        pp('{:<30}'.format(lido_finance_ops_multisig_address), ldo_for_referrals_in_wei / 10 ** 18)
        print()

    fund_audit_call_script = make_fund_audit_call_script(lido_finance_ops_multisig_address, audit_fee_in_wei, finance)
    fund_referral_call_script = make_fund_referral_call_script(lido_finance_ops_multisig_address,
                                                               ldo_for_referrals_in_wei, finance)

    call_script = [fund_audit_call_script, fund_referral_call_script]

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
            f'Omnibus vote: 1) fund easy tracks audit by Sigma Prime, '
            f'2) fund first referral program payout'
        ),
        evm_script=encode_call_script(call_script),
        tx_params=tx_params
    )


def main():
    (vote_id, _) = start_vote({'from': get_deployer_account()})
    print(f'Vote created: {vote_id}')
    time.sleep(5)  # hack: waiting thread 2
