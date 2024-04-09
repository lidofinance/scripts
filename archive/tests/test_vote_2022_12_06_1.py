"""
Tests for voting 06/12/2022.
"""
import math
from scripts.vote_2022_12_06_1 import start_vote

from brownie import ZERO_ADDRESS, chain, reverts, web3, accounts
from brownie.network.transaction import TransactionReceipt

from eth_abi.abi import encode

from utils.config import network_name
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grantp_event,
    validate_permission_revoke_event,
)
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op
from utils.easy_track import create_permissions
from utils.agent import agent_forward
from utils.voting import confirm_vote_script, create_vote, bake_vote_items

STETH_ERROR_MARGIN = 2

permission = Permission(
    entity="0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",  # EVMScriptExecutor
    app="0xB9E5CBB9CA5b0d659238807E84D0176930753d86",  # Finance Aragon App
    role="0x5de467a460382d13defdc02aacddc9c7d6605d6d4e0b8bd2f70732cae8ea17bc",
)  # keccak256('CREATE_PAYMENTS_ROLE')


def has_payments_permission(acl, finance, sender, token, receiver, amount) -> bool:
    return acl.hasPermission["address,address,bytes32,uint[]"](
        sender, finance, finance.CREATE_PAYMENTS_ROLE(), [token, receiver, amount]
    )


