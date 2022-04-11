import time
from brownie.utils import color
from utils.voting import create_vote
from utils.evm_script import encode_call_script
from utils.finance import encode_eth_transfer

from utils.config import (
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


def make_refund_call_script(refund_address, refund_in_wei, finance):
    call_script = [
        encode_eth_transfer(
            recipient=refund_address,
            amount=refund_in_wei,
            reference=f'Cover refund',
            finance=finance
        )
    ]
    return call_script


def start_vote(tx_params, silent=False):
    refund_address = '0xD089cc83f5B803993E266ACEB929e52A993Ca2C8'
    refund_in_wei = 79837990169609360000

    finance = interface.Finance(lido_dao_finance_address)

    if not silent:
        print()
        pp('Using finance contract at address', lido_dao_finance_address)
        pp('Using voting contract at address', lido_dao_voting_address)
        print()

    if not silent:
        print('Cover refund (ETH):')
        pp('{:<30}'.format(refund_address), refund_in_wei / 10 ** 18)
        print()

    call_script = make_refund_call_script(refund_address, refund_in_wei, finance)

    if not silent:
        print('Callscript:')
        for addr, action in call_script:
            pp(addr, action)
        print()

    if not silent:
        print('Does it look good?')
        prompt_bool()

    return create_vote(
        vote_desc=(
            f'Omnibus vote: 1) refund dev team for the cover purchase'
        ),
        evm_script=encode_call_script(call_script),
        tx_params=tx_params
    )


def main():
    (vote_id, _) = start_vote({'from': get_deployer_account()})
    print(f'Vote created: {vote_id}')
    time.sleep(5)  # hack: waiting thread 2
