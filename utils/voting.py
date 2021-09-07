from brownie import exceptions

from utils.evm_script import encode_call_script, EMPTY_CALLSCRIPT
from utils.config import ldo_token_address



def create_vote(voting, token_manager, vote_desc, evm_script, tx_params,
                verbose: bool = False):
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
    vote_id = tx.events['StartVote']['voteId']

    if verbose:
        try:
            tx.call_trace()
        except exceptions.RPCRequestError as err:
            print(f'Node should be run with `--http.api=debug` flag for '
                  f'traceback handling.\n'
                  f'Raised exception: {repr(err)}')

    return (vote_id, tx)
