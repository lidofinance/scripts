"""
Voting 12/12/2023.

I. Replacing Jump Crypto with ChainLayer in Lido on Ethereum Oracle set
1. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for AccountingOracle on Lido on Ethereum to Agent
2. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum to Agent
3. Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from HashConsensus for AccountingOracle on Lido on Ethereum
4. Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum
5. Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to HashConsensus for AccountingOracle on Lido on Ethereum Oracle set
6. Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set

II. Deactivation of Jump Crypto and Anyblock Analytics node operators
7. deactivate the node operator named 'Jump Crypto' with id 1 in Curated Node Operator Registry
8. deactivate the node operator named ‘Anyblock Analytics' with id 12 in Curated Node Operator Registry

III. Replenishment of Lido Contributors Group multisigs with stETH
9. Transfer TBA stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
10. Transfer TBA stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
11. Transfer TBA stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956

IV. Updating the Easy Track setups to allow DAI USDT USDC payments for Lido Contributors Group
12. Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
13. Add CREATE_PAYMENTS_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 with single transfer limits of 1,000 ETH, 1,000 stETH, 5,000,000 LDO, 2,000,000 DAI, 2,000,000 USDC, 2,000,000 USDT
14. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
15. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
16. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
17. Add RCC stable top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4
18. Add PML stable top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D
19. Add ATC stable top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab

V. ET top up setups for stonks
"""

import time

from typing import Dict, Tuple, List
from brownie import interface, ZERO_ADDRESS
from brownie.network.transaction import TransactionReceipt
from utils.agent import agent_forward
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.finance import make_steth_payout
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.permissions import encode_permission_revoke, encode_permission_grant_p
from utils.permission_parameters import Param, SpecialArgumentID, encode_argument_value_if, ArgumentValue, Op
from utils.easy_track import add_evmscript_factory, create_permissions, remove_evmscript_factory
from configs.config_mainnet import DAI_TOKEN, LDO_TOKEN, LIDO


def amount_limits() -> List[Param]:
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


def encode_add_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def encode_remove_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_add_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def encode_remove_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_deactivate_node_operator(id: int) -> Tuple[str, str]:
    curated_sm = contracts.node_operators_registry
    return (curated_sm.address, curated_sm.deactivateNodeOperator.encode_input(id))


description = """
### Omnibus on-chain vote contains:

TBA
"""

EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5

