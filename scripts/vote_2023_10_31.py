"""
Voting 31/10/2023.

I. Add USDT and USDC to EVMScriptExecutor permissions
1. Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
2. Add CREATE_PAYMENTS_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 with single transfer limits of 1,000 ETH, 1,000 stETH, 5,000,000 LDO, 2,000,000 DAI, 2,000,000 USDC, 2,000,000 USDT

II. Switch ET DAI top-up setups into ET Stables setups for RCC PML ATC
3. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
4. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
5. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
6. Add RCC stable top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4 
7. Add PML stable top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D
8. Add ATC stable top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab

III. stETH transfers to  RCC PML ATC
9. Transfer TBA stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
10. Transfer TBA stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
11. Transfer TBA stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956

"""

import time

from typing import Dict, List
from brownie.network.transaction import TransactionReceipt
from brownie import interface, ZERO_ADDRESS
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.easy_track import add_evmscript_factory, create_permissions, remove_evmscript_factory
from utils.permission_parameters import Param, SpecialArgumentID, Op, ArgumentValue, encode_argument_value_if
from utils.permissions import encode_permission_revoke, encode_permission_grant_p
from utils.finance import make_steth_payout

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

description = """
### Omnibus on-chain vote contains:

Two motions to **optimize [Lido Contributors Group's multisigs](https://research.lido.fi/t/ref-introducing-the-lido-contributors-group-including-pool-maintenance-labs-and-argo-technology-consulting/3069) funding operations by [upgrading the Easy Track setup](https://research.lido.fi/t/updating-the-easy-track-setups-to-allow-dai-usdt-usdc-payments-for-lido-contributors-group/5738)**, allowing it to work with DAI, USDT, USDC instead of DAI-only.

1. Grant to `EVMScripExecutor` the permissions to transfer USDT and USDC in addition to current ETH, stETH, LDO, and DAI. Items 1,2.
2. Switch the Easy Track DAI top-up setup to the Easy Track DAI, USDT, and USDC top-up setup for all [Lido Contributors Group multisigs](https://research.lido.fi/t/ref-introducing-the-lido-contributors-group-including-pool-maintenance-labs-and-argo-technology-consulting/3069) ([RCC](https://app.safe.global/settings/setup?safe=eth:0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437), [PML](https://app.safe.global/settings/setup?safe=eth:0x17F6b2C738a63a8D3A113a228cfd0b373244633D), and [ATC](https://app.safe.global/settings/setup?safe=eth:0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956)). Items 3-8.

The new version of contracts was [audited by Oxorio](LINK_TO_AUDIT).

And last motion is

3. **stETH transfer to the [Lido Contributor's Group multisigs](https://research.lido.fi/t/ref-introducing-the-lido-contributors-group-including-pool-maintenance-labs-and-argo-technology-consulting/3069)** ([RCC](https://app.safe.global/settings/setup?safe=eth:0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437), [PML](https://app.safe.global/settings/setup?safe=eth:0x17F6b2C738a63a8D3A113a228cfd0b373244633D), and [ATC](https://app.safe.global/settings/setup?safe=eth:0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956)), as previously [requested on the forum](https://research.lido.fi/t/lido-v2-may-1-2023-december-31-2023-lido-ongoing-grant-request/4476/11). Items 9-11.
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
    "limit": 2_000_000 * (10**6),
    "address": USDC_TOKEN,
}

usdt = {
    "limit": 2_000_000 * (10**6),
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

    rcc_stable_topup_factory = interface.TopUpAllowedRecipients("0x75bDecbb6453a901EBBB945215416561547dfDD4")
    pml_stable_topup_factory = interface.TopUpAllowedRecipients("0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D")
    atc_stable_topup_factory = interface.TopUpAllowedRecipients("0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab")

    rcc_stable_registry = interface.AllowedRecipientRegistry("0xDc1A0C7849150f466F07d48b38eAA6cE99079f80")
    pml_stable_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    atc_stable_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")

    rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
    pml_multisig_address = "0x17F6b2C738a63a8D3A113a228cfd0b373244633D"
    atc_multisig_address = "0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956"

    call_script_items = [
        # I. Add USDT and USDC to EVMScriptExecutor permissions
        # 1. Revoke role CREATE_PAYMENTS_ROLE from EVM script executor
        encode_permission_revoke(
            target_app=contracts.finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            revoke_from=EASYTRACK_EVMSCRIPT_EXECUTOR,
        ),
        # 2. Grant role CREATE_PAYMENTS_ROLE to EasyTrack EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
        # with limits: 1000 ETH, 1000 stETH, 5M LDO, 2M DAI, 2M USDT, 2M USDC
        encode_permission_grant_p(
            target_app=contracts.finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            grant_to=EASYTRACK_EVMSCRIPT_EXECUTOR,
            params=amount_limits(),
        ),

        # II. Switch ET DAI top-up setups into ET Stables setups for RCC PML ATC
        ## 3. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
        remove_evmscript_factory(factory=rcc_dai_topup_factory_old),
        ## 4. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
        remove_evmscript_factory(factory=pml_dai_topup_factory_old),
        ## 5. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
        remove_evmscript_factory(factory=atc_dai_topup_factory_old),
        ## 6. Add RCC stable top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4 to Easy Track
        add_evmscript_factory(
            factory=rcc_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rcc_stable_registry, "updateSpentAmount")[2:],
        ),
        ## 7. Add PML stable top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D to Easy Track
        add_evmscript_factory(
            factory=pml_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(pml_stable_registry, "updateSpentAmount")[2:],
        ),
        ## 8. Add ATC stable top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab to Easy Track
        add_evmscript_factory(
            factory=atc_stable_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(atc_stable_registry, "updateSpentAmount")[2:],
        ),

        # III. stETH transfers to RCC PML ATC
        # 9. Transfer TBA stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_steth_payout(
            target_address=rcc_multisig_address,
            steth_in_wei=1 * (10**18),
            reference="Fund RCC multisig"
        ),
        # 10. Transfer TBA stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
        make_steth_payout(
            target_address=pml_multisig_address,
            steth_in_wei=1 * (10**18),
            reference="Fund PML multisig"
        ),
        # 11. Transfer TBA stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956
        make_steth_payout(
            target_address=atc_multisig_address,
            steth_in_wei=1 * (10**18),
            reference="Fund ATC multisig"
        )
    ]

    vote_desc_items = [
        f"1) Revoke role CREATE_PAYMENTS_ROLE from EVM script executor",
        f"2) Grant role CREATE_PAYMENTS_ROLE to EasyTrack EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",
        f"3) Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track",
        f"4) Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track",
        f"5) Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track",
        f"6) Add RCC stable top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4 to Easy Track",
        f"7) Add PML stable top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D to Easy Track",
        f"8) Add ATC stable top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab to Easy Track",
        f"9) Transfer TBA stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
        f"10) Transfer TBA stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
        f"11) Transfer TBA stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956"
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
