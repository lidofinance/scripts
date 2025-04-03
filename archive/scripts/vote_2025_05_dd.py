"""
Voting may slot '25

I. EasyTrack Factories for Managing MEV-Boost Relay Allowed List

1. Add `AddMEVBoostRelay` EVM script factory with address <TODO: address>
2. Add `RemoveMEVBoostRelay` EVM script factory with address <TODO: address>
3. Add `EditMEVBoostRelay` EVM script factory with address <TODO: address>
4. Change manager role on MEV-Boost Relay Allowed List from RMC multisig 0x98be4a407Bff0c125e25fBE9Eb1165504349c37d to `EasyTrackEVMScriptExecutor` 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977

II. ... 
"""

import time
from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
    EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
    EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
)
from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
)

DESCRIPTION = """
Voting may slot '25

I. EasyTrack Factories for Managing MEV-Boost Relay Allowed List

1. Add `AddMEVBoostRelay` EVM script factory with address {EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY}
2. Add `RemoveMEVBoostRelay` EVM script factory with address {EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY}
3. Add `EditMEVBoostRelay` EVM script factory with address {EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY}
4. Change manager role on MEV-Boost Relay Allowed List from RMC multisig 0x98be4a407Bff0c125e25fBE9Eb1165504349c37d to `EasyTrackEVMScriptExecutor` {EASYTRACK_EVMSCRIPT_EXECUTOR}

II. ...
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting"""

    vote_desc_items, call_script_items = zip(
        (
            "1) Add `AddMEVBoostRelay` EVM script factory with address {EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY}",
            add_evmscript_factory(
                factory=EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
                permissions=(create_permissions(contracts.relay_allowed_list, "add_relay"),),
            ),
        ),
        (
            "2) Add `RemoveMEVBoostRelay` EVM script factory with address {EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY}",
            add_evmscript_factory(
                factory=EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
                permissions=(create_permissions(contracts.relay_allowed_list, "remove_relay"),),
            ),
        ),
        (
            "3) Add `EditMEVBoostRelay` EVM script factory with address {EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY}",
            add_evmscript_factory(
                factory=EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
                permissions=(create_permissions(contracts.relay_allowed_list, "edit_relay"),),
            ),
        ),
        (
            "4) Change manager role on MEV-Boost Relay Allowed List from RMC multisig 0x98be4a407Bff0c125e25fBE9Eb1165504349c37d to `EasyTrackEVMScriptExecutor` {EASYTRACK_EVMSCRIPT_EXECUTOR}",
            agent_forward(
                [
                    (
                        contracts.relay_allowed_list,
                        contracts.relay_allowed_list.set_manager.encode_input(EASYTRACK_EVMSCRIPT_EXECUTOR),
                    )
                ]
            ),
        ),
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

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
