import os
import logging

from typing import List, Union
from collections import defaultdict

import eth_abi
from web3 import Web3
from eth_typing.evm import HexAddress
from brownie.utils import color


def _resolve_parser_dependency() -> None:
    parser_package_name = 'evmscript-parser'

    import importlib.util
    if importlib.util.find_spec('evmscript_parser') is None:
        import sys
        import subprocess

        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '--user',
            parser_package_name
        ])


_resolve_parser_dependency()

from evmscript_parser.core.parse import parse_script  # noqa
from evmscript_parser.core.decode import Call  # noqa
from evmscript_parser.core.decode import decode_function_call  # noqa
from evmscript_parser.core.decode.ABI import ABIProviderEtherscanApi  # noqa
from evmscript_parser.core.exceptions import (
    ParseStructureError,
    ABIEtherscanNetworkError, ABIEtherscanStatusCode  # noqa
)

EMPTY_CALLSCRIPT = '0x00000001'
ETHERSCAN_API_KEY = os.getenv(
    'ETHERSCAN_API_KEY',
    'TGXU5WGVTVYRDDV2MY71R5JYB7147M13FC'
)


def create_executor_id(id):
    return '0x' + str(id).zfill(8)


def strip_byte_prefix(hexstr):
    return hexstr[2:] if hexstr[0:2] == '0x' else hexstr


def encode_call_script(actions, spec_id=1):
    result = create_executor_id(spec_id)
    for to, calldata in actions:
        addr_bytes = Web3.toBytes(hexstr=HexAddress(to)).hex()
        calldata_bytes = strip_byte_prefix(calldata)
        length = eth_abi.encode_single('int256',
                                       len(calldata_bytes) // 2).hex()
        result += addr_bytes + length[56:] + calldata_bytes
    return result


def decode_evm_script(
        script: str, verbose: bool = True,
        specific_net: str = 'mainnet', repeat_is_error: bool = True
) -> List[Union[str, Call]]:
    """Decode EVM script to human-readable format."""
    if verbose:
        # Switch-on debug messages from evmscript-parser package.
        logging.basicConfig(
            format='%(levelname)s:%(message)s',
            level=logging.DEBUG
        )

    try:
        parsed = parse_script(script)
    except ParseStructureError as err:
        if verbose:
            logging.basicConfig(
                level=logging.INFO
            )
        return [repr(err)]

    abi_provider = ABIProviderEtherscanApi(
        ETHERSCAN_API_KEY, specific_net
    )

    calls = []
    called_contracts = defaultdict(lambda: defaultdict(dict))
    for ind, call in enumerate(parsed.calls):
        try:
            call_info = decode_function_call(
                call.address, call.method_id,
                call.encoded_call_data, abi_provider
            )
        except ABIEtherscanNetworkError as err:
            call_info = repr(err)

        except ABIEtherscanStatusCode as err:
            call_info = repr(err)

        contract_calls = called_contracts[call.address][call.method_id]
        if call.encoded_call_data in contract_calls:
            (
                jnd, prev_call_info
            ) = contract_calls[call.encoded_call_data]
            total = len(parsed.calls)
            message = (
                f'!!! REPEATED SCRIPTS !!!:\n'
                f'Previous is {jnd+1}/{total}:\n'
                f'{calls_info_pretty_print(prev_call_info)}\n'
                f'-----------------------------------------\n'
                f'Current is {ind+1}/{total}\n'
                f'{calls_info_pretty_print(call_info)}'
            )

            if repeat_is_error:
                raise RuntimeError(f'\n{message}')

            else:
                print(message)

        calls.append(call_info)
        contract_calls[call.encoded_call_data] = (ind, call_info)

    if verbose:
        logging.basicConfig(
            level=logging.INFO
        )

    return calls


def calls_info_pretty_print(call: Union[str, Call]) -> str:
    """Format printing for Call instance."""
    if isinstance(call, str):
        return f'Decoding failed: {call}'

    else:
        inputs = '\n'.join([
            f'{inp.name}: {inp.type} = {inp.value}'
            for inp in call.inputs
        ])
        return color.highlight(
            f'Contract: {call.contract_address}\n'
            f'Function: {call.function_name}\n'
            f'Inputs:\n'
            f'{inputs}'
        )