MANAGE_MEMBERS_AND_QUORUM_ROLE = "0x66a484cf1a3c6ef8dfd59d24824943d2853a29d96f34a01271efc55774452a51"


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    jump_crypto_oracle_member = "0x1d0813bf088be3047d827d98524fbf779bc25f00"
    chain_layer_oracle_member = "0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf"

    rcc_multisig_address = "0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437"
    pml_multisig_address = "0x17F6b2C738a63a8D3A113a228cfd0b373244633D"
    atc_multisig_address = "0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956"

    rcc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xDc1A0C7849150f466F07d48b38eAA6cE99079f80")
    pml_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xDFfCD3BF14796a62a804c1B16F877Cf7120379dB")
    atc_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xe07305F43B11F230EaA951002F6a55a16419B707")

    call_script_items = [
        # I. Replacing Jump Crypto with ChainLayer in Lido on Ethereum Oracle set
        #
        # 1. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for AccountingOracle on Lido on Ethereum to Agent
        agent_forward(
            [
                (
                    contracts.hash_consensus_for_accounting_oracle.address,
                    contracts.hash_consensus_for_accounting_oracle.grantRole.encode_input(
                        MANAGE_MEMBERS_AND_QUORUM_ROLE, contracts.agent.address
                    ),
                )
            ]
        ),
        # 2. Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum to Agent
        agent_forward(
            [
                (
                    contracts.hash_consensus_for_validators_exit_bus_oracle.address,
                    contracts.hash_consensus_for_validators_exit_bus_oracle.grantRole.encode_input(
                        MANAGE_MEMBERS_AND_QUORUM_ROLE, contracts.agent.address
                    ),
                )
            ]
        ),
        # 3. Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from HashConsensus for AccountingOracle on Lido on Ethereum
        agent_forward(
            [
                encode_remove_accounting_oracle_member(
                    jump_crypto_oracle_member, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                )
            ],
        ),
        # 4. Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum
        agent_forward(
            [
                encode_remove_validators_exit_bus_oracle_member(
                    jump_crypto_oracle_member, HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM
                )
            ],
        ),
        # 5. Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to HashConsensus for AccountingOracle on Lido on Ethereum Oracle set
        agent_forward(
            [
                encode_add_accounting_oracle_member(
                    chain_layer_oracle_member, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM
                ),
            ]
        ),
        # 6. Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set
        agent_forward(
            [
                encode_add_validators_exit_bus_oracle_member(
                    chain_layer_oracle_member, HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM
                ),
            ]
        ),
        #
        # II. Deactivation of Jump Crypto and Anyblock Analytics node operators
        #
        # 7. deactivate the node operator named 'Jump Crypto' with id 1 in Curated Node Operator Registry
        agent_forward([encode_deactivate_node_operator(1)]),
        # 8. deactivate the node operator named ‘Anyblock Analytics' with id 12 in Curated Node Operator Registry
        agent_forward([encode_deactivate_node_operator(12)]),
        #
        # III. Replenishment of Lido Contributors Group multisigs with stETH
        #
        # 9. Transfer TBA stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437
        make_steth_payout(
            target_address=rcc_multisig_address,
            steth_in_wei=10**18,
            reference="Fund RCC multisig",
        ),
        # 10. Transfer TBA stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D
        make_steth_payout(
            target_address=pml_multisig_address,
            steth_in_wei=10**18,
            reference="Fund PML multisig",
        ),
        # 11. Transfer TBA stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956
        make_steth_payout(
            target_address=atc_multisig_address,
            steth_in_wei=10**18,
            reference="Fund ATC multisig",
        ),
        #
        # IV. Updating the Easy Track setups to allow DAI USDT USDC payments for Lido Contributors Group
        #
        # 12. Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977
        encode_permission_revoke(
            target_app=contracts.finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            revoke_from=EVM_SCRIPT_EXECUTOR,
        ),
        # 13. Add CREATE_PAYMENTS_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 with single transfer limits of 1,000 ETH, 1,000 stETH, 5,000,000 LDO, 2,000,000 DAI, 2,000,000 USDC, 2,000,000 USDT
        encode_permission_grant_p(
            target_app=contracts.finance,
            permission_name="CREATE_PAYMENTS_ROLE",
            grant_to=EVM_SCRIPT_EXECUTOR,
            params=amount_limits(),
        ),
        # 14. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
        remove_evmscript_factory("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e"),
        # 15. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
        remove_evmscript_factory("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD"),
        # 16. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
        remove_evmscript_factory("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07"),
        # 17. Add RCC stable top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4
        add_evmscript_factory(
            factory="0x75bDecbb6453a901EBBB945215416561547dfDD4",
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rcc_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
        # 18. Add PML stable top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D
        add_evmscript_factory(
            factory="0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D",
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(pml_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
        # 19. Add ATC stable top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab
        add_evmscript_factory(
            factory="0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab",
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(atc_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    ]

    vote_desc_items = [
        "1) Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for AccountingOracle on Lido on Ethereum to Agent",
        "2) Grant MANAGE_MEMBERS_AND_QUORUM_ROLE on HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum to Agent",
        "3) Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from HashConsensus for AccountingOracle on Lido on Ethereum",
        "4) Remove the oracle member named 'Jump Crypto' with address 0x1d0813bf088be3047d827d98524fbf779bc25f00 from HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum",
        "5) Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to HashConsensus for AccountingOracle on Lido on Ethereum Oracle set",
        "6) Add oracle member named 'ChainLayer' with address 0xc79F702202E3A6B0B6310B537E786B9ACAA19BAf to HashConsensus for ValidatorsExitBusOracle on Lido on Ethereum Oracle set",
        "7) Deactivate the node operator named 'Jump Crypto' with id 1 in Curated Node Operator Registry",
        "8) Deactivate the node operator named ‘Anyblock Analytics' with id 12 in Curated Node Operator Registry",
        "9) Transfer TBA stETH to RCC 0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437",
        "10) Transfer TBA stETH to PML 0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
        "11) Transfer TBA stETH to ATC 0x9B1cebF7616f2BC73b47D226f90b01a7c9F86956",
        "12) Remove CREATE_PAYMENTS_ROLE from EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",
        "13) Add CREATE_PAYMENTS_ROLE to EVMScriptExecutor 0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977 with single transfer limits of 1,000 ETH, 1,000 stETH, 5,000,000 LDO, 2,000,000 DAI, 2,000,000 USDC, 2,000,000 USDT",
        "14) Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track",
        "15) Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track",
        "16) Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track",
        "17) Add RCC stable top up EVM script factory 0x75bDecbb6453a901EBBB945215416561547dfDD4",
        "18) Add PML stable top up EVM script factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D",
        "19) Add ATC stable top up EVM script factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab",
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
