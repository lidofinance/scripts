"""
Voting may slot '25 [HOODI]

I. EasyTrack Factories for Managing MEV-Boost Relay Allowed List

1. Add `AddMEVBoostRelay` EVM script factory with address 0xF02DbeaA1Bbc90226CaB995db4C190DbE25983af
2. Add `RemoveMEVBoostRelay` EVM script factory with address 0x7FCc2901C6C3D62784cB178B14d44445B038f736
3. Add `EditMEVBoostRelay` EVM script factory with address 0x27A99a7104190DdA297B222104A6C70A4Ca5A17e
4. Change manager role on MEV-Boost Relay Allowed List from 0xF865A1d43D36c713B4DA085f32b7d1e9739B9275 to `EasyTrackEVMScriptExecutor` 0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E

II. ... 
"""

import time
from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.agent import dual_governance_agent_forward
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

1. Add `AddMEVBoostRelay` EVM script factory with address 0xF02DbeaA1Bbc90226CaB995db4C190DbE25983af
2. Add `RemoveMEVBoostRelay` EVM script factory with address 0x7FCc2901C6C3D62784cB178B14d44445B038f736
3. Add `EditMEVBoostRelay` EVM script factory with address 0x27A99a7104190DdA297B222104A6C70A4Ca5A17e
4. Change manager role on MEV-Boost Relay Allowed List from 0xF865A1d43D36c713B4DA085f32b7d1e9739B9275 to `EasyTrackEVMScriptExecutor` 0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E

II. ...
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting"""

    vote_desc_items, call_script_items = zip(
        (
            "1) Add `AddMEVBoostRelay` EVM script factory with address 0xF02DbeaA1Bbc90226CaB995db4C190DbE25983af",
            add_evmscript_factory(
                factory=EASYTRACK_MEV_BOOST_ADD_RELAYS_FACTORY,
                permissions=create_permissions(contracts.relay_allowed_list, "add_relay"),
            ),
        ),
        (
            "2) Add `RemoveMEVBoostRelay` EVM script factory with address 0x7FCc2901C6C3D62784cB178B14d44445B038f736",
            add_evmscript_factory(
                factory=EASYTRACK_MEV_BOOST_REMOVE_RELAYS_FACTORY,
                permissions=create_permissions(contracts.relay_allowed_list, "remove_relay"),
            ),
        ),
        (
            "3) Add `EditMEVBoostRelay` EVM script factory with address 0x27A99a7104190DdA297B222104A6C70A4Ca5A17e",
            add_evmscript_factory(
                factory=EASYTRACK_MEV_BOOST_EDIT_RELAYS_FACTORY,
                permissions=create_permissions(contracts.relay_allowed_list, "add_relay")
                + create_permissions(contracts.relay_allowed_list, "remove_relay")[2:],
            ),
        ),
        (
            "4) Change manager role on MEV-Boost Relay Allowed List from 0xF865A1d43D36c713B4DA085f32b7d1e9739B9275 to `EasyTrackEVMScriptExecutor` 0x79a20FD0FA36453B2F45eAbab19bfef43575Ba9E",
            dual_governance_agent_forward(
                [
                    (
                        contracts.relay_allowed_list.address,
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
