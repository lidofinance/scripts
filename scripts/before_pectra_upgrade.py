"""
Release part of the update before the Pectra upgrade

1. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle to Aragon Agent
2. Update Accounting Oracle consensus version to 3
3. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle from Aragon Agent
4. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle to Aragon Agent
5. Update Validator Exit Bus Oracle consensus version to 3
6. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle from Aragon Agent
7. Grant MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle to Aragon Agent
8. Update CSFeeOracle consensus version to 2
9. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle from Aragon Agent
10. Revoke VERIFIER_ROLE role on CSM from old CS Verifier
11. Grant VERIFIER_ROLE role on CSM to new CS Verifier
"""

import time

try:
    from brownie import interface, accounts, convert
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")


from typing import Dict, Tuple, Optional
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
    CS_VERIFIER_ADDRESS_OLD,
)
from utils.permissions import (
    encode_oz_grant_role,
    encode_oz_revoke_role,
    encode_permission_grant,
    encode_permission_revoke,
    encode_permission_create,
)
from utils.easy_track import (
    add_evmscript_factory,
)
from utils.allowed_recipients_registry import (
    create_top_up_allowed_recipient_permission,
)
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward
from utils.mainnet_fork import pass_and_exec_dao_vote


# Consensus version

AO_CONSENSUS_VERSION = 3
VEBO_CONSENSUS_VERSION = 3
CS_FEE_ORACLE_CONSENSUS_VERSION = 2

description = """
**Pectra Hardfork Compatibility**
Changes include adjustments to oracle algorithms, Oracle Report Sanity Checker limits, and the CS Verifier.
"""


def encode_ao_set_consensus_version() -> Tuple[str, str]:
    proxy = contracts.accounting_oracle
    return proxy.address, proxy.setConsensusVersion.encode_input(AO_CONSENSUS_VERSION)


def encode_vebo_set_consensus_version() -> Tuple[str, str]:
    proxy = contracts.validators_exit_bus_oracle
    return proxy.address, proxy.setConsensusVersion.encode_input(VEBO_CONSENSUS_VERSION)


def encode_cs_fee_oracle_set_consensus_version() -> Tuple[str, str]:
    proxy = contracts.cs_fee_oracle
    return proxy.address, proxy.setConsensusVersion.encode_input(CS_FEE_ORACLE_CONSENSUS_VERSION)


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        (
            "1. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle to Aragon Agent",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.accounting_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "2. Update Accounting Oracle consensus version to 3",
            agent_forward([encode_ao_set_consensus_version()]),
        ),
        (
            "3. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle from Aragon Agent",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.accounting_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "4. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle to Aragon Agent",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "5. Update Validator Exit Bus Oracle consensus version to 3",
            agent_forward([encode_vebo_set_consensus_version()]),
        ),
        (
            "6. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle from Aragon Agent",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.validators_exit_bus_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "7. Grant MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle to Aragon Agent",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.cs_fee_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "8. Update CSFeeOracle consensus version to 2",
            agent_forward([encode_cs_fee_oracle_set_consensus_version()]),
        ),
        (
            "9. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle from Aragon Agent",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.cs_fee_oracle,
                        role_name="MANAGE_CONSENSUS_VERSION_ROLE",
                        revoke_from=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "10. Revoke VERIFIER_ROLE role on CSM from old CS Verifier",
            agent_forward(
                [
                    encode_oz_revoke_role(
                        contract=contracts.csm,
                        role_name="VERIFIER_ROLE",
                        revoke_from=CS_VERIFIER_ADDRESS_OLD,
                    )
                ]
            ),
        ),
        (
            "11. Grant VERIFIER_ROLE role on CSM to new CS Verifier",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.csm,
                        role_name="VERIFIER_ROLE",
                        grant_to=contracts.cs_verifier,
                    )
                ]
            ),
        ),
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.


def start_and_execute_vote_on_fork():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    time.sleep(5)  # hack for waiting thread #2.

    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id))
