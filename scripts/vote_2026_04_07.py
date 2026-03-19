"""
TODO Vote 2026_04_07

TODO <list of items synced with Notion>

TODO (after vote) Vote #{vote number} passed & executed on {date+time}, block {blockNumber}.
"""

from brownie import interface
from typing import Dict, List, Tuple

from utils.easy_track import add_evmscript_factory, create_permissions, remove_evmscript_factory
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import get_deployer_account, get_is_live, get_priority_fee
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals

from utils.agent import agent_forward


# ============================== Constants ===================================
OLD_EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0xB7668B5485d0f826B86a75b0115e088bB9ee03eE"
OLD_EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x8aa34dAaF0fC263203A15Bcfa0Ed926D466e59F3"
NEW_EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x58A59dDC6Aea9b1D5743D024E15DfA4badB56E37"
NEW_EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY = "0x4F716AD3Cc7A3A5cdA2359e5B2c84335c171dCde"
VALIDATORS_EXIT_BUS_ORACLE = "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e"
OLD_CHORUS_ADDRESS = "0x285f8537e1daeedaf617e96c742f2cf36d63ccfb"
NEW_CHORUS_ADDRESS = "0x8dB977C13CAA938BC58464bFD622DF0570564b78"

HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE = "0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288"
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE = "0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"
HASH_CONSENSUS_FOR_CS_FEE_ORACLE = "0x71093efF8D8599b5fA340D665Ad60fA7C80688e4"

HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM = 5
HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM = 5

def encode_remove_accounting_oracle_member(member: str) -> Tuple[str, str]:
    hash_consensus = interface.HashConsensus(HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE)

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM))

def encode_remove_cs_fee_oracle_member(member: str) -> Tuple[str, str]:
    hash_consensus = interface.CSHashConsensus(HASH_CONSENSUS_FOR_CS_FEE_ORACLE)

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM))

def encode_remove_validators_exit_bus_oracle_member(member: str) -> Tuple[str, str]:
    hash_consensus = interface.HashConsensus(HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE)

    return (hash_consensus.address, hash_consensus.removeMember.encode_input(member, HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM))

def encode_add_accounting_oracle_member(member: str) -> Tuple[str, str]:
    hash_consensus = interface.HashConsensus(HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE)

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, HASH_CONSENSUS_FOR_ACCOUNTING_ORACLE_QUORUM))

def encode_add_cs_fee_oracle_member(member: str) -> Tuple[str, str]:
    hash_consensus = interface.CSHashConsensus(HASH_CONSENSUS_FOR_CS_FEE_ORACLE)

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, HASH_CONSENSUS_FOR_CS_FEE_ORACLE_QUORUM))

def encode_add_validators_exit_bus_oracle_member(member: str) -> Tuple[str, str]:
    hash_consensus = interface.HashConsensus(HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE)

    return (hash_consensus.address, hash_consensus.addMember.encode_input(member, HASH_CONSENSUS_FOR_VALIDATORS_EXIT_BUS_ORACLE_QUORUM))


# ============================= IPFS Description ==================================
# TODO IPFS description text
IPFS_DESCRIPTION = """
"""


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    # TODO set up interface objects

    return [
        # TODO 1.1. item description
        agent_forward([
            encode_remove_accounting_oracle_member(OLD_CHORUS_ADDRESS),
            encode_remove_cs_fee_oracle_member(OLD_CHORUS_ADDRESS),
            encode_remove_validators_exit_bus_oracle_member(OLD_CHORUS_ADDRESS),
            encode_add_accounting_oracle_member(NEW_CHORUS_ADDRESS),
            encode_add_cs_fee_oracle_member(NEW_CHORUS_ADDRESS),
            encode_add_validators_exit_bus_oracle_member(NEW_CHORUS_ADDRESS),
        ]),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:

    # TODO set up interface objects

    # TODO in case of using smart-contract based omnibus, retrieve vote items from omnibus contract
    # voting_items = brownie.interface.SmartContractOmnibus(omnibus_contract).getVoteItems()
    # vote_desc_items = []
    # call_script_items = []
    # for desc, call_script in voting_items:
    #     vote_desc_items.append(desc)
    #     call_script_items.append((call_script[0], call_script[1].hex()))
    # return vote_desc_items, call_script_items
    #
    # OR
    #
    # vote_desc_items = []
    # call_script_items = []
    # # 1. receive DG vote items from omnibus contract
    # contract_dg_items = interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).getVoteItems()
    # dg_items = []
    # for _, call_script in contract_dg_items:
    #     dg_items.append((call_script[0], call_script[1].hex()))
    # dg_call_script = submit_proposals([
    #     (dg_items, DG_PROPOSAL_DESCRIPTION)
    # ])
    # vote_desc_items.append(DG_SUBMISSION_DESCRIPTION)
    # call_script_items.append(dg_call_script[0])
    # # 2. receive non-DG vote items from omnibus contract
    # voting_items = interface.V3LaunchOmnibus(OMNIBUS_CONTRACT).getVotingVoteItems()
    # for desc, call_script in voting_items:
    #     vote_desc_items.append(desc)
    #     call_script_items.append((call_script[0], call_script[1].hex()))
    # return vote_desc_items, call_script_items
    validators_exit_bus_oracle = interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE)

    dg_items = get_dg_items()

    dg_call_script = submit_proposals([
        # TODO DG proposal description
        (dg_items, "DG proposal description")
    ])

    vote_desc_items, call_script_items = zip(
        (
            # TODO DG proposal description
            "1. DG proposal submition description",
            dg_call_script[0]
        ),
        (
            "2. Remove old SubmitValidatorsExitRequestHashes (Simple DVT) EVM script factory from EasyTrack",
            remove_evmscript_factory(
                factory=OLD_EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
            ),
        ),
        (
            "3. Remove old SubmitValidatorsExitRequestHashes (Curated Module) EVM script factory  from EasyTrack",
            remove_evmscript_factory(
                factory=OLD_EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
            ),
        ),
        (
            "4. Add SubmitValidatorsExitRequestHashes (Simple DVT) EVM script factory `0xB7668B5485d0f826B86a75b0115e088bB9ee03eE` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` with permissions `submitExitRequestsHash`",
            add_evmscript_factory(
                factory=NEW_EASYTRACK_SDVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                permissions=(create_permissions(validators_exit_bus_oracle, "submitExitRequestsHash")),
            ),
        ),
        (
            "5. Add SubmitValidatorsExitRequestHashes (Curated Module) EVM script factory `0x8aa34dAaF0fC263203A15Bcfa0Ed926D466e59F3` to Easy Track `0xF0211b7660680B49De1A7E9f25C65660F0a13Fea` with permissions `submitExitRequestsHash`",
            add_evmscript_factory(
                factory=NEW_EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY,
                permissions=(create_permissions(validators_exit_bus_oracle, "submitExitRequestsHash")),
            ),
        ),
    )

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION)
        if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
