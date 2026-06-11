"""
Vote [HOODI] - update CSM and Curated module implementations.
"""

from typing import Dict, List, Tuple

from brownie import interface

from utils.agent import agent_forward
from utils.config import (
    CSM_ADDRESS,
    CS_ACCOUNTING_ADDRESS,
    CS_STRIKES_ADDRESS,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.dual_governance import submit_proposals
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.voting import bake_vote_items, confirm_vote_script, create_vote


CURATED_MODULE_ADDRESS = "0x87EB69Ae51317405FD285efD2326a4a11f6173b9"
CURATED_META_REGISTRY_ADDRESS = "0x857289cCBFBc4C134Cc312022a104CD9b38d8AAE"

CSM_ACCOUNTING_IMPL = "0x7E54Ff8aa8f5B61a471447b152Ad34BC7F54f4E6"
CSM_IMPL = "0xB48d144A1c7aB43FDb0ac7582C65728E94e1Df0c"
CSM_VALIDATOR_STRIKES_IMPL = "0x55D2206a4f7e81c170D3f5b7aFbD46B9f75Bc54d"

CURATED_ACCOUNTING_IMPL = "0x7c3733Bd2c3D70b017F6215A232b17a115466536"
CURATED_MODULE_IMPL = "0xf01b6b3E27fD3A4c063E391A0714c770d9422CE8"
CURATED_META_REGISTRY_IMPL = "0x55C22866805080b12A9876e9892180f1F66a5d6B"
CURATED_VALIDATOR_STRIKES_IMPL = "0xc6215d060F26e1F6F34d53d09C626e46bf4a46A3"

DG_PROPOSAL_DESCRIPTION = "Hoodi CSM and Curated module implementations update"

IPFS_DESCRIPTION = """
# Hoodi CSM and Curated module implementations update

1. Update Community Staking Module Accounting implementation.
2. Update Community Staking Module implementation.
3. Update Community Staking Module ValidatorStrikes implementation.
4. Update Curated Module Accounting implementation.
5. Update Curated Module implementation.
6. Update Curated Module MetaRegistry implementation.
7. Update Curated Module ValidatorStrikes implementation.
"""


def _encode_proxy_upgrade_to(
    proxy_address: str, implementation: str
) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy_address)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def _curated_module() -> interface.CSModule:
    return interface.CSModule(CURATED_MODULE_ADDRESS)


def _get_curated_accounting_address() -> str:
    return _curated_module().ACCOUNTING()


def _get_curated_validator_strikes_address() -> str:
    exit_penalties = interface.CSExitPenalties(_curated_module().EXIT_PENALTIES())
    return exit_penalties.STRIKES()


def get_proxy_upgrades() -> List[Tuple[str, str, str]]:
    return [
        ("CSM Accounting", CS_ACCOUNTING_ADDRESS, CSM_ACCOUNTING_IMPL),
        ("CSM", CSM_ADDRESS, CSM_IMPL),
        ("CSM ValidatorStrikes", CS_STRIKES_ADDRESS, CSM_VALIDATOR_STRIKES_IMPL),
        (
            "Curated Accounting",
            _get_curated_accounting_address(),
            CURATED_ACCOUNTING_IMPL,
        ),
        ("Curated Module", CURATED_MODULE_ADDRESS, CURATED_MODULE_IMPL),
        (
            "Curated MetaRegistry",
            CURATED_META_REGISTRY_ADDRESS,
            CURATED_META_REGISTRY_IMPL,
        ),
        (
            "Curated ValidatorStrikes",
            _get_curated_validator_strikes_address(),
            CURATED_VALIDATOR_STRIKES_IMPL,
        ),
    ]


def get_dg_items() -> List[Tuple[str, str]]:
    return [
        agent_forward(
            [
                _encode_proxy_upgrade_to(proxy, impl)
                for _label, proxy, impl in get_proxy_upgrades()
            ]
        )
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    dg_call_script = submit_proposals([(get_dg_items(), DG_PROPOSAL_DESCRIPTION)])

    vote_desc_items = [
        "1. Submit DG proposal: update CSM and Curated module implementations",
    ]
    call_script_items = [dg_call_script[0]]

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent
        else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
