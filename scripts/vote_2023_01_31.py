"""
Voting 31/01/2023.
1. Add Referral program DAI top up EVM script factory 0x009ffa22ce4388d2F5De128Ca8E6fD229A312450 to Easy Track
2. Add Referral program DAI add recipient EVM script factory 0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151 to Easy Track
3. Add Referral program DAI remove recipient EVM script factory 0xd8f9B72Cd97388f23814ECF429cd18815F6352c1 to Easy Track
4. Remove reWARDS top up EVM script factory (old ver) 0x77781A93C4824d2299a38AC8bBB11eb3cd6Bc3B7 from Easy Track
5. Remove reWARDS add recipient EVM script factory (old ver) 0x9D15032b91d01d5c1D940eb919461426AB0dD4e3 from Easy Track
6. Remove reWARDS remove recipient EVM script factory (old ver) 0xc21e5e72Ffc223f02fC410aAedE3084a63963932 from Easy Track

"""

import time

from typing import Dict, Tuple, Optional

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.easy_track import add_evmscript_factory, create_permissions, remove_evmscript_factory

from utils.config import (
    get_deployer_account,
    lido_dao_finance_address,
)


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    finance = interface.Finance(lido_dao_finance_address)

    referral_dai_registry = interface.AllowedRecipientRegistry("0xa295C212B44a48D07746d70d32Aa6Ca9b09Fb846")
    referral_dai_topup_factory = interface.TopUpAllowedRecipients("0x009ffa22ce4388d2F5De128Ca8E6fD229A312450")
    referral_dai_add_recipient_factory = interface.AddAllowedRecipient("0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151")
    referral_dai_remove_recipient_factory = interface.RemoveAllowedRecipient("0xd8f9B72Cd97388f23814ECF429cd18815F6352c1")

    rewards_topup_factory_old = interface.IEVMScriptFactory("0x77781A93C4824d2299a38AC8bBB11eb3cd6Bc3B7")
    rewards_add_factory_old = interface.IEVMScriptFactory("0x9D15032b91d01d5c1D940eb919461426AB0dD4e3")
    rewards_remove_factory_old = interface.IEVMScriptFactory("0xc21e5e72Ffc223f02fC410aAedE3084a63963932")

    call_script_items = [
        # 1. Add Referral program DAI top up EVM script factory 0x009ffa22ce4388d2F5De128Ca8E6fD229A312450 to Easy Track
        add_evmscript_factory(
            factory=referral_dai_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(referral_dai_registry, "updateSpentAmount")[2:],
        ),
        # 2. Add Referral program DAI add recipient EVM script factory 0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151 to Easy Track
        add_evmscript_factory(
            factory=referral_dai_add_recipient_factory,
            permissions=create_permissions(referral_dai_registry, "addRecipient"),
        ),
        # 3. Add Referral program DAI remove recipient EVM script factory 0xd8f9B72Cd97388f23814ECF429cd18815F6352c1 to Easy Track
        add_evmscript_factory(
            factory=referral_dai_remove_recipient_factory,
            permissions=create_permissions(referral_dai_registry, "removeRecipient"),
        ),
        # 4. Remove reWARDS top up EVM script factory (old ver) 0x77781A93C4824d2299a38AC8bBB11eb3cd6Bc3B7 from Easy Track
        remove_evmscript_factory(factory=rewards_topup_factory_old),
        # 5. Remove reWARDS add recipient EVM script factory (old ver) 0x9D15032b91d01d5c1D940eb919461426AB0dD4e3 from Easy Track
        remove_evmscript_factory(factory=rewards_add_factory_old),
        # 6. Remove reWARDS remove recipient EVM script factory (old ver) 0xc21e5e72Ffc223f02fC410aAedE3084a63963932 from Easy Track
        remove_evmscript_factory(factory=rewards_remove_factory_old),
    ]

    vote_desc_items = [
        "1) Add Referral program DAI top up EVM script factory 0x009ffa22ce4388d2F5De128Ca8E6fD229A312450 to Easy Track",
        "2) Add Referral program DAI add recipient EVM script factory 0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151 to Easy Track",
        "3) Add Referral program DAI remove recipient EVM script factory 0xd8f9B72Cd97388f23814ECF429cd18815F6352c1 to Easy Track",
        "4) Remove reWARDS top up EVM script factory (old ver) 0x77781A93C4824d2299a38AC8bBB11eb3cd6Bc3B7 from Easy Track",
        "5) Remove reWARDS add recipient EVM script factory (old ver) 0x9D15032b91d01d5c1D940eb919461426AB0dD4e3 from Easy Track",
        "6) Remove reWARDS remove recipient EVM script factory (old ver) 0xc21e5e72Ffc223f02fC410aAedE3084a63963932 from Easy Track",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
