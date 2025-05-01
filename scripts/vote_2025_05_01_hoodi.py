"""
Voting 01/05/2025. Hoodi network.

I. Deploy sandbox EVM script factories for EasyTrack:

1. Add `RemoveAllowedRecipients` EVM script factory 
2. Add `AddAllowedRecipient` EVM script factory
3. Add `TopUpAllowedRecipient` EVM script factory
4. Add `CREATE_PAYMENTS_ROLE` permission to EasyTrackEVMScriptExecutor
"""

import time
from typing import Dict
from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.permissions import encode_permission_grant

from utils.agent import agent_forward
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.config import (
    contracts,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
)

DESCRIPTION = """
Voting 01/05/2025. Hoodi network.

I. Deploy sandbox EVM script factories for EasyTrack:

1. Add `RemoveAllowedRecipients` EVM script factory 
2. Add `AddAllowedRecipient` EVM script factory
3. Add `TopUpAllowedRecipient` EVM script factory
4. Add `CREATE_PAYMENTS_ROLE` permission to EasyTrackEVMScriptExecutor
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting"""

    # 1. Add `RemoveAllowedRecipients` EVM script factory (sandbox)
    remove_allowed_recipient = "0xc84251D2959E976AfE95201E1e2B88dB56Bc0a69"
    # 2. Add `AddAllowedRecipient` EVM script factory (sandbox)
    add_allowed_recipient = "0x056561d0F1314CB3932180b3f0B3C03174F2642B"
    # 3. Add `TopUpAllowedRecipient` EVM script factory (sandbox)
    top_up_allowed_recipients = "0x8D9Fd9cD208f57c6735174B848180B53A0F7F560"

    allowed_recipient_registry = interface.AllowedRecipientRegistry("0xd57FF1ce54F572F4E8DaF0cB7038F1Bd6049cAa8")

    vote_desc_items, call_script_items = zip(
        (
            "1) Add `RemoveAllowedRecipients` EVM script factory with address 0xc84251D2959E976AfE95201E1e2B88dB56Bc0a69",
            add_evmscript_factory(
                factory=remove_allowed_recipient,
                permissions=create_permissions(allowed_recipient_registry, "removeRecipient"),
            ),
        ),
        (
            "2) Add `AddAllowedRecipient` EVM script factory with address 0x056561d0F1314CB3932180b3f0B3C03174F2642B",
            add_evmscript_factory(
                factory=add_allowed_recipient,
                permissions=create_permissions(allowed_recipient_registry, "addRecipient"),
            ),
        ),
        (
            "3) Add `TopUpAllowedRecipient` EVM script factory with address 0x8D9Fd9cD208f57c6735174B848180B53A0F7F560",
            add_evmscript_factory(
                factory=top_up_allowed_recipients,
                permissions=create_permissions(contracts.finance, "newImmediatePayment")
                + create_permissions(allowed_recipient_registry, "updateSpentAmount")[2:],
            ),
        ),
        (
            "4) Add CREATE_PAYMENTS_ROLE permission to EasyTrackEVMScriptExecutor",
            encode_permission_grant(
                target_app=contracts.finance,
                permission_name="CREATE_PAYMENTS_ROLE",
                grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
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
