from typing import Tuple, Optional, List, Dict

from brownie import exceptions
from brownie.utils import color
from brownie.network.transaction import TransactionReceipt
from brownie.network.contract import Contract

from utils.evm_script import (encode_call_script,
                              decode_evm_script,
                              calls_info_pretty_print,
                              EMPTY_CALLSCRIPT)

from utils.config import (prompt_bool, chain_network, contracts, get_config_params)

def bake_vote_items(
    vote_desc_items: List[str],
    call_script_items: List[Tuple[str, str]]
) -> Dict[str, Tuple[str, str]]:
    if not isinstance(call_script_items, list):
        raise TypeError("callscript should be passed as a list of items")
    if not isinstance(vote_desc_items, list):
        raise TypeError("vote description has invalid format")
    if len(vote_desc_items) != len(call_script_items):
        raise ValueError(
            f"vote desc and evm_script inconsistent vote items cnt: {len(vote_desc_items)} vs {len(call_script_items)}"
        )
    if len(vote_desc_items) > len(set(vote_desc_items)):
        raise ValueError("vote desc contains repetitive items")
    return dict(zip(vote_desc_items, call_script_items))

def create_vote(
    vote_items: Dict[str, Tuple[str, str]],
    tx_params: Dict[str, str],
    verbose: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    vote_desc_str = ''
    for v in vote_items.keys():
        vote_desc_str += f'{v}; '
    if len(vote_desc_str) > 0:
        vote_desc_str = f'Omnibus vote: {vote_desc_str[:-2]}.'

    voting = contracts.voting
    token_manager = contracts.token_manager

    evm_script = encode_call_script(vote_items.values())

    new_vote_script = encode_call_script([
        (voting.address,
         voting.newVote.encode_input(
             evm_script if evm_script is not None else EMPTY_CALLSCRIPT,
             vote_desc_str, False, False))
    ])
    tx = token_manager.forward(new_vote_script, tx_params)
    if tx.revert_msg is not None:
        print(tx.traceback)
        return -1, tx

    vote_id = None
    try:
        vote_id = tx.events['StartVote']['voteId']
    except:
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


def confirm_vote_script(vote_items: Dict[str, Tuple[str, str]], silent: bool) -> bool:
    encoded_call_script = encode_call_script(vote_items.values())

    human_readable_script = decode_evm_script(
        encoded_call_script, verbose=False, specific_net=chain_network, repeat_is_error=True
    )

    # Show detailed description of prepared voting.
    if not silent:
        vote_descs = list(vote_items.keys())
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
            print(f'Description: {color("green")}{vote_descs[ind]}.{color}')
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
