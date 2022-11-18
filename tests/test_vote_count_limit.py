from brownie import accounts, interface
from brownie.network.transaction import TransactionReceipt
from utils.test.tx_tracing_helpers import *
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.permissions import encode_permission_revoke, encode_permission_grant_p
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op
from utils.finance import ZERO_ADDRESS

from utils.config import (
    get_deployer_account,
    lido_dao_finance_address,
    lido_easytrack_evmscriptexecutor,
    ldo_token_address,
    dai_token_address,
    lido_dao_steth_address,
)

factories_to_add = 9

eth = {
    'limit': 1_000 * (10 ** 18),
    'address': ZERO_ADDRESS,
}

steth = {
    'limit': 1_000 * (10 ** 18),
    'address': lido_dao_steth_address,
}

ldo = {
    'limit': 5_000_000 * (10 ** 18),
    'address': ldo_token_address,
}

dai = {
    'limit': 2_000_000 * (10 ** 18),
    'address': dai_token_address,
}

def amount_limits() -> List[Param]:
    """ Here we want to build such permissions that checks the _token and _amount pairs
        on each Finance#newImmediatePayment launch.

        Arguments provided from that method:
        `authP(CREATE_PAYMENTS_ROLE, _arr(_token, _receiver, _amount, MAX_UINT256, uint256(1), getTimestamp()))`

        See https://etherscan.io/address/0x836835289a2e81b66ae5d95b7c8dbc0480dcf9da#code#L1549
    """
    token_arg_index = 0
    amount_arg_index = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE,
              encode_argument_value_if(condition=1, success=2, failure=3)),
        # 1: (_token == LDO)
        Param(token_arg_index, Op.EQ, ArgumentValue(ldo['address'])),
        # 2: { return _amount <= 5_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(ldo['limit'])),
        # 3: else if (4) then (5) else (6)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE,
              encode_argument_value_if(condition=4, success=5, failure=6)),
        # 4: (_token == ETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(eth['address'])),
        # 5: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(eth['limit'])),
        # 6: else if (7) then (8) else (9)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE,
              encode_argument_value_if(condition=7, success=8, failure=9)),
        # 7: (_token == DAI)
        Param(token_arg_index, Op.EQ, ArgumentValue(dai['address'])),
        # 8: { return _amount <= 100_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(dai['limit'])),
        # 9: else if (10) then (11) else (12)
        Param(SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE,
              encode_argument_value_if(condition=10, success=11, failure=12)),
        # 10: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth['address'])),
        # 11: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth['limit'])),
        # 12: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0))
    ]


def generate_and_start_vote():
    reward_programs_registry = interface.RewardProgramsRegistry(
        "0xfCaD241D9D2A2766979A2de208E8210eDf7b7D4F"
    )
    finance = interface.Finance(lido_dao_finance_address)
    evmscriptexecutor = lido_easytrack_evmscriptexecutor
    vote_desc_items = ['remove rights', 'add rights']    

    call_script_items = [
        encode_permission_revoke(
            target_app=finance,
            permission_name='CREATE_PAYMENTS_ROLE',
            revoke_from=evmscriptexecutor
        ),

        # 5. Grant role CREATE_PAYMENTS_ROLE to Easy Track EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
        # with limits: 1000 ETH, 1000 stETH, 5M LDO, 100K DAI
        encode_permission_grant_p(
            target_app=finance,
            permission_name='CREATE_PAYMENTS_ROLE',
            grant_to=evmscriptexecutor,
            params=amount_limits()
        )
        ]
    
    for index in range(factories_to_add):
        call_script_items.append(
            add_evmscript_factory(
                factory=accounts[index].address,
                permissions=create_permissions(
                    reward_programs_registry,
                    "addRewardProgram" if ((index % 2) == 0) else "removeRewardProgram",
                ),
            )
        )
        vote_desc_items.append(index)

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, True) and create_vote(
        vote_items, {"from": get_deployer_account()}
    )


def test_vote_count_limit(dao_voting, helpers, bypass_events_decoding):
    (vote_id, _) = generate_and_start_vote()

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    if not bypass_events_decoding:
        assert (
            count_vote_items_by_events(tx, dao_voting) == (2 + factories_to_add)
        ), "Incorrect voting items count"

    pass
