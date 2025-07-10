"""
I. PML, ATC, RCC ET Factories Removal
1. Remove PML stablecoins factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
2. Remove PML stETH factory 0xc5527396DDC353BD05bBA578aDAa1f5b6c721136 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
3. Remove ATC stablecoins factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
4. Remove ATC stETH factory 0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
5. Remove RCC stablecoins factory 0x75bDecbb6453a901EBBB945215416561547dfDD4 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea
6. Remove RCC stETH factory 0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea

II. Kyber Oracle Rotation
7. Remove oracle set member with address 0xA7410857ABbf75043d61ea54e07D57A6EB6EF186 from HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288 for AccountingOracle 0x852deD011285fe67063a08005c71a85690503Cee
8. Remove oracle set member with address 0xA7410857ABbf75043d61ea54e07D57A6EB6EF186 from HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a for ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e
9. Remove oracle set member with address 0xA7410857ABbf75043d61ea54e07D57A6EB6EF186 from CSHashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4 for CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB
10. Add oracle set member with address 0x4118dad7f348a4063bd15786c299de2f3b1333f3 to HashConsensus 0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288 for AccountingOracle 0x852deD011285fe67063a08005c71a85690503Cee
11. Add oracle set member with address 0x4118dad7f348a4063bd15786c299de2f3b1333f3 to HashConsensus 0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a for ValidatorsExitBusOracle 0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e
12. Add oracle set member with address 0x4118dad7f348a4063bd15786c299de2f3b1333f3 to CSHashConsensus 0x71093efF8D8599b5fA340D665Ad60fA7C80688e4 for CSFeeOracle 0x4D4074628678Bd302921c20573EEa1ed38DdF7FB

III. CSM Parameters Change
13. Change stakeShareLimit from 200 BP to 300 BP and priorityExitShareThreshold from 250 to 375 on Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999 for CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F
14. Grant MODULE_MANAGER_ROLE on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F to Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
15. Reduce keyRemovalCharge from 0.02 to 0 ETH on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F
16. Revoke MODULE_MANAGER_ROLE on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c

IV. CS Verifier rotation
17. Revoke VERIFIER_ROLE role on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F from old CS Verifier 0x0c345dFa318f9F4977cdd4f33d80F9D0ffA38e8B (addresses to be verified and checked)
18. Grant VERIFIER_ROLE role on CSModule 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F to new CS Verifier 0xeC6Cc185f671F627fb9b6f06C8772755F587b05d (addresses to be verified and checked)
"""

import importlib
import utils.voting
importlib.reload(utils.voting)

import time
from typing import Dict, Tuple, Optional
from brownie import interface
from brownie.network.transaction import TransactionReceipt

from utils.agent import agent_forward
from utils.dual_governance import submit_proposals
from utils.voting import create_vote, bake_vote_items, confirm_vote_script
from utils.easy_track import remove_evmscript_factory
from utils.ipfs import calculate_vote_ipfs_description, upload_vote_ipfs_description
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)

from utils.permissions import (
    encode_oz_revoke_role,
    encode_oz_grant_role
)

HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM = 5

KYBER_ORACLE_MEMBER = "0xA7410857ABbf75043d61ea54e07D57A6EB6EF186"
CALIBER_ORACLE_MEMBER = "0x4118DAD7f348A4063bD15786c299De2f3B1333F3"

NEW_KEY_REMOVAL_CHARGE = 0

CS_VERIFIER_ADDRESS_OLD="0x0c345dFa318f9F4977cdd4f33d80F9D0ffA38e8B"
CS_VERIFIER_ADDRESS_NEW="0xeC6Cc185f671F627fb9b6f06C8772755F587b05d"

# To be defined
IPFS_DESCRIPTION = ""



# AccountingOracle helpers
def encode_remove_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_add_accounting_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_accounting_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


# ValidatorsExitBusOracle helpers
def encode_remove_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus: interface.LidoOracle = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


def encode_remove_validators_cs_fee_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.csm_hash_consensus

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, quorum))


# CSFeeOracle helpers
def encode_add_validators_exit_bus_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.hash_consensus_for_validators_exit_bus_oracle

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


def encode_add_cs_fee_oracle_member(member: str, quorum: int) -> Tuple[str, str]:
    hash_consensus = contracts.csm_hash_consensus

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, quorum))


# CSM Parameters change helper

