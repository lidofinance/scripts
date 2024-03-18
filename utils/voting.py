from typing import Tuple, Optional, Dict, List

from brownie import exceptions, web3, convert
from brownie.utils import color
from brownie.network.transaction import TransactionReceipt
from brownie.network.contract import Contract
from brownie.network.event import _decode_logs

from utils.evm_script import (
    encode_call_script,
    decode_evm_script,
    calls_info_pretty_print,
    EMPTY_CALLSCRIPT,
)

from utils.config import prompt_bool, CHAIN_NETWORK_NAME, contracts
from utils.ipfs import make_lido_vote_cid, get_url_by_cid, IPFSUploadResult


def bake_vote_items(vote_desc_items: List[str], call_script_items: List[Tuple[str, str]]) -> Dict[str, Tuple[str, str]]:
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
    verbose: bool = False,
    cast_vote: bool = False,
    executes_if_decided: bool = False,
    desc_ipfs: IPFSUploadResult = None,
) -> Tuple[int, Optional[TransactionReceipt]]:
    vote_desc_str = ""
    for v in vote_items.keys():
        vote_desc_str += f"{v};\n "
    if len(vote_desc_str) > 0:
        vote_desc_str = f"Omnibus vote: {vote_desc_str[:-3]}."

    if desc_ipfs:
        lido_vote_cid = make_lido_vote_cid(desc_ipfs["cid"])
        vote_desc_str = f"{vote_desc_str}\n{lido_vote_cid}"

    voting = contracts.voting
    token_manager = contracts.token_manager

    evm_script = encode_call_script(vote_items.values())

    new_vote_script = encode_call_script(
        [
            (
                voting.address,
                voting.newVote.encode_input(
                    evm_script if evm_script is not None else EMPTY_CALLSCRIPT,
                    vote_desc_str,
                    cast_vote,
                    executes_if_decided,
                ),
            )
        ]
    )
    tx = token_manager.forward(new_vote_script, tx_params)
    if tx.revert_msg is not None:
        print(tx.traceback)
        return -1, tx

    vote_id = None
    try:
        vote_id = tx.events["StartVote"]["voteId"]
    except:
        # If we're updating Voting itself there can be problems with parsing events from the log
        try:
            vote_id = find_vote_id_in_raw_logs(tx.logs)
        except Exception as e:
            print(e)
            print(
                f"Looks like your brownie topics cache is out of date, "
                f"fetching new abi from etherscan "
                f'for "{voting.address}" address'
            )
            x = Contract.from_explorer(voting.address)
            print(f"{x} downloaded, exiting... please restart the process again")
            return -1, None

    if verbose:
        try:
            tx.call_trace()
        except exceptions.RPCRequestError as err:
            print(
                f"Node should be run with `--http.api=debug` flag for "
                f"traceback handling.\n"
                f"Raised exception: {repr(err)}"
            )

    return vote_id, tx


def find_vote_id_in_raw_logs(logs) -> int:
    start_vote_signature = web3.keccak(text="StartVote(uint256,address,string)")
    start_vote_logs = list(filter(lambda log: log["topics"][0] == start_vote_signature, logs))

    assert len(start_vote_logs) == 1, "Should be only one StartVote in tx"

    start_vote_log = start_vote_logs[0]

    return convert.to_uint(start_vote_log["topics"][1])


def find_metadata_by_vote_id(vote_id: int) -> str:
    vote = contracts.voting.getVote(vote_id)
    if not vote:
        return None

    start_vote_signature = web3.keccak(text="StartVote(uint256,address,string)").hex()

    events_after_voting = web3.eth.filter(
        {
            "address": contracts.voting.address,
            "fromBlock": vote[3],
            "toBlock": vote[3] + 1,
            "topics": [start_vote_signature],
        }
    ).get_all_entries()

    events_after_voting = _decode_logs(events_after_voting)
    return str(events_after_voting["StartVote"]["metadata"])


def _print_points(human_readable_script, vote_descriptions, cid: str) -> bool:
    print("\nPoints of voting:")
    total = len(human_readable_script)
    for ind, call in enumerate(human_readable_script):
        print(f"Point #{ind + 1}/{total}.")
        print(f'Description: {color("green")}{vote_descriptions[ind]}.{color}')
        print(calls_info_pretty_print(call))
        print("---------------------------")
    if cid:
        print(f"Description cid: {color('green')}{make_lido_vote_cid(cid)}{color}")
        print(f"Description preview url: {color('cyan')}{get_url_by_cid(cid)}{color}")

    print("Does it look good? [yes/no]")
    resume = prompt_bool()
    while resume is None:
        resume = prompt_bool()

    if not resume:
        print("Exit without running.")
        return False

    return True


def _print_messages(messages: list[Tuple[str, str]], level: str) -> bool:
    if not messages:
        return True

    filtered = list(filter(lambda item: item[0] == level, messages))
    if not filtered or not len(filtered):
        return True

    color_value = "red" if level == "error" else "yellow"
    print(f"\n{color(color_value)}You have some {level}{color}:")
    for ind, call in enumerate(filtered):
        (_, message) = filtered[ind]
        print(f"{color(color_value)}- {message}{color}")
        print("---------------------------")
    print("Do you want to continue? [yes/no]")
    resume = prompt_bool()
    while resume is None:
        resume = prompt_bool()

    if not resume:
        print("Exit without running.")
        return False

    return True


def confirm_vote_script(
    vote_items: Dict[str, Tuple[str, str]],
    silent: bool,
    desc_ipfs: IPFSUploadResult = None,
) -> bool:
    encoded_call_script = encode_call_script(vote_items.values())

    # Show detailed description of prepared voting.
    if not silent:
        # human_readable_script = decode_evm_script(
        #    encoded_call_script,
        #    verbose=False,
        #    specific_net=CHAIN_NETWORK_NAME,
        #    repeat_is_error=True,
        # )
        human_readable_script = ""

        vote_descriptions = list(vote_items.keys())

        if desc_ipfs:
            cid = desc_ipfs["cid"]
            messages = desc_ipfs["messages"]
        else:
            cid = ""
            messages = [
                (
                    "error",
                    (
                        "You didn't provide an extended description. "
                        "The vote UI allows you to store an extended description in IPFS network. "
                        "Only hash sum will be added to the vote metadata. "
                        "The description is supports a Markdown styles in vote UI. "
                        "You could read more in utils/README.md#ipfs. "
                        "You could use function 'upload_vote_description_to_ipfs' from 'utils.ipfs' to upload text. "
                        "Then provide the result to 'create_vote' and 'confirm_vote_script' into desc_ipfs argument."
                    ),
                )
            ]

        agree = _print_points(human_readable_script, vote_descriptions, cid)
        if not agree:
            return False

        agree = _print_messages(messages, "error")
        if not agree:
            return False

        agree = _print_messages(messages, "warning")
        if not agree:
            return False

    print(f'{color("yellow")}Voting confirmed, please wait a few seconds ...{color}')
    return True
