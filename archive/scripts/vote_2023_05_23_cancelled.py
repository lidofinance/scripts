"""
Voting 23/05/2023.

1. Increase Easy Track motions amount limit: set motionsCountLimit to 20

2. Add reWARDS program top up EVM script factory for stETH 0x1F2b79FE297B7098875930bBA6dd17068103897E
3. Add reWARDS program add recipient EVM script factory for stETH 0x935cb3366Faf2cFC415B2099d1F974Fd27202b77
4. Add reWARDS program remove recipient EVM script factory for stETH 0x22010d1747CaFc370b1f1FBBa61022A313c5693b

5. Remove reWARDS program top up EVM script factory for LDO 0x85d703B2A4BaD713b596c647badac9A1e95bB03d
6. Remove reWARDS program add recipient EVM script factory for LDO 0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C
7. Remove reWARDS program remove recipient EVM script factory for LDO 0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E

8. Remove referral program top up EVM script factory for LDO 0x54058ee0E0c87Ad813C002262cD75B98A7F59218 from Easy Track
9. Remove referral program add recipient EVM script factory for LDO Track 0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51 from Easy Track
10. Remove referral program remove recipient EVM script factory for LDO 0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C  from Easy Track

11. Remove referral program top up EVM script factory for DAI 0x009ffa22ce4388d2F5De128Ca8E6fD229A312450 from Easy Track
12. Remove referral program add recipient EVM script factory for DAI  0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151 from Easy Track
13. Remove referral program remove recipient EVM script factory for DAI  • 0xd8f9B72Cd97388f23814ECF429cd18815F6352c1 from Easy Track
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import interface, ShapellaUpgradeTemplate  # type: ignore
from utils.agent import agent_forward
from utils.finance import make_steth_payout

from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.kernel import update_app_implementation
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    STAKING_ROUTER,
    WITHDRAWAL_VAULT,
    WITHDRAWAL_VAULT_IMPL,
    SELF_OWNED_STETH_BURNER,
    get_priority_fee,
)

from utils.easy_track import (
    set_motions_count_limit,
    add_evmscript_factory,
    create_permissions,
    remove_evmscript_factory
)

def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    # 1 Increase Easy Track motions amount limit
    motionsCountLimit = 20

    # 2-4 Add reWARDS stETH setup to Easy Track
    reWARDS_stETH_registry = interface.AllowedRecipientRegistry("0x48c4929630099b217136b64089E8543dB0E5163a")
    reWARDS_stETH_topup_factory = interface.TopUpAllowedRecipients("0x1F2b79FE297B7098875930bBA6dd17068103897E")
    reWARDS_stETH_add_recipient_factory = interface.AddAllowedRecipient("0x935cb3366Faf2cFC415B2099d1F974Fd27202b77")
    reWARDS_stETH_remove_recipient_factory = interface.RemoveAllowedRecipient("0x22010d1747CaFc370b1f1FBBa61022A313c5693b")

    # 5-7 Remove reWARDS LDO setup from Easy Track
    reWARDS_LDO_topup_factory = interface.TopUpAllowedRecipients("0x85d703B2A4BaD713b596c647badac9A1e95bB03d")
    reWARDS_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C")
    reWARDS_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E")

    # 8-10 Remove LDO referral program from Easy Track
    referral_program_LDO_topup_factory = interface.TopUpAllowedRecipients("0x54058ee0E0c87Ad813C002262cD75B98A7F59218")
    referral_program_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51")
    referral_program_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C")

    # 11-13 Remove LDO referral program from Easy Track
    referral_program_DAI_topup_factory = interface.TopUpAllowedRecipients("0x009ffa22ce4388d2F5De128Ca8E6fD229A312450")
    referral_program_DAI_add_recipient_factory = interface.AddAllowedRecipient("0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151")
    referral_program_DAI_remove_recipient_factory = interface.RemoveAllowedRecipient("0xd8f9B72Cd97388f23814ECF429cd18815F6352c1")


    call_script_items = [
        # 1.
        set_motions_count_limit(motionsCountLimit),
        # 2.
        add_evmscript_factory(
            factory=reWARDS_stETH_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(reWARDS_stETH_registry, "updateSpentAmount")[2:],
        ),
        # 3.
        add_evmscript_factory(
            factory=reWARDS_stETH_add_recipient_factory,
            permissions=create_permissions(reWARDS_stETH_registry, "addRecipient"),
        ),
        # 4.
        add_evmscript_factory(
            factory=reWARDS_stETH_remove_recipient_factory,
            permissions=create_permissions(reWARDS_stETH_registry, "removeRecipient"),
        ),
        # 5.
        remove_evmscript_factory(factory=reWARDS_LDO_topup_factory),
        # 6.
        remove_evmscript_factory(factory=reWARDS_LDO_add_recipient_factory),
        # 7.
        remove_evmscript_factory(factory=reWARDS_LDO_remove_recipient_factory),
        # 8.
        remove_evmscript_factory(factory=referral_program_LDO_topup_factory),
        # 9.
        remove_evmscript_factory(factory=referral_program_LDO_add_recipient_factory),
        # 10.
        remove_evmscript_factory(factory=referral_program_LDO_remove_recipient_factory),
        # 11.
        remove_evmscript_factory(factory=referral_program_DAI_topup_factory),
        # 12.
        remove_evmscript_factory(factory=referral_program_DAI_add_recipient_factory),
        # 13.
        remove_evmscript_factory(factory=referral_program_DAI_remove_recipient_factory),

    ]

    vote_desc_items = [
        "1) Increase Easy Track motions amount limit: set motionsCountLimit to 20",
        "2) Add reWARDS program top up EVM script factory for stETH 0x1F2b79FE297B7098875930bBA6dd17068103897E",
        "3) Add reWARDS program add recipient EVM script factory for stETH 0x935cb3366Faf2cFC415B2099d1F974Fd27202b77",
        "4) Add reWARDS program remove recipient EVM script factory for stETH 0x22010d1747CaFc370b1f1FBBa61022A313c5693b",
        "5) Remove reWARDS program top up EVM script factory for LDO 0x85d703B2A4BaD713b596c647badac9A1e95bB03d",
        "6) Remove reWARDS program add recipient EVM script factory for LDO 0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C",
        "7) Remove reWARDS program remove recipient EVM script factory for LDO 0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E",
        "8) Remove referral program top up EVM script factory for LDO 0x54058ee0E0c87Ad813C002262cD75B98A7F59218 from Easy Track",
        "9) Remove referral program add recipient EVM script factory for LDO Track 0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51 from Easy Track",
        "10) Remove referral program remove recipient EVM script factory for LDO 0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C  from Easy Track",
        "11) Remove referral program top up EVM script factory for DAI 0x009ffa22ce4388d2F5De128Ca8E6fD229A312450 from Easy Track",
        "12) Remove referral program add recipient EVM script factory for DAI  0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151 from Easy Track",
        "13) Remove referral program remove recipient EVM script factory for DAI  • 0xd8f9B72Cd97388f23814ECF429cd18815F6352c1 from Easy Track",

    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
