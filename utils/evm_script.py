import logging
import os
from collections import defaultdict
from functools import lru_cache
from typing import List, Union, Optional, Callable

import eth_abi
from brownie.utils import color
from eth_typing.evm import HexAddress
from eth_utils import keccak
from hexbytes import HexBytes
from web3 import Web3

from avotes_parser.core import parse_script, EncodedCall, Call, FuncInput, decode_function_call
from avotes_parser.core.ABI import get_cached_combined

from avotes_parser.core.parsing import ParseStructureError
from avotes_parser.core.ABI.utilities.exceptions import (
    ABILocalNotFound,
    ABIEtherscanStatusCode,
    ABIEtherscanNetworkError,
)

EMPTY_CALLSCRIPT = "0x00000001"
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "TGXU5WGVTVYRDDV2MY71R5JYB7147M13FC")


def create_executor_id(id) -> str:
    return "0x" + str(id).zfill(8)


def strip_byte_prefix(hexstr):
    return hexstr[2:] if hexstr[0:2] == "0x" else hexstr


def encode_call_script(actions, spec_id=1) -> str:
    result = create_executor_id(spec_id)
    for to, calldata in actions:
        addr_bytes = Web3.to_bytes(hexstr=HexAddress(to)).hex()
        calldata_bytes = strip_byte_prefix(calldata)
        length = eth_abi.encode("int256", len(calldata_bytes) // 2).hex()
        result += addr_bytes + length[56:] + calldata_bytes
    return result


@lru_cache
def get_abi_cache(api_key: str, net: str):
    return get_cached_combined(
        api_key,
        net,
        os.getenv("INTERFACES_DIRECTORY", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "interfaces")),
    )


def _is_encoded_script(data: FuncInput) -> bool:
    return data.type == "bytes" and data.name == "_evmScript"


def decode_evm_script(
    script: str,
    verbose: bool = True,
    specific_net: str = "mainnet",
    repeat_is_error: bool = True,
    is_encoded_script: Optional[Callable[[FuncInput], bool]] = None,
) -> List[Union[str, Call, EncodedCall]]:
    """Decode EVM script to human-readable format."""
    if verbose:
        # Switch-on debug messages from evmscript-parser package.
        logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

    if is_encoded_script is None:
        is_encoded_script = _is_encoded_script

    try:
        parsed = parse_script(script)
    except ParseStructureError as err:
        if verbose:
            logging.basicConfig(level=logging.INFO)
        return [repr(err)]

    abi_storage = get_abi_cache(ETHERSCAN_API_KEY, specific_net)

    calls = []
    called_contracts = defaultdict(lambda: defaultdict(dict))
    for ind, call in enumerate(parsed.calls):
        try:
            call_info = decode_function_call(call.address, call.method_id, call.encoded_call_data, abi_storage)

            if call_info is not None:
                for inp in filter(is_encoded_script, call_info.inputs):
                    script = inp.value
                    inp.value = decode_evm_script(
                        script,
                        verbose=verbose,
                        specific_net=specific_net,
                        repeat_is_error=repeat_is_error,
                        is_encoded_script=is_encoded_script,
                    )

        except (ABIEtherscanNetworkError, ABIEtherscanStatusCode, ABILocalNotFound) as err:
            call_info = repr(err)

        contract_calls = called_contracts[call.address][call.method_id]
        if call.encoded_call_data in contract_calls:
            (jnd, prev_call_info) = contract_calls[call.encoded_call_data]
            total = len(parsed.calls)
            message = (
                f"!!! REPEATED SCRIPTS !!!:\n"
                f"Previous is {jnd + 1}/{total}:\n"
                f"{calls_info_pretty_print(prev_call_info)}\n"
                f"-----------------------------------------\n"
                f"Current is {ind + 1}/{total}\n"
                f"{calls_info_pretty_print(call_info)}"
            )

            if repeat_is_error:
                raise RuntimeError(f"\n{message}")

            else:
                print(message)

        if call_info is not None:
            calls.append(call_info)
        else:
            calls.append(call)
        contract_calls[call.encoded_call_data] = (ind, call_info)

    if verbose:
        logging.basicConfig(level=logging.INFO)

    return calls


def calls_info_pretty_print(call: Union[str, Call, EncodedCall]) -> str:
    """Format printing for Call instance."""
    return color.highlight(repr(call))

# DEPRECATED
def encode_error(error: str, values=None) -> str:
    encoded_error = error.split('(')[0] + ': '
    args = ''
    if values is not None:
        args = ', '.join(str(x) for x in values)
        return f"{encoded_error}{args}"
    return encoded_error
