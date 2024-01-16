"""
Voting 16/01/2024.

I. Replace Jump Crypto with ChainLayer in Lido on Ethereum Oracle set
1. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for AccountingOracle on Lido on Ethereum to Agent
2. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum to Agent
3. Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from
    HashConsensus for AccountingOracle on Lido on Ethereum
4. Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from
    HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum
5. Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to
    HashConsensus for AccountingOracle on Lido on Ethereum Oracle set
6. Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to
    HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set

II. Deactivate Jump Crypto and Anyblock Analytics node operators
7. Deactivate the node operator named 'Jump Crypto' with id 1 in Curated Node Operators Registry
8. Deactivate the node operator named 'Anyblock Analytics' with id 12 in Curated Node Operators Registry

III. Change the on-chain name of node operator with id 20 from 'HashQuark' to 'HashKey Cloud'
9. Change the on-chain name of node operator with id 20 from 'HashQuark' to 'HashKey Cloud'

IV. Add stETH factories for PML, ATC, RCC
10. Add RCC stETH top up EVM script factory 0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35
11. Add PML stETH top up EVM script factory 0xc5527396DDC353BD05bBA578aDAa1f5b6c721136
12. Add ATC stETH top up EVM script factory 0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9

V. Upgrade the Easy Track setups to allow DAI USDT USDC payments for Lido Contributors Group
13. Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
14. Add CREATE_PAYMENTS_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 with single
    transfer limits of 1,000 ETH, 1,000 stETH, 5,000,000 LDO, 2,000,000 DAI, 2,000,000 USDC, 2,000,000 USDT
15. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
16. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
17. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
18. Add RCC stables top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4
19. Add PML stables top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D
20. Add ATC stables top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab

VI. Upgrade the Easy Track setups to allow DAI USDT USDC payments for LEGO
21. Remove LEGO DAI top up EVM script factory (old ver) 0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC from Easy Track
22. Add LEGO stables top up EVM script factory 0x6AB39a8Be67D9305799c3F8FdFc95Caf3150d17c

VII. Decrease the limit for Easy Track TRP setup to 9,178,284.42 LDO
23. Set spend amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 0
24. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 9178284.42 * 10 ** 18
"""

import time

from typing import Dict, List, NamedTuple
from brownie import ZERO_ADDRESS, Wei
from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.permissions import encode_permission_revoke, encode_permission_grant_p, encode_oz_grant_role
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op
from utils.easy_track import (
    add_evmscript_factory,
    remove_evmscript_factory,
)
from configs.config_mainnet import DAI_TOKEN, LDO_TOKEN, LIDO, USDC_TOKEN, USDT_TOKEN
from utils.node_operators import encode_set_node_operator_name, deactivate_node_operator
from utils.allowed_recipients_registry import (
    update_spent_amount,
    set_limit_parameters,
    create_top_up_allowed_recipient_permission,
)
from utils.oracle import (
    add_accounting_oracle_member,
    remove_accounting_oracle_member,
    add_validators_exit_bus_oracle_member,
    remove_validators_exit_bus_oracle_member,
)


class TokenLimit(NamedTuple):
    address: str
    limit: int


ldo_limit = TokenLimit(LDO_TOKEN, 5_000_000 * (10**18))
eth_limit = TokenLimit(ZERO_ADDRESS, 1_000 * 10**18)
steth_limit = TokenLimit(LIDO, 1_000 * (10**18))
dai_limit = TokenLimit(DAI_TOKEN, 2_000_000 * (10**18))
usdc_limit = TokenLimit(USDC_TOKEN, 2_000_000 * (10**6))
usdt_limit = TokenLimit(USDT_TOKEN, 2_000_000 * (10**6))


