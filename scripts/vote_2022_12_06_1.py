"""
Voting 06/12/2022.
1. Revoke CREATE_PAYMENTS_ROLE role from EasyTrack EVM script executor 
2. Grant CREATE_PAYMENTS_ROLE role to EasyTrack EVM script executor with limits: 2,000,000 DAI, 5,000,000 LDO, 1,000 ETH, 1,000 stETH
3. Remove LEGO EVM script factory 0x648C8Be548F43eca4e482C0801Ebccccfb944931 from the EasyTrack
4. Add LEGO DAI top up EVM script factory 0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC
5. Add LEGO LDO top up EVM script factory 0x00caAeF11EC545B192f16313F53912E453c91458
6. Add reWARDS top up EVM script factory 0x85d703B2A4BaD713b596c647badac9A1e95bB03d
7. Add reWARDS add recipient EVM script factory 0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C
8. Add reWARDS remove recipient EVM script factory 0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E
9. Add Lido Contributors Group DAI payment EVM script factory (RCC) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e
10. Add Lido Contributors Group DAI payment EVM script factory (PML) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD
11. Add Lido Contributors Group DAI payment EVM script factory (ATC) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07
12. Add Gas Funder ETH payment EVM script factory 0x41F9daC5F89092dD6061E59578A2611849317dc8
"""

import time

from typing import Dict, Tuple, Optional, List

from brownie import interface, ZERO_ADDRESS
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.permissions import encode_permission_revoke, encode_permission_grant_p
from utils.easy_track import add_evmscript_factory, create_permissions, remove_evmscript_factory
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op

from utils.config import (
    contracts,
    get_deployer_account,
    lido_dao_finance_address,
    lido_easytrack_evmscriptexecutor,
    ldo_token_address,
    dai_token_address,
    lido_dao_steth_address,
)

eth = {
    "limit": 1_000 * (10**18),
    "address": ZERO_ADDRESS,
}

steth = {
    "limit": 1_000 * (10**18),
    "address": lido_dao_steth_address,
}

ldo = {
    "limit": 5_000_000 * (10**18),
    "address": ldo_token_address,
}

dai = {
    "limit": 2_000_000 * (10**18),
    "address": dai_token_address,
}


