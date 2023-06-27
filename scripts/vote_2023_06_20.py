"""
Voting 20/06/2023.

I. RockLogic Slashing Incident Staker Compensation: burn 13.45978634 stETH as cover
1. Transfer 13.45978634 stETH from Insurance fund to Agent
2. Set 13.45978634 stETH as the allowance of Burner over the Agent's tokens
3. Grant REQUEST_BURN_MY_STETH_ROLE to Agent
4. Request to burn 13.45978634 stETH for cover
5. Renounce REQUEST_BURN_MY_STETH_ROLE from Agent

II. Add stETH Gas Supply factories
6. Add Gas Supply top up EVM script factory for stETH 0x200dA0b6a9905A377CF8D469664C65dB267009d1
7. Add Gas Supply add recipient EVM script factory for stETH 0x48c135Ff690C2Aa7F5B11C539104B5855A4f9252
8. Add Gas Supply remove recipient EVM script factory for stETH 0x7E8eFfAb3083fB26aCE6832bFcA4C377905F97d7

III. Add stETH reWARDS factories
9. Add reWARDS program top up EVM script factory for stETH 0x1F2b79FE297B7098875930bBA6dd17068103897E
10. Add reWARDS program add recipient EVM script factory for stETH 0x935cb3366Faf2cFC415B2099d1F974Fd27202b77
11. Add reWARDS program remove recipient EVM script factory for stETH 0x22010d1747CaFc370b1f1FBBa61022A313c5693b

IV. Remove LDO reWARDS factories
12. Remove reWARDS program top up EVM script factory for LDO 0x85d703B2A4BaD713b596c647badac9A1e95bB03d
13. Remove reWARDS program add recipient EVM script factory for LDO 0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C
14. Remove reWARDS program remove recipient EVM script factory for LDO 0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E

V. Remove LDO and DAI referral factories
15. Remove referral program top up EVM script factory for LDO 0x54058ee0E0c87Ad813C002262cD75B98A7F59218 from Easy Track
16. Remove referral program add recipient EVM script factory for LDO 0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51 from Easy Track
17. Remove referral program remove recipient EVM script factory for LDO 0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C from Easy Track
18. Remove referral program top up EVM script factory for DAI 0x009ffa22ce4388d2F5De128Ca8E6fD229A312450 from Easy Track
19. Remove referral program add recipient EVM script factory for DAI 0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151 from Easy Track
20. Remove referral program remove recipient EVM script factory for DAI 0xd8f9B72Cd97388f23814ECF429cd18815F6352c1 from Easy Track

VI. Send 150,000 LDO to Lido on Polygon team 0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290 for reaching 3% share milestone

VII. Send 200,000 LDO to PML multisig 0x17F6b2C738a63a8D3A113a228cfd0b373244633D

VIII. Change NO names and addresses
23. Create permission for MANAGE_NODE_OPERATOR_ROLE assigning it to Voting
24. Change the on-chain name of node operator with id 1 from 'Certus One' to 'Jump Crypto'
25. Change the on-chain name of node operator with id 21 from 'ConsenSys Codefi' to 'Consensys'
26. Change the on-chain name of node operator with id 8 from 'SkillZ' to 'Kiln'
27. Change the reward address of node operator with id 8 from 0xe080E860741b7f9e8369b61645E68AD197B1e74C to 0xD6B7d52E15678B9195F12F3a6D6cb79dcDcCb690
28. Change the reward address of node operator with id 22 from 0x49Df3CCa2670eB0D591146B16359fe336e476F29 to 0x765c6a8f20c842E8C826B0D9425015784F982aFc
29. Revoke MANAGE_NODE_OPERATOR_ROLE from Voting

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import interface
from utils.agent import agent_forward
from utils.finance import make_steth_payout

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.finance import make_ldo_payout
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
    add_evmscript_factory,
    create_permissions,
    remove_evmscript_factory
)
from utils.node_operators import (
    encode_set_node_operator_name,
    encode_set_node_operator_reward_address
)

from utils.permissions import (
    encode_permission_create,
    encode_permission_revoke
)
def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    no_registry = contracts.node_operators_registry

    # I. RockLogic Slashing Incident Staker Compensation
    stETH_to_burn = 13.45978634 * 1e18
    REQUEST_BURN_MY_STETH_ROLE = "0x28186f938b759084eea36948ef1cd8b40ec8790a98d5f1a09b70879fe054e5cc"

    # II. Add Gas Supply stETH setup to Easy Track
    gasSupply_stETH_registry = interface.AllowedRecipientRegistry("0x49d1363016aA899bba09ae972a1BF200dDf8C55F")
    gasSupply_stETH_topup_factory = interface.TopUpAllowedRecipients("0x200dA0b6a9905A377CF8D469664C65dB267009d1")
    gasSupply_stETH_add_recipient_factory = interface.AddAllowedRecipient("0x48c135Ff690C2Aa7F5B11C539104B5855A4f9252")
    gasSupply_stETH_remove_recipient_factory = interface.RemoveAllowedRecipient("0x7E8eFfAb3083fB26aCE6832bFcA4C377905F97d7")

    # III. Add reWARDS stETH setup to Easy Track
    reWARDS_stETH_registry = interface.AllowedRecipientRegistry("0x48c4929630099b217136b64089E8543dB0E5163a")
    reWARDS_stETH_topup_factory = interface.TopUpAllowedRecipients("0x1F2b79FE297B7098875930bBA6dd17068103897E")
    reWARDS_stETH_add_recipient_factory = interface.AddAllowedRecipient("0x935cb3366Faf2cFC415B2099d1F974Fd27202b77")
    reWARDS_stETH_remove_recipient_factory = interface.RemoveAllowedRecipient("0x22010d1747CaFc370b1f1FBBa61022A313c5693b")

    # IV. Remove reWARDS LDO setup from Easy Track
    reWARDS_LDO_topup_factory = interface.TopUpAllowedRecipients("0x85d703B2A4BaD713b596c647badac9A1e95bB03d")
    reWARDS_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C")
    reWARDS_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E")

    # V. Remove LDO and DAI referral program from Easy Track
    referral_program_LDO_topup_factory = interface.TopUpAllowedRecipients("0x54058ee0E0c87Ad813C002262cD75B98A7F59218")
    referral_program_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51")
    referral_program_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C")
    referral_program_DAI_topup_factory = interface.TopUpAllowedRecipients("0x009ffa22ce4388d2F5De128Ca8E6fD229A312450")
    referral_program_DAI_add_recipient_factory = interface.AddAllowedRecipient("0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151")
    referral_program_DAI_remove_recipient_factory = interface.RemoveAllowedRecipient("0xd8f9B72Cd97388f23814ECF429cd18815F6352c1")

    # VI. Polygon team incentives
    polygon_team_address = "0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290"
    polygon_team_incentives_amount = 150_000 * 10**18

    # VII. Transfer 200k LDO to PML multisig 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
    PML_multisig = "0x17F6b2C738a63a8D3A113a228cfd0b373244633D"
    PML_topup_amount = 200_000 * 10**18

    # VIII. Change NO names and addresses
    NO_registry = interface.NodeOperatorsRegistry(contracts.node_operators_registry)

    CertusOne_Jumpcrypto_id = 1
    CertusOne_Jumpcrypto_new_name = "Jump Crypto"

    ConsenSysCodefi_Consensys_id = 21
    ConsenSysCodefi_Consensys_new_name = "Consensys"

    SkillZ_Kiln_id = 8
    SkillZ_Kiln_new_name = "Kiln"
    SkillZ_Kiln_new_address = "0xD6B7d52E15678B9195F12F3a6D6cb79dcDcCb690"

    RockLogic_id = 22
    RockLogic_new_address = "0x765c6a8f20c842E8C826B0D9425015784F982aFc"

    call_script_items = [
        # I.
        agent_forward(
            [
                (
                    contracts.insurance_fund.address,
                    contracts.insurance_fund.transferERC20.encode_input(contracts.lido.address, contracts.agent.address, stETH_to_burn),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.lido.address,
                    contracts.lido.approve.encode_input(contracts.burner.address, stETH_to_burn),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.burner.address,
                    contracts.burner.grantRole.encode_input(REQUEST_BURN_MY_STETH_ROLE, contracts.agent.address),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.burner.address,
                    contracts.burner.requestBurnMyStETHForCover.encode_input(stETH_to_burn),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.burner.address,
                    contracts.burner.renounceRole.encode_input(REQUEST_BURN_MY_STETH_ROLE, contracts.agent.address),
                )
            ]
        ),
        # II.
        add_evmscript_factory(
            factory=gasSupply_stETH_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(gasSupply_stETH_registry, "updateSpentAmount")[2:],
        ),
        add_evmscript_factory(
            factory=gasSupply_stETH_add_recipient_factory,
            permissions=create_permissions(gasSupply_stETH_registry, "addRecipient"),
        ),
        add_evmscript_factory(
            factory=gasSupply_stETH_remove_recipient_factory,
            permissions=create_permissions(gasSupply_stETH_registry, "removeRecipient"),
        ),
        # III.
        add_evmscript_factory(
            factory=reWARDS_stETH_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(reWARDS_stETH_registry, "updateSpentAmount")[2:],
        ),
        add_evmscript_factory(
            factory=reWARDS_stETH_add_recipient_factory,
            permissions=create_permissions(reWARDS_stETH_registry, "addRecipient"),
        ),
        add_evmscript_factory(
            factory=reWARDS_stETH_remove_recipient_factory,
            permissions=create_permissions(reWARDS_stETH_registry, "removeRecipient"),
        ),
        # IV.
        remove_evmscript_factory(factory=reWARDS_LDO_topup_factory),
        remove_evmscript_factory(factory=reWARDS_LDO_add_recipient_factory),
        remove_evmscript_factory(factory=reWARDS_LDO_remove_recipient_factory),
        # V.
        remove_evmscript_factory(factory=referral_program_LDO_topup_factory),
        remove_evmscript_factory(factory=referral_program_LDO_add_recipient_factory),
        remove_evmscript_factory(factory=referral_program_LDO_remove_recipient_factory),
        remove_evmscript_factory(factory=referral_program_DAI_topup_factory),
        remove_evmscript_factory(factory=referral_program_DAI_add_recipient_factory),
        remove_evmscript_factory(factory=referral_program_DAI_remove_recipient_factory),
        # VI. Send 150,000 LDO to Lido on Polygon team 0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290 for reaching 3% share milestone
        make_ldo_payout(
            target_address=polygon_team_address,
            ldo_in_wei=polygon_team_incentives_amount,
            reference="Incentives for Lido on Polygon team 0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290 for reaching 3% share milestone",
        ),
        # VII. Transfer 200k LDO to PML multisig 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
        make_ldo_payout(
            target_address=PML_multisig,
            ldo_in_wei=PML_topup_amount,
            reference="Transfer 200k LDO to PML multisig 0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
        ),
        # VIII. Change NO names and addresses
        encode_permission_create(entity=contracts.voting, target_app=no_registry, permission_name="MANAGE_NODE_OPERATOR_ROLE", manager=contracts.voting),
        encode_set_node_operator_name(CertusOne_Jumpcrypto_id, CertusOne_Jumpcrypto_new_name, no_registry),
        encode_set_node_operator_name(ConsenSysCodefi_Consensys_id, ConsenSysCodefi_Consensys_new_name, no_registry),
        encode_set_node_operator_name(SkillZ_Kiln_id, SkillZ_Kiln_new_name, no_registry),
        encode_set_node_operator_reward_address(SkillZ_Kiln_id, SkillZ_Kiln_new_address, no_registry),
        encode_set_node_operator_reward_address(RockLogic_id, RockLogic_new_address, no_registry),
        encode_permission_revoke(no_registry, "MANAGE_NODE_OPERATOR_ROLE", revoke_from=contracts.voting),
    ]


    vote_desc_items = [
        "1) Transfer 13.45978634 stETH from Insurance fund to Agent",
        "2) Set 13.45978634 stETH as the allowance of Burner over the Agent's tokens",
        "3) Grant REQUEST_BURN_MY_STETH_ROLE to Agent",
        "4) Request to burn 13.45978634 stETH for cover",
        "5) Renounce REQUEST_BURN_MY_STETH_ROLE from Agent",
        "6) Add Gas Supply top up EVM script factory for stETH ",
        "7) Add Gas Supply add recipient EVM script factory for stETH ",
        "8) Add Gas Supply remove recipient EVM script factory for stETH ",
        "9) Add reWARDS program top up EVM script factory for stETH 0x1F2b79FE297B7098875930bBA6dd17068103897E",
        "10) Add reWARDS program add recipient EVM script factory for stETH 0x935cb3366Faf2cFC415B2099d1F974Fd27202b77",
        "11) Add reWARDS program remove recipient EVM script factory for stETH 0x22010d1747CaFc370b1f1FBBa61022A313c5693b",
        "12) Remove reWARDS program top up EVM script factory for LDO 0x85d703B2A4BaD713b596c647badac9A1e95bB03d",
        "13) Remove reWARDS program add recipient EVM script factory for LDO 0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C",
        "14) Remove reWARDS program remove recipient EVM script factory for LDO 0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E",
        "15) Remove referral program top up EVM script factory for LDO 0x54058ee0E0c87Ad813C002262cD75B98A7F59218 from Easy Track",
        "16) Remove referral program add recipient EVM script factory for LDO Track 0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51 from Easy Track",
        "17) Remove referral program remove recipient EVM script factory for LDO 0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C from Easy Track",
        "18) Remove referral program top up EVM script factory for DAI 0x009ffa22ce4388d2F5De128Ca8E6fD229A312450 from Easy Track",
        "19) Remove referral program add recipient EVM script factory for DAI  0x8F06a7f244F6Bb4B68Cd6dB05213042bFc0d7151 from Easy Track",
        "20) Remove referral program remove recipient EVM script factory for DAI 0xd8f9B72Cd97388f23814ECF429cd18815F6352c1 from Easy Track",
        "21) Send 150,000 LDO to Lido on Polygon team 0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290 for reaching 3% share milestone",
        "22) Send 200,000 LDO to PML multisig 0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
        "23) Create permission for MANAGE_NODE_OPERATOR_ROLE assigning it to Voting",
        "24) Change the on-chain name of node operator with id 1 from 'Certus One' to 'Jump Crypto'",
        "25) Change the on-chain name of node operator with id 21 from 'ConsenSys Codefi' to 'Consensys'",
        "26) Change the on-chain name of node operator with id 8 from 'SkillZ' to 'Kiln'",
        "27) Change the reward address of node operator with id 8 from 0xe080E860741b7f9e8369b61645E68AD197B1e74C to 0xD6B7d52E15678B9195F12F3a6D6cb79dcDcCb690",
        "28) Change the reward address of node operator with id 22 from 0x49Df3CCa2670eB0D591146B16359fe336e476F29 to 0x765c6a8f20c842E8C826B0D9425015784F982aFc",
        "29) Revoke MANAGE_NODE_OPERATOR_ROLE from Voting",
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