def encode_update_staking_module(
    staking_module_id: int,
    stake_share_limit: int,
    priority_exit_share_threshold: int
) -> Tuple[str, str]:
    module = contracts.staking_router.getStakingModule(staking_module_id)

    return (
        contracts.staking_router.address,
        contracts.staking_router.updateStakingModule.encode_input(
            staking_module_id,
            stake_share_limit,
            priority_exit_share_threshold,
            module["stakingModuleFee"],  # Preserve current fee
            module["treasuryFee"],  # Preserve current treasury fee
            module["maxDepositsPerBlock"],  # Preserve current max deposits per block
            module["minDepositBlockDistance"]  # Preserve current min deposit block distance
        )
    )


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting"""

# Remove Kyber oracle member from AccountingOracle, ValidatorsExitBusOracle, CSFeeOracle
    remove_kyber_oracle_member_script = [
        encode_remove_accounting_oracle_member(KYBER_ORACLE_MEMBER, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM),
        encode_remove_validators_exit_bus_oracle_member(KYBER_ORACLE_MEMBER,
                                                        HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM),
        encode_remove_validators_cs_fee_oracle_member(KYBER_ORACLE_MEMBER, HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM),
    ]

    # Add Caliber oracle member to AccountingOracle, ValidatorsExitBusOracle, CSFeeOracle
    add_caliber_oracle_member_script = [
        encode_add_accounting_oracle_member(CALIBER_ORACLE_MEMBER, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM),
        encode_add_validators_exit_bus_oracle_member(CALIBER_ORACLE_MEMBER,
                                                     HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM),
        encode_add_cs_fee_oracle_member(CALIBER_ORACLE_MEMBER, HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM),
    ]

    csm_params_change_script = [
        encode_update_staking_module(
            staking_module_id=3,
            stake_share_limit=300,
            priority_exit_share_threshold=375
        ),
        encode_oz_grant_role(contracts.csm, "MODULE_MANAGER_ROLE", contracts.agent),
        (
            contracts.csm.address,
            contracts.csm.setKeyRemovalCharge.encode_input(NEW_KEY_REMOVAL_CHARGE),
        ),
        encode_oz_revoke_role(contracts.csm, "MODULE_MANAGER_ROLE", contracts.agent)
    ]

    cs_verifier_rotation_script = [
        encode_oz_revoke_role(
            contract=contracts.csm,
            role_name="VERIFIER_ROLE",
            revoke_from=CS_VERIFIER_ADDRESS_OLD,
        ),
        encode_oz_grant_role(
            contract=contracts.csm,
            role_name="VERIFIER_ROLE",
            grant_to=CS_VERIFIER_ADDRESS_NEW,
        )
    ]

    combined_call_script = [
        *remove_kyber_oracle_member_script,
        *add_caliber_oracle_member_script,
        *csm_params_change_script,
        *cs_verifier_rotation_script
    ]

    dual_governance_call_script = submit_proposals([
        ([agent_forward(combined_call_script)],
         "Oracle rotation and CSM parameter updates")
    ])

    vote_desc_items, call_script_items = zip(
        # --- I. PML, ATC, RCC ET Factories Removal
        (
            "1. Remove PML stablecoins factory 0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory("0x92a27C4e5e35cFEa112ACaB53851Ec70e2D99a8D")
        ),
        (
            "2. Remove PML stETH factory 0xc5527396DDC353BD05bBA578aDAa1f5b6c721136 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory("0xc5527396DDC353BD05bBA578aDAa1f5b6c721136")
        ),
        (
            "3. Remove ATC stablecoins factory 0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory("0x1843Bc35d1fD15AbE1913b9f72852a79457C42Ab")
        ),
        (
            "4. Remove ATC stETH factory 0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory("0x87b02dF27cd6ec128532Add7C8BC19f62E6f1fB9")
        ),
        (
            "5. Remove RCC stablecoins factory 0x75bDecbb6453a901EBBB945215416561547dfDD4 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory("0x75bDecbb6453a901EBBB945215416561547dfDD4")
        ),
        (
            "6. Remove RCC stETH factory 0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35 from Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            remove_evmscript_factory("0xcD42Eb8a5db5a80Dc8f643745528DD77cf4C7D35")
        ),

        (
            "DG Items",
            dual_governance_call_script[0]
        )
    )

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(IPFS_DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(IPFS_DESCRIPTION)

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
