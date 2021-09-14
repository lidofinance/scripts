import os
import logging

from functools import lru_cache
from collections import defaultdict
from typing import (
    List, Union,
    Optional, Callable
)

import eth_abi
from web3 import Web3
from eth_typing.evm import HexAddress
from brownie.utils import color


def _get_latest_version(package_name: str) -> str:
    import json
    import urllib3

    from distutils import version

    url = f'https://pypi.org/pypi/{package_name}/json'

    versions = list(json.loads(urllib3.PoolManager().request(
        'GET', url
    ).data)['releases'].keys())
    versions.sort(key=version.StrictVersion)

    return versions[-1]


def _resolve_parser_dependency() -> None:
    parser_package_name = 'evmscript-parser'

    import sys
    import subprocess
    import pkg_resources

    from distutils import version

    try:
        installed_version = version.StrictVersion(
            pkg_resources.get_distribution(
                parser_package_name
            ).version
        )
        if os.getenv(
                'UPGRADE-EVMSCRIPT-PARSER',
                1
        ):
            latest_version = _get_latest_version(parser_package_name)
            if latest_version > installed_version:
                try:
                    subprocess.run([
                        sys.executable, '-m', 'pip', 'install',
                        '--upgrade',
                        parser_package_name
                    ], stdout=sys.stdout, check=True, stderr=sys.stderr)
                except subprocess.CalledProcessError:
                    subprocess.run([
                        sys.executable, '-m', 'pip3', 'install',
                        '--upgrade',
                        parser_package_name
                    ], stdout=sys.stdout, check=True, stderr=sys.stderr)

    except pkg_resources.DistributionNotFound:
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', '--user',
                parser_package_name
            ], stdout=sys.stdout, check=True, stderr=sys.stderr)
        except subprocess.CalledProcessError:
            subprocess.run([
                sys.executable, '-m', 'pip3', 'install', '--user',
                parser_package_name
            ], stdout=sys.stdout, check=True, stderr=sys.stderr)


_resolve_parser_dependency()

from evmscript_parser.core.parse import parse_script  # noqa
from evmscript_parser.core.decode import Call, FuncInput  # noqa
from evmscript_parser.core.decode import decode_function_call  # noqa
from evmscript_parser.core.ABI import get_cached_combined  # noqa
from evmscript_parser.core.exceptions import (
    ABILocalFileNotExisted, ParseStructureError,
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


@lru_cache
def get_abi_cache(api_key: str, net: str):
    return get_cached_combined(
        api_key, net, os.getenv(
            'INTERFACES_DIRECTORY',
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..',
                'interfaces'
            )
        )
    )


def _is_decoded_script(data: FuncInput) -> bool:
    return data.type == 'bytes'


def decode_evm_script(
        script: str, verbose: bool = True,
        specific_net: str = 'mainnet', repeat_is_error: bool = True,
        interface: Optional[str] = None,
        is_decoded_script: Optional[Callable[[FuncInput], bool]] = None
) -> List[Union[str, Call]]:
    """Decode EVM script to human-readable format."""
    if verbose:
        # Switch-on debug messages from evmscript-parser package.
        logging.basicConfig(
            format='%(levelname)s:%(message)s',
            level=logging.DEBUG
        )

    if is_decoded_script is None:
        is_decoded_script = _is_decoded_script

    try:
        parsed = parse_script(script)
    except ParseStructureError as err:
        if verbose:
            logging.basicConfig(
                level=logging.INFO
            )
        return [repr(err)]

    abi_storage = get_abi_cache(ETHERSCAN_API_KEY, specific_net)

    calls = []
    called_contracts = defaultdict(lambda: defaultdict(dict))
    for ind, call in enumerate(parsed.calls):
        try:
            call_info = decode_function_call(
                call.address, call.method_id,
                call.encoded_call_data, abi_storage,
                combined_key=True, interface_name=interface
            )

            for inp in filter(is_decoded_script, call_info.inputs):
                script = inp.value.hex()
                inp.value = decode_evm_script(
                    script, verbose=verbose, specific_net=specific_net,
                    repeat_is_error=repeat_is_error, interface=interface,
                    is_decoded_script=is_decoded_script
                )

        except (
                ABIEtherscanNetworkError,
                ABIEtherscanStatusCode,
                ABILocalFileNotExisted
        ) as err:
            call_info = repr(err)

        contract_calls = called_contracts[call.address][call.method_id]
        if call.encoded_call_data in contract_calls:
            (
                jnd, prev_call_info
            ) = contract_calls[call.encoded_call_data]
            total = len(parsed.calls)
            message = (
                f'!!! REPEATED SCRIPTS !!!:\n'
                f'Previous is {jnd + 1}/{total}:\n'
                f'{calls_info_pretty_print(prev_call_info)}\n'
                f'-----------------------------------------\n'
                f'Current is {ind + 1}/{total}\n'
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


def _input_pretty_print(inp: FuncInput, tabs: int) -> str:
    offset: str = ' ' * tabs

    if isinstance(inp.value, list) and isinstance(inp.value[0], Call):
        calls = '\n'.join(
            _calls_info_pretty_print(call, tabs + 3)
            for call in inp.value
        )
        return f'{offset}{inp.name}: {inp.type} = [\n{calls}\n]'

    return f'{offset}{inp.name}: {inp.type} = {inp.value}'


def _calls_info_pretty_print(
        call: Union[str, Call], tabs: int = 0
) -> str:
    if isinstance(call, str):
        return f'Decoding failed: {call}'

    else:
        inputs = '\n'.join([
            _input_pretty_print(inp, tabs)
            for inp in call.inputs
        ])

        offset: str = ' ' * tabs

        return (
            f'{offset}Contract: {call.contract_address}\n'
            f'{offset}Function: {call.function_name}\n'
            f'{offset}Inputs:\n'
            f'{inputs}'
        )


def calls_info_pretty_print(
        call: Union[str, Call]
) -> str:
    """Format printing for Call instance."""
    return color.highlight(_calls_info_pretty_print(call))
