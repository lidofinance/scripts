import logging
import os
from collections import defaultdict
from functools import lru_cache
from typing import List, Union, Optional, Callable, Any

import eth_abi
from brownie import Contract, convert
from brownie.utils import color
from eth_typing.evm import HexAddress
from web3 import Web3

# NOTE: The decode_function_call() method is currently unused; it is retained for fallback to the previous decoder version
# (refer to the NOTEs in the decode_evm_script method).
from avotes_parser.core import parse_script, EncodedCall, Call, FuncInput, decode_function_call
from avotes_parser.core.ABI import get_cached_combined

from avotes_parser.core.parsing import ParseStructureError
from avotes_parser.core.ABI.utilities.exceptions import (
    ABILocalNotFound,
    ABIEtherscanStatusCode,
    ABIEtherscanNetworkError,
)

EMPTY_CALLSCRIPT = "0x00000001"
ETHERSCAN_TOKEN = os.getenv("ETHERSCAN_TOKEN", "TGXU5WGVTVYRDDV2MY71R5JYB7147M13FC")


def create_executor_id(id) -> str:
    return "0x" + str(id).zfill(8)


def strip_byte_prefix(hexstr):
    return hexstr[2:] if hexstr[0:2] == "0x" else hexstr


def encode_call_script(actions, spec_id=1) -> str:
    result = create_executor_id(spec_id)
    for to, calldata in actions:
        addr_bytes = Web3.to_bytes(hexstr=HexAddress(to)).hex()
        calldata_bytes = strip_byte_prefix(calldata)
        length = eth_abi.encode(["int256"], [len(calldata_bytes) // 2]).hex()
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
    """Decode EVM script to human-readable format with automatic DG nested call detection."""
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

    # NOTE: The line below is not used in the current version; it is retained for fallback to the previous decoder version (see NOTE below).
    abi_storage = get_abi_cache(ETHERSCAN_TOKEN, specific_net)

    calls = []
    called_contracts = defaultdict(lambda: defaultdict(dict))
    for ind, call in enumerate(parsed.calls):
        try:
            call_info = decode_encoded_call(call)

            # NOTE: If the decode_encoded_call(call) method fails, uncomment the line below to fall back to the previous version:
            #
            # call_info = decode_function_call(call.address, call.method_id, call.encoded_call_data, abi_storage)

            if call_info is not None:
                # Handle standard nested _evmScript parameters
                for inp in filter(is_encoded_script, call_info.inputs):
                    script = inp.value
                    inp.value = decode_evm_script(
                        script,
                        verbose=verbose,
                        specific_net=specific_net,
                        repeat_is_error=repeat_is_error,
                        is_encoded_script=is_encoded_script,
                    )

                # Check for DG submitProposal calls and extract nested Agent scripts
                if (hasattr(call_info, 'function_name') and call_info.function_name == "submitProposal" and
                    hasattr(call_info, 'inputs') and len(call_info.inputs) >= 1):

                    try:
                        calls_input = call_info.inputs[0]

                        if calls_input.name == "calls" and (calls_input.type.startswith("tuple[]") or calls_input.type.startswith("struct")):
                            calls_data = calls_input.value
                            if len(calls_data) > 0:
                                first_call = calls_data[0]
                                if len(first_call) >= 3:
                                    nested_script_data = first_call[2]  # The calldata

                                    # Convert to hex string if it's bytes
                                    if isinstance(nested_script_data, bytes):
                                        nested_script_hex = "0x" + nested_script_data.hex()
                                    else:
                                        nested_script_hex = nested_script_data

                                    # Check if this looks like an Agent forward call
                                    if nested_script_hex.startswith("0xd948d468"):  # Agent.forward signature
                                        try:
                                            from eth_abi import decode
                                            # Agent.forward takes (bytes _evmScript)
                                            if isinstance(nested_script_data, bytes):
                                                # Skip the first 4 bytes (function selector)
                                                decoded_params = decode(['bytes'], nested_script_data[4:])
                                            else:
                                                # Skip 0x + 4 bytes (8 hex chars for function selector)
                                                decoded_params = decode(['bytes'], bytes.fromhex(nested_script_hex[10:]))

                                            nested_script = decoded_params[0].hex()

                                            if verbose:
                                                print(f"\n Found nested Agent script in DG proposal:")
                                                print(f"Nested script: 0x{nested_script}")
                                                print(f"Decoding nested calls...\n")

                                            # Recursively decode the nested script
                                            nested_calls = decode_evm_script(
                                                f"0x{nested_script}",
                                                verbose=verbose,
                                                specific_net=specific_net,
                                                repeat_is_error=repeat_is_error,
                                                is_encoded_script=is_encoded_script,
                                            )

                                            # Add nested calls as a custom attribute
                                            call_info.nested_calls = nested_calls

                                        except Exception as e:
                                            if verbose:
                                                print(f"  Failed to decode nested Agent script: {e}")

                    except Exception as e:
                        if verbose:
                            print(f"  Failed to extract nested script from DG proposal: {e}")

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
    result = color.highlight(repr(call))

    # Check if this call has nested calls (from DG script decoding)
    if hasattr(call, 'nested_calls') and call.nested_calls:
        result += f"\n{color('cyan')}Nested calls within this DG proposal:{color()}\n"
        for i, nested_call in enumerate(call.nested_calls):
            result += f"  {i+1}. {color.highlight(repr(nested_call))}\n"

    return result


def encode_error(error: str, values=None) -> str:
    encoded_error = error.split("(")[0] + ": "
    args = ""
    if values is not None:
        args = ", ".join(str(x) for x in values)
        return f"{encoded_error}{args}"
    return encoded_error


def decode_encoded_call(encoded_call: EncodedCall) -> Optional[Call]:
    """
    Decodes an encoded contract call using Brownie's Contract API.

    This function replaces AVotesParser.decode_function_call() and converts the provided
    EncodedCall into a Call object or returns None if the decoding wasn't successfull.
    Unsuccessfull deconding usually happens when the contract is not verified contract on etherscan

    Parameters:
        encoded_call (EncodedCall): An object containing the target contract address, method id,
                                    and encoded call data and encoded call data length.

    Returns:
        Call: A Call object with decoded call details if successful, otherwise None if the method
              call cannot be decoded.
    """
    contract = Contract(encoded_call.address)

    # If the method selector is not found in the locally stored contracts, fetch the full ABI from Etherscan.
    if encoded_call.method_id not in contract.selectors:
        # For proxy contracts, Brownie automatically retrieves the implementation ABI.
        contract = Contract.from_explorer(encoded_call.address)

    # If the method selector is still not found, the call may target the proxy contract directly rather than its implementation.
    if encoded_call.method_id not in contract.selectors:
        # Explicitly fetch the ABI for the proxy contract itself by setting `as_proxy_for` to the proxy's address.
        # NOTE: Normalization via `convert.to_address()` is required; without it, the internal check in `from_explorer()` may fail,
        #   resulting in the implementation's ABI being downloaded instead.
        contract = Contract.from_explorer(encoded_call.address, as_proxy_for=convert.to_address(encoded_call.address))

    # If the method selector is still not found, the contract is likely not verified.
    if encoded_call.method_id not in contract.selectors:
        return None

    method_name = contract.selectors[encoded_call.method_id]
    contract_method = getattr(contract, method_name)

    method_abi = contract_method.abi

    calldata_with_selector = encoded_call.method_id + encoded_call.encoded_call_data[2:]
    decoded_calldata = contract_method.decode_input(calldata_with_selector)

    inputs = [get_func_input(method_abi["inputs"][idx], arg) for idx, arg in enumerate(decoded_calldata)]

    properties = {
        "constant": "unknown",  # Typically False even for pure methods, but not guaranteed.
        "payable": method_abi["stateMutability"] == "payable",
        "stateMutability": method_abi["stateMutability"],
        "type": "function",
    }

    return Call(
        contract.address,
        encoded_call.method_id,
        method_name,
        inputs,
        properties,
        method_abi["outputs"],
    )


def get_func_input(input_abi: dict, value: Any) -> FuncInput:
    return FuncInput(input_abi["name"], input_abi.get("internalType", input_abi.get("type")), value)