# The higher the token in the list, the less gas will be used to evaluate the parameter logic
# by the ACL.evalParam() method, and the cheaper the transfer from the Finance contract will be.
# The optimal gas strategy is:  tokens that are transferred often, then others must be at the top of the list.
# The current order is the following:
# 1. stETH
# 2. DAI
# 3. LDO
# 4. USDC
# 5. USDT
# 6. ETH
def amount_limits() -> List[Param]:
    token_arg_index = 0
    amount_arg_index = 2

    return [
        # 0: if (1) then (2) else (3)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=1, success=2, failure=3)
        ),
        # 1: (_token == stETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(steth_limit.address)),
        # 2: { return _amount <= 1_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(steth_limit.limit)),
        #
        # 3: else if (4) then (5) else (6)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=4, success=5, failure=6)
        ),
        # 4: (_token == DAI)
        Param(token_arg_index, Op.EQ, ArgumentValue(dai_limit.address)),
        # 5: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(dai_limit.limit)),
        #
        # 6: else if (7) then (8) else (9)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID, Op.IF_ELSE, encode_argument_value_if(condition=7, success=8, failure=9)
        ),
        # 7: (_token == LDO)
        Param(token_arg_index, Op.EQ, ArgumentValue(ldo_limit.address)),
        # 8: { return _amount <= 5_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(ldo_limit.limit)),
        #
        # 9: else if (10) then (11) else (12)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=10, success=11, failure=12),
        ),
        # 10: (_token == USDC)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdc_limit.address)),
        # 11: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdc_limit.limit)),
        #
        # 12: else if (13) then (14) else (15)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=13, success=14, failure=15),
        ),
        # 13: (_token == USDT)
        Param(token_arg_index, Op.EQ, ArgumentValue(usdt_limit.address)),
        # 14: { return _amount <= 2_000_000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(usdt_limit.limit)),
        #
        # 15: else if (16) then (17) else (18)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=16, success=17, failure=18),
        ),
        # 16: (_token == ETH)
        Param(token_arg_index, Op.EQ, ArgumentValue(eth_limit.address)),
        # 17: { return _amount <= 1000 }
        Param(amount_arg_index, Op.LTE, ArgumentValue(eth_limit.limit)),
        #
        # 18: else { return false }
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]


description = """
1. **Replace Jump Crypto with ChainLayer in Lido on Ethereum Oracle set**. [Snapshot vote](https://snapshot.org/#/lido-snapshot.eth/proposal/0x29a1106ab03bfc146f324cf194f13119ae172d92a031ceb35ea37bd928c10577). Items 1-6.

2. **Deactivate node operators** Jump Crypto (id 1) and Anyblock Analytics (id 12) in Curated Node Operators Registry. Proposed [on the forum](https://research.lido.fi/t/disable-inactive-node-operators-anyblock-analytics-jump-crypto-in-curated-node-operator-registry/6077). Items 7,8.

3. **Rename node operator** HashQuark (id 20) to HashKey Cloud. Requested [on the forum](https://research.lido.fi/t/node-operator-registry-name-reward-address-change/4170/20). Item 9.

4. **Add the stETH factories** to enable [Lido Contributors Group multisigs](https://research.lido.fi/t/ref-introducing-the-lido-contributors-group-including-pool-maintenance-labs-and-argo-technology-consulting/3069) ([RCC](https://app.safe.global/settings/setup?safe=eth:0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437), [PML](https://app.safe.global/settings/setup?safe=eth:0x17F6b2C738a63a8D3A113a228cfd0b373244633D), and [ATC](https://app.safe.global/settings/setup?safe=eth:0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956)) funding in stETH via Easy Track as proposed [on the forum](https://research.lido.fi/t/egg-st2024-v1-lido-contributors-group-request-for-grant-funding-to-advance-goose-goals/6054/13). Items 10-12.

5. **Upgrade the Easy Track setups to allow funding not only in DAI but also in USDT and USDC**. The new version of contracts was [audited by Oxorio](https://github.com/lidofinance/audits/blob/main/Oxorio%20Lido%20Easy%20Track%20Smart%20Contracts%20Security%20Audit%20Report%2010-2023.pdf)
The upgrade includes:
    - Add `EVMScripExecutor` the permissions to transfer USDT and USDC with a single transfer limit of 2M in addition to current permissions. Items 13,14.
    - Switch the DAI top-up setup to the DAI, USDT, and USDC top-up setup for all [Lido Contributors Group multisigs](https://research.lido.fi/t/ref-introducing-the-lido-contributors-group-including-pool-maintenance-labs-and-argo-technology-consulting/3069) ([RCC](https://app.safe.global/settings/setup?safe=eth:0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437), [PML](https://app.safe.global/settings/setup?safe=eth:0x17F6b2C738a63a8D3A113a228cfd0b373244633D), and [ATC](https://app.safe.global/settings/setup?safe=eth:0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956)). Proposed [on the forum](https://research.lido.fi/t/updating-the-easy-track-setups-to-allow-dai-usdt-usdc-payments-for-lido-contributors-group/5738). Items 15-20.
    - Switch the DAI top-up setup to the DAI, USDT, and USDC top-up setup for [LEGO multisig](https://app.safe.global/settings/setup?safe=eth:0x12a43b049A7D330cB8aEAB5113032D18AE9a9030). Proposed [on the forum](https://research.lido.fi/t/updating-the-easy-track-setup-for-lego/6344). Items 21,22.

6. **Decrease the Easy Track limit for** [TRP multisig](https://app.safe.global/settings/setup?safe=eth:0x834560F580764Bc2e0B16925F8bF229bb00cB759) as recommended by the TRP committee [here](https://research.lido.fi/t/request-to-authorise-a-22m-ldo-ceiling-for-a-four-year-contributor-token-reward-plan-trp/3833/23). Items 23,24.
"""


HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    vote_desc_items, call_script_items = zip(
        #
        # I. Replace Jump Crypto with ChainLayer in Lido on Ethereum Oracle set
        #
        (
            "1) Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for AccountingOracle on Lido on Ethereum to Agent",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.hash_consensus_for_accounting_oracle,
                        role_name="MANAGE_MEMBERS_AND_QUORUM_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "2) Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum to Agent",
            agent_forward(
                [
                    encode_oz_grant_role(
                        contract=contracts.hash_consensus_for_validators_exit_bus_oracle,
                        role_name="MANAGE_MEMBERS_AND_QUORUM_ROLE",
                        grant_to=contracts.agent,
                    )
                ]
            ),
        ),
        (
            "3) Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from "
            + "HashConsensus for AccountingOracle on Lido on Ethereum",
            agent_forward(
                [
                    remove_accounting_oracle_member(
                        "0x1d0813bf088be3047d827d98524fbf779bc25f00", HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    )
                ],
            ),
        ),
        (
            "4) Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from "
            + "HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum",
            agent_forward(
                [
                    remove_validators_exit_bus_oracle_member(
                        "0x1d0813bf088be3047d827d98524fbf779bc25f00",
                        HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM,
                    )
                ],
            ),
        ),
        (
            "5) Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to "
            + "HashConsensus for AccountingOracle on Lido on Ethereum Oracle set",
            agent_forward(
                [
                    add_accounting_oracle_member(
                        "0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf", HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                    ),
                ]
            ),
        ),
        (
            "6) Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to "
            + "HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set",
            agent_forward(
                [
                    add_validators_exit_bus_oracle_member(
                        "0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf",
                        HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM,
                    ),
                ]
            ),
        ),
        #
        # II. Deactivate Jump Crypto and Anyblock Analytics node operators
        #
        (
            "7) Deactivate the node operator named 'Jump Crypto' with id 1 in Curated Node Operators Registry",
            agent_forward([deactivate_node_operator(1)]),
        ),
        (
            "8) Deactivate the node operator named 'Anyblock Analytics' with id 12 in Curated Node Operators Registry",
            agent_forward([deactivate_node_operator(12)]),
        ),
        #
        # III. Change the on-chain name of node operator with id 20 from 'HashQuark' to 'HashKey Cloud'
        #
        (
            "9) Change the on-chain name of node operator with id 20 from 'HashQuark' to 'HashKey Cloud'",
            agent_forward(
                [
                    encode_set_node_operator_name(
                        id=20, name="HashKey Cloud", registry=contracts.node_operators_registry
                    ),
                ]
            ),
        ),
        #
        # IV. Add stETH factories for PML, ATC, RCC
        #
        (
            "10) Add RCC stETH top up EVM script factory 0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35",
            add_evmscript_factory(
                factory="0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="0xAAC4FcE2c5d55D1152512fe5FAA94DB267EE4863"
                ),
            ),
        ),
        (
            "11) Add PML stETH top up EVM script factory 0xc5527396DDC353BD05bBA578aDAa1f5b6c721136",
            add_evmscript_factory(
                factory="0xc5527396DDC353BD05bBA578aDAa1f5b6c721136",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="0x7b9B8d00f807663d46Fb07F87d61B79884BC335B"
                ),
            ),
        ),
        (
            "12) Add ATC stETH top up EVM script factory 0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9",
            add_evmscript_factory(
                factory="0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="0xd3950eB3d7A9B0aBf8515922c0d35D13e85a2c91"
                ),
            ),
        ),
        #
        # V. Upgrade the Easy Track setups to allow DAI USDT USDC payments for Lido Contributors Group
        #
        (
            "13) Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",
            encode_permission_revoke(
                target_app=contracts.finance,
                permission_name="CREATE_PAYMENTS_ROLE",
                revoke_from="0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",
            ),
        ),
        (
            "14) Add CREATE_PAYMENTS_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 with single "
            + "transfer limits of 1,000 ETH, 1,000 stETH, 5,000,000 LDO, 2,000,000 DAI, 2,000,000 USDC, 2,000,000 USDT",
            encode_permission_grant_p(
                target_app=contracts.finance,
                permission_name="CREATE_PAYMENTS_ROLE",
                grant_to="0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",
                params=amount_limits(),
            ),
        ),
        (
            "15) Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track",
            remove_evmscript_factory("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e"),
        ),
        (
            "16) Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track",
            remove_evmscript_factory("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD"),
        ),
        (
            "17) Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track",
            remove_evmscript_factory("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07"),
        ),
        (
            "18) Add RCC stables top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4",
            add_evmscript_factory(
                factory="0x75bDecbb6453a901EBBB945215416561547dfDD4",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="0xDc1A0C7849150f466F07d48b38eAA6cE99079f80"
                ),
            ),
        ),
        (
            "19) Add PML stables top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D",
            add_evmscript_factory(
                factory="0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB"
                ),
            ),
        ),
        (
            "20) Add ATC stables top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab",
            add_evmscript_factory(
                factory="0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="0xe07305F43B11F230EaA951002F6a55a16419B707"
                ),
            ),
        ),
        #
        # VI. Upgrade the Easy Track setups to allow DAI USDT USDC payments for LEGO
        #
        (
            "21) Remove LEGO DAI top up EVM script factory (old ver) 0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC from Easy Track",
            remove_evmscript_factory(factory="0x0535a67ea2D6d46f85fE568B7EaA91Ca16824FEC"),
        ),
        (
            "22) Add LEGO stables top up EVM script factory 0x6AB39a8Be67D9305799c3F8FdFc95Caf3150d17c",
            add_evmscript_factory(
                factory="0x6AB39a8Be67D9305799c3F8FdFc95Caf3150d17c",
                permissions=create_top_up_allowed_recipient_permission(
                    registry_address="0xb0FE4D300334461523D9d61AaD90D0494e1Abb43"
                ),
            ),
        ),
        #
        # VII.Decrease the limit for Easy Track TRP setup to 9,178,284.42 LDO
        #
        (
            "23) Set spent amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 0",
            agent_forward(
                [update_spent_amount(spent_amount=0, registry_address="0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8")]
            ),
        ),
        (
            "24) Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 9178284.42 * 10 ** 18",
            agent_forward(
                [
                    set_limit_parameters(
                        limit=Wei("9178284.42 ether"),
                        period_duration_months=12,
                        registry_address="0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8",
                    ),
                ]
            ),
        ),
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

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
