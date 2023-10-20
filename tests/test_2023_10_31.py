"""
Tests for voting 31/10/2023

"""
from scripts.vote_2023_10_31 import start_vote

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_removed_event,
)
from utils.test.event_validators.node_operators_registry import (
    validate_target_validators_count_changed_event,
    TargetValidatorsCountChanged,
)
from utils.test.event_validators.permission import validate_grant_role_event


def test_vote(
    helpers,
    accounts,
    interface,
    vote_ids_from_env,
):
    easy_track = interface.EasyTrack("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")
    dao_voting = interface.Voting("0x2e59A20f205bB85a89C53f1936454680651E618e")

    rcc_dai_topup_factory_old = interface.IEVMScriptFactory("0x84f74733ede9bFD53c1B3Ea96338867C94EC313e")
    pml_dai_topup_factory_old = interface.IEVMScriptFactory("0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD")
    atc_dai_topup_factory_old = interface.IEVMScriptFactory("0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07")

    old_factories_list = easy_track.getEVMScriptFactories()

    assert len(old_factories_list) == 16

    assert rcc_dai_topup_factory_old in old_factories_list
    assert pml_dai_topup_factory_old in old_factories_list
    assert atc_dai_topup_factory_old in old_factories_list

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")


    updated_factories_list = easy_track.getEVMScriptFactories()
    assert len(updated_factories_list) == 13


    # 1. Remove RCC DAI top up EVM script factory (old ver) 0x84f74733ede9bFD53c1B3Ea96338867C94EC313e from Easy Track
    assert rcc_dai_topup_factory_old not in updated_factories_list

    # 2. Remove PML DAI top up EVM script factory (old ver) 0x4E6D3A5023A38cE2C4c5456d3760357fD93A22cD from Easy Track
    assert pml_dai_topup_factory_old not in updated_factories_list

    # 3. Remove ATC DAI top up EVM script factory (old ver) 0x67Fb97ABB9035E2e93A7e3761a0d0571c5d7CD07 from Easy Track
    assert atc_dai_topup_factory_old not in updated_factories_list

    # validate vote events
    assert count_vote_items_by_events(vote_tx, dao_voting) == 3, "Incorrect voting items count"

    display_voting_events(vote_tx)

    evs = group_voting_events(vote_tx)


    validate_evmscript_factory_removed_event(evs[0], rcc_dai_topup_factory_old)
    validate_evmscript_factory_removed_event(evs[1], pml_dai_topup_factory_old)
    validate_evmscript_factory_removed_event(evs[2], atc_dai_topup_factory_old)

