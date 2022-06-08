from typing import Tuple, Optional

from brownie import exceptions, web3, convert
from brownie.utils import color
from brownie.network.transaction import TransactionReceipt
from brownie.network.contract import Contract

from utils.evm_script import (encode_call_script,
                              decode_evm_script,
                              calls_info_pretty_print,
                              EMPTY_CALLSCRIPT)

from utils.config import (prompt_bool, chain_network, contracts, get_config_params)


def create_vote(vote_desc, evm_script, tx_params, verbose: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    voting = contracts.voting
    token_manager = contracts.token_manager

    new_vote_script = encode_call_script([
        (voting.address,
         voting.newVote.encode_input(
             evm_script if evm_script is not None else EMPTY_CALLSCRIPT,
             vote_desc, False, False))
    ])
    tx = token_manager.forward(new_vote_script, tx_params)
    if tx.revert_msg is not None:
        print(tx.traceback)
        return -1, tx

    vote_id = None
    try:
        vote_id = tx.events['StartVote']['voteId']
    except:
        # If we're updating Voting itself there can be problems with parsing events from the log
        try:
            vote_id = find_vote_id_in_raw_logs(tx.logs)
        except Exception as e:
            print(e)
            print(f'Looks like your brownie topics cache is out of date, '
                  f'fetching new abi from etherscan '
                  f'for "{voting.address}" address')
            x = Contract.from_explorer(voting.address)
            print(f'{x} downloaded, exiting... please restart the process again')
            return -1, None

    if verbose:
        try:
            tx.call_trace()
        except exceptions.RPCRequestError as err:
            print(f'Node should be run with `--http.api=debug` flag for '
                  f'traceback handling.\n'
                  f'Raised exception: {repr(err)}')

    return vote_id, tx


def find_vote_id_in_raw_logs(logs) -> int:
    start_vote_signature = web3.keccak(text="StartVote(uint256,address,string)")
    start_vote_logs = list(filter(lambda log: log['topics'][0] == start_vote_signature, logs))

    assert len(start_vote_logs) == 1, "Should be only one StartVote in tx"

    start_vote_log = start_vote_logs[0]

    return convert.to_uint(start_vote_log['topics'][1])


def confirm_vote_script(encoded_call_script: str, silent: bool) -> bool:
    human_readable_script = decode_evm_script(
        encoded_call_script, verbose=False, specific_net=chain_network, repeat_is_error=True
    )

    # Show detailed description of prepared voting.
    if not silent:
        cfg_params = get_config_params()

        config_repr = 'All known addresses extracted from a config file:\n'
        for k, v in cfg_params.items():
            config_repr += f'{k} => {v}\n'
        config_repr = color.highlight(config_repr)
        print(f'{config_repr}')

        print('\nPoints of voting:')
        total = len(human_readable_script)
        for ind, call in enumerate(human_readable_script):
            print(f'Point #{ind + 1}/{total}.')
            print(calls_info_pretty_print(call))
            print('---------------------------')

        print('Does it look good? [yes/no]')
        resume = prompt_bool()
        while resume is None:
            resume = prompt_bool()

        if not resume:
            print('Exit without running.')
            return False

    print(f'{color("yellow")}Voting confirmed, please wait a few seconds ...{color}')
    return True
