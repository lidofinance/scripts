from utils.evm_script import encode_call_script, EMPTY_CALLSCRIPT
from utils.config import ldo_token_address


def create_vote(voting, token_manager, vote_desc, evm_script, tx_params):
    new_vote_script = encode_call_script([
        (voting.address,
         voting.newVote.encode_input(
             evm_script if evm_script is not None else EMPTY_CALLSCRIPT,
             vote_desc, False, False))
    ])
    tx = token_manager.forward(new_vote_script, tx_params)
    vote_id = tx.events['StartVote']['voteId']
    return (vote_id, tx)