"""
Release part of the update before the Pectra upgrade

1. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle 0x852deD011285fe67063a08005c71a85690503Cee to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
2. Update Accounting Oracle 0x852deD011285fe67063a08005c71a85690503Cee consensus version to 3
3. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle 0x852deD011285fe67063a08005c71a85690503Cee from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
4. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6 to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
5. Update Validator Exit Bus Oracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e consensus version to 3
6. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
7. Grant MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
8. Update CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB consensus version to 2
9. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
10. Revoke VERIFIER_ROLE role on CSM 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F from old CS Verifier 0x3Dfc50f22aCA652a0a6F28a0F892ab62074b5583
11. Grant VERIFIER_ROLE role on CSM 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F to new CS Verifier 0x0c345dFa318f9F4977cdd4f33d80F9D0ffA38e8B
"""

import time

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
            "1. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle 0x852deD011285fe67063a08005c71a85690503Cee to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c",
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
            "2. Update Accounting Oracle 0x852deD011285fe67063a08005c71a85690503Cee consensus version to 3",
            agent_forward([encode_ao_set_consensus_version()]),
        ),
        (
            "3. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Accounting Oracle 0x852deD011285fe67063a08005c71a85690503Cee from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c",
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
            "4. Grant MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6 to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c",
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
            "5. Update Validator Exit Bus Oracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e consensus version to 3",
            agent_forward([encode_vebo_set_consensus_version()]),
        ),
        (
            "6. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on Validator Exit Bus Oracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c",
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
            "7. Grant MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c",
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
            "8. Update CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB consensus version to 2",
            agent_forward([encode_cs_fee_oracle_set_consensus_version()]),
        ),
        (
            "9. Revoke MANAGE_CONSENSUS_VERSION_ROLE role on CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c",
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
            "10. Revoke VERIFIER_ROLE role on CSM 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F from old CS Verifier 0x3Dfc50f22aCA652a0a6F28a0F892ab62074b5583",
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
            "11. Grant VERIFIER_ROLE role on CSM 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F to new CS Verifier 0x0c345dFa318f9F4977cdd4f33d80F9D0ffA38e8B",
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
