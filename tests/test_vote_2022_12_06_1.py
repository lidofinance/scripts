"""
Tests for voting 15/11/2022.
"""

from scripts.vote_2022_12_06_1 import start_vote

from typing import Dict, List

from brownie import ZERO_ADDRESS
from brownie.network.transaction import TransactionReceipt
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op

from utils.config import (
    get_deployer_account,
    lido_dao_finance_address,
    lido_easytrack_evmscriptexecutor,
    ldo_token_address,
    dai_token_address,
    lido_dao_steth_address,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import (
    Payout,
    validate_token_payout_event,
)
from brownie.network.transaction import TransactionReceipt
from brownie import interface
from utils.config import (
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
        # 8: { return _amount <= 100_000 }
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


lego_factory_old = "0x648C8Be548F43eca4e482C0801Ebccccfb944931"
lego_dai_factory = "0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC"
lego_ldo_factory = "0x00caAeF11EC545B192f16313F53912E453c91458"
rewards_topup_factory = "0x85d703B2A4BaD713b596c647badac9A1e95bB03d"
rewards_add_recipient_factory = "0x1dCFc37719A99d73a0ce25CeEcbeFbF39938cF2C"
rewards_remove_recipient_factory = "0x00BB68a12180a8f7E20D8422ba9F81c07A19A79E"
rcc_dai_topup_factory = "0x84f74733ede9bFD53c1B3Ea96338867C94EC313e"
pml_dai_topup_factory = "0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD"
atc_dai_topup_factory = "0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07"
gas_refund_eth_topup_factory = "0x41F9daC5F89092dD6061E59578A2611849317dc8"


def test_vote(helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, bypass_events_decoding, easy_track, lido):

    old_factories = easy_track.getEVMScriptFactories()

    assert lego_factory_old in old_factories
    assert lego_dai_factory not in old_factories
    assert lego_ldo_factory not in old_factories
    assert rewards_topup_factory not in old_factories
    assert rewards_add_recipient_factory not in old_factories
    assert rewards_remove_recipient_factory not in old_factories
    assert rcc_dai_topup_factory not in old_factories
    assert pml_dai_topup_factory not in old_factories
    assert atc_dai_topup_factory not in old_factories
    assert gas_refund_eth_topup_factory not in old_factories

    # START VOTE
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 12, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return