def test_vote(
    helpers,
    accounts,
    vote_id_from_env,
    bypass_events_decoding,
    unknown_person,
    interface,
    ldo_holder,
):

    steth_token = interface.ERC20("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
    ldo_token = interface.ERC20("0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32")
    dai_token = interface.ERC20("0x6B175474E89094C44Da98b954EedeAC495271d0F")
    usdc_token = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"

    finance = interface.Finance("0xB9E5CBB9CA5b0d659238807E84D0176930753d86")
    dao_voting = interface.Voting("0x2e59A20f205bB85a89C53f1936454680651E618e")
    easy_track = interface.EasyTrack("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")
    acl = interface.ACL("0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb")

    evmscriptexecutor = accounts.at("0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977", {"force": True})
    agent = accounts.at("0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c", {"force": True})

    lego_factory_old = interface.IEVMScriptFactory("0x648C8Be548F43eca4e482C0801Ebccccfb944931")
    lego_dai_factory = interface.TopUpAllowedRecipients("0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC")
    lego_ldo_factory = interface.TopUpAllowedRecipients("0x00caAeF11EC545B192f16313F53912E453c91458")
    rewards_topup_factory = interface.TopUpAllowedRecipients("0x85d703B2A4BaD713b596c647badac9A1e95bB03d")
    rewards_add_recipient_factory = interface.AddAllowedRecipient("0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C")
    rewards_remove_recipient_factory = interface.RemoveAllowedRecipient("0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E")
    rcc_dai_topup_factory = interface.TopUpAllowedRecipients("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_dai_topup_factory = interface.TopUpAllowedRecipients("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_dai_topup_factory = interface.TopUpAllowedRecipients("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")

    lego_dai_registry = interface.AllowedRecipientRegistry("0xb0FE4D300334461523D9d61AaD90D0494e1Abb43")
    lego_ldo_registry = interface.AllowedRecipientRegistry("0x97615f72c3428A393d65A84A3ea6BBD9ad6C0D74")
    rewards_registry = interface.AllowedRecipientRegistry("0xAa47c268e6b2D4ac7d7f7Ffb28A39484f5212c2A")
    rcc_dai_registry = interface.AllowedRecipientRegistry("0xDc1A0C7849150f466F07d48b38eAA6cE99079f80")
    pml_dai_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    atc_dai_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")

    lego_multisig = accounts.at("0x12a43b049A7D330cB8aEAB5113032D18AE9a9030", {"force": True})
    rewards_multisig = accounts.at("0x87D93d9B2C672bf9c9642d853a8682546a5012B5", {"force": True})
    rcc_funder = accounts.at("0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437", {"force": True})
    pml_funder = accounts.at("0x17F6b2C738a63a8D3A113a228cfd0b373244633D", {"force": True})
    atc_funder = accounts.at("0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956", {"force": True})

    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 8

    assert lego_factory_old in old_factories_list
    assert lego_dai_factory not in old_factories_list
    assert lego_ldo_factory not in old_factories_list
    assert rewards_topup_factory not in old_factories_list
    assert rewards_add_recipient_factory not in old_factories_list
    assert rewards_remove_recipient_factory not in old_factories_list
    assert rcc_dai_topup_factory not in old_factories_list
    assert pml_dai_topup_factory not in old_factories_list
    assert atc_dai_topup_factory not in old_factories_list

    ##
    ## START VOTE
    ##

    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 15

    # 1. Revoke role CREATE_PAYMENTS_ROLE from EVM script executor
    # 2. Grant role CREATE_PAYMENTS_ROLE to EasyTrack EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
    # with limits: 1000 ETH, 1000 stETH, 5M LDO, 2M DAI

    assert has_payments_permission(acl, finance, permission.entity, eth["address"], ldo_holder.address, eth["limit"])
    assert has_payments_permission(
        acl, finance, permission.entity, steth["address"], ldo_holder.address, steth["limit"]
    )
    assert has_payments_permission(acl, finance, permission.entity, ldo["address"], ldo_holder.address, ldo["limit"])
    assert has_payments_permission(acl, finance, permission.entity, dai["address"], ldo_holder.address, dai["limit"])

    assert not has_payments_permission(
        acl, finance, permission.entity, eth["address"], ldo_holder.address, eth["limit"] + 1
    )
    assert not has_payments_permission(
        acl, finance, permission.entity, steth["address"], ldo_holder.address, steth["limit"] + 1
    )
    assert not has_payments_permission(
        acl, finance, permission.entity, ldo["address"], ldo_holder.address, ldo["limit"] + 1
    )
    assert not has_payments_permission(
        acl, finance, permission.entity, dai["address"], ldo_holder.address, dai["limit"] + 1
    )

    assert not has_payments_permission(
        acl, finance, accounts[0].address, eth["address"], ldo_holder.address, eth["limit"]
    )
    assert not has_payments_permission(acl, finance, accounts[0].address, usdc_token, ldo_holder.address, 1)

    # 1000 ETH
    agent_balance_before = agent.balance()
    eth_balance_before = unknown_person.balance()
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            ZERO_ADDRESS,
            unknown_person,
            1000 * 10**18 + 1,
            "ETH transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        ZERO_ADDRESS, unknown_person, 1000 * 10**18, "ETH transfer", {"from": evmscriptexecutor}
    )
    assert agent.balance() == agent_balance_before - 1000 * 10**18
    assert unknown_person.balance() == eth_balance_before + 1000 * 10**18

    # 1000 stETH
    agent_steth_balance_before = steth_token.balanceOf(agent)
    stETH_balance_before = steth_token.balanceOf(unknown_person)
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            steth_token,
            unknown_person,
            1000 * 10**18 + 1,
            "stETH transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        steth_token, unknown_person, 1000 * 10**18, "stETH transfer", {"from": evmscriptexecutor}
    )
    assert math.isclose(
        steth_token.balanceOf(agent), agent_steth_balance_before - 1000 * 10**18, abs_tol=STETH_ERROR_MARGIN
    )
    assert math.isclose(
        steth_token.balanceOf(unknown_person), stETH_balance_before + 1000 * 10**18, abs_tol=STETH_ERROR_MARGIN
    )

    # 5_000_000 LDO
    agent_ldo_balance_before = ldo_token.balanceOf(agent)
    ldo_balance_before = ldo_token.balanceOf(unknown_person)
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            ldo_token,
            unknown_person,
            5_000_000 * 10**18 + 1,
            "LDO transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        ldo_token, unknown_person, 5_000_000 * 10**18, "LDO transfer", {"from": evmscriptexecutor}
    )
    assert ldo_token.balanceOf(agent) == agent_ldo_balance_before - 5_000_000 * 10**18
    assert ldo_token.balanceOf(unknown_person) == ldo_balance_before + 5_000_000 * 10**18

    # 2_000_000 DAI
    agent_dai_balance_before = dai_token.balanceOf(agent)
    dai_balance_before = dai_token.balanceOf(unknown_person)
    with reverts("APP_AUTH_FAILED"):
        finance.newImmediatePayment(
            dai_token,
            unknown_person,
            2_000_000 * 10**18 + 1,
            "DAI transfer",
            {"from": evmscriptexecutor},
        )
    finance.newImmediatePayment(
        dai_token, unknown_person, 2_000_000 * 10**18, "DAI transfer", {"from": evmscriptexecutor}
    )
    assert dai_token.balanceOf(agent) == agent_dai_balance_before - 2_000_000 * 10**18
    assert dai_token.balanceOf(unknown_person) == dai_balance_before + 2_000_000 * 10**18

    # 3. Remove LEGO EVM script factory 0x648C8Be548F43eca4e482C0801Ebccccfb944931 from the EasyTrack
    assert lego_factory_old not in updated_factories_list

    # 4. Add LEGO DAI top up EVM script factory 0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC
    assert lego_dai_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        lego_multisig,
        lego_dai_factory,
        dai_token,
        [lego_multisig],
        [10 * 10**18],
        unknown_person,
    )
    check_add_and_remove_recipient_with_voting(lego_dai_registry, helpers, ldo_holder, dao_voting)

    # 5. Add LEGO LDO top up EVM script factory 0x00caAeF11EC545B192f16313F53912E453c91458
    assert lego_ldo_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        lego_multisig,
        lego_ldo_factory,
        ldo_token,
        [lego_multisig],
        [10 * 10**18],
        unknown_person,
    )
    check_add_and_remove_recipient_with_voting(lego_ldo_registry, helpers, ldo_holder, dao_voting)

    # 6. Add reWARDS top up EVM script factory 0x85d703B2A4BaD713b596c647badac9A1e95bB03d
    assert rewards_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        rewards_multisig,
        rewards_topup_factory,
        ldo_token,
        [
            accounts.at("0x753D5167C31fBEB5b49624314d74A957Eb271709", {"force": True}),
            accounts.at("0x87D93d9B2C672bf9c9642d853a8682546a5012B5", {"force": True}),
            accounts.at("0x86F6c353A0965eB069cD7f4f91C1aFEf8C725551", {"force": True}),
            accounts.at("0xe3224542066D3bbc02Bc3d70B641bE4Bc6F40E36", {"force": True}),
        ],
        [10 * 10**18, 10 * 10**18, 10 * 10**18, 10 * 10**18],
        unknown_person,
    )
    check_add_and_remove_recipient_with_voting(rewards_registry, helpers, ldo_holder, dao_voting)

    # 7. Add reWARDS add recipient EVM script factory 0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C
    assert rewards_add_recipient_factory in updated_factories_list
    create_and_enact_add_recipient_motion(
        easy_track,
        rewards_multisig,
        rewards_registry,
        rewards_add_recipient_factory,
        unknown_person,
        "New recipient",
        ldo_holder,
    )

    # 8. Add reWARDS remove recipient EVM script factory 0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E
    assert rewards_remove_recipient_factory in updated_factories_list
    create_and_enact_remove_recipient_motion(
        easy_track,
        rewards_multisig,
        rewards_registry,
        rewards_remove_recipient_factory,
        unknown_person,
        ldo_holder,
    )

    # 9. Add Lido Contributors Group DAI payment EVM script factory (RCC) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e
    assert rcc_dai_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        rcc_funder,
        rcc_dai_topup_factory,
        dai_token,
        [rcc_funder],
        [10 * 10**18],
        unknown_person,
    )
    check_add_and_remove_recipient_with_voting(rcc_dai_registry, helpers, ldo_holder, dao_voting)

    # 10. Add Lido Contributors Group DAI payment EVM script factory (PML) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD
    assert pml_dai_topup_factory in updated_factories_list
    create_and_enact_payment_motion(
        easy_track,
        pml_funder,
        pml_dai_topup_factory,
        dai_token,
        [pml_funder],
        [10 * 10**18],
        unknown_person,
    )
    check_add_and_remove_recipient_with_voting(pml_dai_registry, helpers, ldo_holder, dao_voting)

    # 11. Add Lido Contributors Group DAI payment EVM script factory (ATC) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07
    create_and_enact_payment_motion(
        easy_track,
        atc_funder,
        atc_dai_topup_factory,
        dai_token,
        [atc_funder],
        [10 * 10**18],
        unknown_person,
    )
    check_add_and_remove_recipient_with_voting(atc_dai_registry, helpers, ldo_holder, dao_voting)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 11, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(tx)

    validate_permission_revoke_event(evs[0], permission)
    validate_permission_grantp_event(evs[1], permission, amount_limits())

    validate_evmscript_factory_removed_event(evs[2], lego_factory_old)

    validate_evmscript_factory_added_event(
        evs[3],
        EVMScriptFactoryAdded(
            factory_addr=lego_dai_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(lego_dai_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[4],
        EVMScriptFactoryAdded(
            factory_addr=lego_ldo_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(lego_ldo_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[5],
        EVMScriptFactoryAdded(
            factory_addr=rewards_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(rewards_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[6],
        EVMScriptFactoryAdded(
            factory_addr=rewards_add_recipient_factory,
            permissions=create_permissions(rewards_registry, "addRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[7],
        EVMScriptFactoryAdded(
            factory_addr=rewards_remove_recipient_factory,
            permissions=create_permissions(rewards_registry, "removeRecipient"),
        ),
    )
    validate_evmscript_factory_added_event(
        evs[8],
        EVMScriptFactoryAdded(
            factory_addr=rcc_dai_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(rcc_dai_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[9],
        EVMScriptFactoryAdded(
            factory_addr=pml_dai_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(pml_dai_registry, "updateSpentAmount")[2:],
        ),
    )
    validate_evmscript_factory_added_event(
        evs[10],
        EVMScriptFactoryAdded(
            factory_addr=atc_dai_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(atc_dai_registry, "updateSpentAmount")[2:],
        ),
    )


def _encode_calldata(signature, values):
    return "0x" + encode(signature, values).hex()


def create_and_enact_payment_motion(
    easy_track,
    trusted_caller,
    factory,
    token,
    recievers,
    transfer_amounts,
    stranger,
):
    agent = accounts.at("0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c", {"force": True})
    agent_balance_before = token.balanceOf(agent)
    recievers_balance_before = [token.balanceOf(reciever) for reciever in recievers]
    motions_before = easy_track.getMotions()

    recievers_addresses = [reciever.address for reciever in recievers]

    calldata = _encode_calldata("(address[],uint256[])", [recievers_addresses, transfer_amounts])

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    recievers_balance_after = [token.balanceOf(reciever) for reciever in recievers]
    for i in range(len(recievers)):
        assert recievers_balance_after[i] == recievers_balance_before[i] + transfer_amounts[i]

    agent_balance_after = token.balanceOf(agent)

    assert agent_balance_after == agent_balance_before - sum(transfer_amounts)


def create_and_enact_add_recipient_motion(
    easy_track,
    trusted_caller,
    registry,
    factory,
    recipient,
    title,
    stranger,
):
    recipients_count = len(registry.getAllowedRecipients())
    assert not registry.isRecipientAllowed(recipient)
    motions_before = easy_track.getMotions()

    calldata = _encode_calldata("(address,string)", [recipient.address, title])

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(registry.getAllowedRecipients()) == recipients_count + 1
    assert registry.isRecipientAllowed(recipient)


def create_and_enact_remove_recipient_motion(
    easy_track,
    trusted_caller,
    registry,
    factory,
    recipient,
    stranger,
):
    recipients_count = len(registry.getAllowedRecipients())
    assert registry.isRecipientAllowed(recipient)
    motions_before = easy_track.getMotions()

    calldata = _encode_calldata("(address)", [recipient.address])

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    motions = easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(registry.getAllowedRecipients()) == recipients_count - 1
    assert not registry.isRecipientAllowed(recipient)


eth = {
    "limit": 1_000 * (10**18),
    "address": ZERO_ADDRESS,
}

steth = {
    "limit": 1_000 * (10**18),
    "address": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
}

ldo = {
    "limit": 5_000_000 * (10**18),
    "address": "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",
}

dai = {
    "limit": 2_000_000 * (10**18),
    "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
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


def check_add_and_remove_recipient_with_voting(registry, helpers, ldo_holder, dao_voting):
    recipient_candidate = accounts[0]
    title = "Recipient"
    recipients_length_before = len(registry.getAllowedRecipients())

    assert not registry.isRecipientAllowed(recipient_candidate)

    call_script_items = [
        agent_forward(
            [
                (
                    registry.address,
                    registry.addRecipient.encode_input(recipient_candidate, title),
                )
            ]
        )
    ]
    vote_desc_items = ["Add recipient"]
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    vote_id = create_vote(vote_items, {"from": ldo_holder})[0]

    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )

    assert registry.isRecipientAllowed(recipient_candidate)
    assert len(registry.getAllowedRecipients()) == recipients_length_before + 1, 'Wrong whitelist length'

    call_script_items = [
        agent_forward(
            [
                (
                    registry.address,
                    registry.removeRecipient.encode_input(recipient_candidate),
                )
            ]
        )
    ]
    vote_desc_items = ["Remove recipient"]
    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    vote_id = create_vote(vote_items, {"from": ldo_holder})[0]

    helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=dao_voting,
        skip_time=3 * 60 * 60 * 24,
    )

    assert not registry.isRecipientAllowed(recipient_candidate)
    assert len(registry.getAllowedRecipients()) == recipients_length_before, 'Wrong whitelist length'
