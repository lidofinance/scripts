"""
todo: change title
Voting 31/10/2023.

"""

import time

from typing import Dict, List
from brownie.network.transaction import TransactionReceipt
from brownie import interface, ZERO_ADDRESS
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.agent import agent_forward
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.easy_track import add_evmscript_factory, create_permissions, remove_evmscript_factory
from utils.permission_parameters import Param, SpecialArgumentID, Op, ArgumentValue, encode_argument_value_if
from utils.permissions import encode_permission_revoke, encode_permission_grant_p

from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    get_priority_fee,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    LIDO,
    LDO_TOKEN,
    DAI_TOKEN,
    USDC_TOKEN,
    USDT_TOKEN
)

# todo: change description
description = """
### Omnibus on-chain vote contains 3 motions:

1. Switch off TopUp ETs for RCC PML ACT
2. Switch on TopUpStable ETs for RCC PML ACT

"""

eth = {
    "limit": 1_000 * (10**18),
    "address": ZERO_ADDRESS,
}

steth = {
    "limit": 1_000 * (10**18),
    "address": LIDO,
}

ldo = {
    "limit": 5_000_000 * (10**18),
    "address": LDO_TOKEN,
}

dai = {
    "limit": 2_000_000 * (10**18),
    "address": DAI_TOKEN,
}

usdc = {
    "limit": 2_000_000 * (10**18),
    "address": USDC_TOKEN,
}

usdt = {
    "limit": 2_000_000 * (10**18),
    "address": USDT_TOKEN,
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
        # 10: (_token == USDT)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdt["address"])),
        # 11: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdt["limit"])),
        # 12: else if (13) then (14) else (15)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=13, success=14, failure=15),
        ),
        # 13: (_token == USDC)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdc["address"])),
        # 14: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdc["limit"])),
        # 15: else if (16) then (17) else (18)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=16, success=17, failure=18),
        ),
        # 16: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth["address"])),
        # 17: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth["limit"])),
        # 18: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    rcc_dai_topup_factory_old = interface.IEVMScriptFactory("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_dai_topup_factory_old = interface.IEVMScriptFactory("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_dai_topup_factory_old = interface.IEVMScriptFactory("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")

    # todo: change addresses
    rcc_stable_topup_factory = interface.TopUpAllowedRecipients("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_stable_topup_factory = interface.TopUpAllowedRecipients("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_stable_topup_factory = interface.TopUpAllowedRecipients("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")

    # addresses stay same
    rcc_stable_registry = interface.AllowedRecipientRegistry("0xDc1A0C7849150f466F07d48b38eAA6cE99079f80")
    pml_stable_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    atc_stable_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")

    call_script_items = [

        # 1. Revoke role CREATE_PAYMENTS_ROLE from EVM script executor
        encode_permission_revoke(
            target_app=contracts.finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            revoke_from=EASYTRACK_EVMSCRIPT_EXECUTOR,
        ),
        # 2. Grant role CREATE_PAYMENTS_ROLE to EasyTrack EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
        # with limits: 1000 ETH, 1000 stETH, 5M LDO, 2M DAI, 2M USTD, 2M USDC
        encode_permission_grant_p(
            target_app=contracts.finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
            params=amount_limits(),
        ),        

        ## 3. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
        remove_evmscript_factory(factory=rcc_dai_topup_factory_old),
        ## 4. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
        remove_evmscript_factory(factory=pml_dai_topup_factory_old),
        ## 5. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
        remove_evmscript_factory(factory=atc_dai_topup_factory_old),

        # todo: change addresses
        ## 6. Add RCC stable top up EVM script factory 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e to Easy Track
        add_evmscript_factory(
            factory=rcc_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rcc_stable_registry, "updateSpentAmount")[2:],
        ),
        ## 7. Add PML stable top up EVM script factory 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD to Easy Track
        add_evmscript_factory(
            factory=pml_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(pml_stable_registry, "updateSpentAmount")[2:],
        ),
        ## 8. Add ATC stable top up EVM script factory 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 to Easy Track
        add_evmscript_factory(
            factory=atc_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(atc_stable_registry, "updateSpentAmount")[2:],
        )
    ]

    # todo: change addresses in 6,7,8 strings
    vote_desc_items = [
        f"1) Revoke role CREATE_PAYMENTS_ROLE from EVM script executor",
        f"2) Grant role CREATE_PAYMENTS_ROLE to EasyTrack EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",
        f"3) Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track",
        f"4) Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track",
        f"5) Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track",
        f"6) Add RCC stable top up EVM script factory 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e to Easy Track",
        f"7) Add PML stable top up EVM script factory 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD to Easy Track",
        f"8) Add ATC stable top up EVM script factory 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 to Easy Track",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

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