def amount_limits() -> List[Param]:
    token_arg_index = 0
    amount_arg_index = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=1, success=2, failure=3)
        ),
        # 1: (_token == LDO)
        Param(token_arg_index, Op.EQ, ArgumentValue(ldo["address"])),
        # 2: { return _amount <= 5_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(ldo["limit"])),
        # 3: else if (4) then (5) else (6)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=4, success=5, failure=6)
        ),
        # 4: (_token == ETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(eth["address"])),
        # 5: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(eth["limit"])),
        # 6: else if (7) then (8) else (9)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=7, success=8, failure=9)
        ),
        # 7: (_token == DAI)
        Param(token_arg_index, Op.EQ, ArgumentValue(dai["address"])),
        # 8: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(dai["limit"])),
        # 9: else if (10) then (11) else (12)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=10, success=11, failure=12),
        ),
        # 10: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth["address"])),
        # 11: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth["limit"])),
        # 12: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    finance = interface.Finance(lido_dao_finance_address)

    lego_factory_old = interface.IEVMScriptFactory("0x648C8Be548F43eca4e482C0801Ebccccfb944931")
    lego_dai_factory = interface.TopUpAllowedRecipients("0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC")
    lego_ldo_factory = interface.TopUpAllowedRecipients("0x00caAeF11EC545B192f16313F53912E453c91458")
    rewards_topup_factory = interface.TopUpAllowedRecipients("0x85d703B2A4BaD713b596c647badac9A1e95bB03d")
    rewards_add_recipient_factory = interface.AddAllowedRecipient("0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C")
    rewards_remove_recipient_factory = interface.RemoveAllowedRecipient("0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E")
    rcc_dai_topup_factory = interface.TopUpAllowedRecipients("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_dai_topup_factory = interface.TopUpAllowedRecipients("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_dai_topup_factory = interface.TopUpAllowedRecipients("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")
    gas_refund_eth_topup_factory = interface.TopUpAllowedRecipients("0x41F9daC5F89092dD6061E59578A2611849317dc8")

    lego_dai_registry = interface.AllowedRecipientRegistry("0xb0FE4D300334461523D9d61AaD90D0494e1Abb43")
    lego_ldo_registry = interface.AllowedRecipientRegistry("0x97615f72c3428A393d65A84A3ea6BBD9ad6C0D74")
    rewards_registry = interface.AllowedRecipientRegistry("0xAa47c268e6b2D4ac7d7f7Ffb28A39484f5212c2A")
    rcc_dai_registry = interface.AllowedRecipientRegistry("0xDc1A0C7849150f466F07d48b38eAA6cE99079f80")
    pml_dai_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    atc_dai_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")
    gas_refund_registry = interface.AllowedRecipientRegistry("0xCf46c4c7f936dF6aE12091ADB9897E3F2363f16F")

    call_script_items = [
        # 1. Revoke role CREATE_PAYMENTS_ROLE from EVM script executor
        encode_permission_revoke(
            target_app=finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            revoke_from=lido_easytrack_evmscriptexecutor,
        ),
        # 2. Grant role CREATE_PAYMENTS_ROLE to EasyTrack EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
        # with limits: 1000 ETH, 1000 stETH, 5M LDO, 2M DAI
        encode_permission_grant_p(
            target_app=finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            grant_to=lido_easytrack_evmscriptexecutor,
            params=amount_limits(),
        ),
        # 3. Remove LEGO EVM script factory 0x648C8Be548F43eca4e482C0801Ebccccfb944931 from the EasyTrack
        remove_evmscript_factory(factory=lego_factory_old),
        # 4. Add LEGO DAI top up EVM script factory 0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC
        add_evmscript_factory(
            factory=lego_dai_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(lego_dai_registry, "updateSpentAmount")[2:],
        ),
        # 5. Add LEGO LDO top up EVM script factory 0x00caAeF11EC545B192f16313F53912E453c91458
        add_evmscript_factory(
            factory=lego_ldo_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(lego_ldo_registry, "updateSpentAmount")[2:],
        ),
        # 6. Add reWARDS top up EVM script factory 0x85d703B2A4BaD713b596c647badac9A1e95bB03d
        add_evmscript_factory(
            factory=rewards_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(rewards_registry, "updateSpentAmount")[2:],
        ),
        # 7. Add reWARDS add recipient EVM script factory 0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C
        add_evmscript_factory(
            factory=rewards_add_recipient_factory,
            permissions=create_permissions(rewards_registry, "addRecipient"),
        ),
        # 8. Add reWARDS remove recipient EVM script factory 0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E
        add_evmscript_factory(
            factory=rewards_remove_recipient_factory,
            permissions=create_permissions(rewards_registry, "removeRecipient"),
        ),
        # 9. Add Lido Contributors Group DAI payment EVM script factory (RCC) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e
        add_evmscript_factory(
            factory=rcc_dai_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(rcc_dai_registry, "updateSpentAmount")[2:],
        ),
        # 10. Add Lido Contributors Group DAI payment EVM script factory (PML) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD
        add_evmscript_factory(
            factory=pml_dai_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(pml_dai_registry, "updateSpentAmount")[2:],
        ),
        # 11. Add Lido Contributors Group DAI payment EVM script factory (ATC) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07
        add_evmscript_factory(
            factory=atc_dai_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(atc_dai_registry, "updateSpentAmount")[2:],
        ),
        # 12. Add Gas Funder ETH payment EVM script factory 0x41F9daC5F89092dD6061E59578A2611849317dc8
        add_evmscript_factory(
            factory=gas_refund_eth_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(gas_refund_registry, "updateSpentAmount")[2:],
        ),
    ]

    vote_desc_items = [
        "1) Revoke CREATE_PAYMENTS_ROLE role from EasyTrack EVM script executor",
        "2) Grant CREATE_PAYMENTS_ROLE role to EasyTrack EVM script executor with limits: 2,000,000 DAI, 5,000,000 LDO, 1,000 ETH, 1,000 stETH",
        "3) Remove LEGO EVM script factory 0x648C8Be548F43eca4e482C0801Ebccccfb944931 from the EasyTrack",
        "4) Add LEGO DAI top up EVM script factory 0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC",
        "5) Add LEGO LDO top up EVM script factory 0x00caAeF11EC545B192f16313F53912E453c91458",
        "6) Add reWARDS top up EVM script factory 0x85d703B2A4BaD713b596c647badac9A1e95bB03d",
        "7) Add reWARDS add recipient EVM script factory 0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C",
        "8) Add reWARDS remove recipient EVM script factory 0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E",
        "9) Add Lido Contributors Group DAI payment EVM script factory (RCC) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e",
        "10) Add Lido Contributors Group DAI payment EVM script factory (PML) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD",
        "11) Add Lido Contributors Group DAI payment EVM script factory (ATC) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07",
        "12) Add Gas Funder ETH payment EVM script factory 0x41F9daC5F89092dD6061E59578A2611849317dc8",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
