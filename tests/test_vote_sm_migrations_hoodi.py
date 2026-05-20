"""
Test vote [HOODI] - SM migrations.
"""

from brownie import interface, chain, Contract

from scripts import vote_sm_migrations_hoodi as voting_script
from scripts.vote_sm_migrations_hoodi import (
    start_vote,
    _read_all_groups,
    _new_factory_permissions,
    EASYTRACK_CREATE_OR_UPDATE_OPERATOR_GROUP_OLD_FACTORY,
    EASYTRACK_CREATE_OR_UPDATE_OPERATOR_GROUP_NEW_FACTORY,
)
from utils.config import (
    DUAL_GOVERNANCE,
    TIMELOCK,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    contracts,
)
from utils.dual_governance import wait_for_target_time_to_satisfy_time_constrains


_META_REGISTRY_NEW_READ_ABI = [
    {
        "name": "getOperatorGroupsCount",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "uint256", "name": ""}],
    },
    {
        "name": "getOperatorGroup",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"type": "uint256", "name": "groupId"}],
        "outputs": [{
            "type": "tuple",
            "name": "",
            "components": [
                {"type": "string", "name": "name"},
                {
                    "type": "tuple[]",
                    "name": "subNodeOperators",
                    "components": [
                        {"type": "uint64", "name": "nodeOperatorId"},
                        {"type": "uint16", "name": "share"},
                    ],
                },
                {
                    "type": "tuple[]",
                    "name": "externalOperators",
                    "components": [{"type": "bytes", "name": "data"}],
                },
            ],
        }],
    },
    {
        "name": "getNodeOperatorGroupId",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"type": "uint256", "name": "nodeOperatorId"}],
        "outputs": [{"type": "uint256", "name": ""}],
    },
    {
        "name": "getExternalOperatorGroupId",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{
            "type": "tuple",
            "name": "op",
            "components": [{"type": "bytes", "name": "data"}],
        }],
        "outputs": [{"type": "uint256", "name": ""}],
    },
    {
        "name": "getNodeOperatorWeight",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"type": "uint256", "name": "nodeOperatorId"}],
        "outputs": [{"type": "uint256", "name": ""}],
    },
]


def _mr() -> Contract:
    return Contract.from_abi(
        "MetaRegistryNew", voting_script.META_REGISTRY_ADDRESS, _META_REGISTRY_NEW_READ_ABI
    )


def test_vote_sm_migrations_hoodi(helpers, accounts, vote_ids_from_env, stranger):
    proxy = interface.OssifiableProxy(voting_script.META_REGISTRY_ADDRESS)
    easy_track = contracts.easy_track
    new_impl = voting_script.META_REGISTRY_NEW_IMPL
    new_factory = EASYTRACK_CREATE_OR_UPDATE_OPERATOR_GROUP_NEW_FACTORY

    assert proxy.proxy__getImplementation().lower() != new_impl.lower()
    assert easy_track.isEVMScriptFactory(EASYTRACK_CREATE_OR_UPDATE_OPERATOR_GROUP_OLD_FACTORY)
    assert not easy_track.isEVMScriptFactory(new_factory)

    real_groups_before = _read_all_groups()
    assert real_groups_before, "Nothing to migrate: MetaRegistry has no groups"

    mr = _mr()
    weights_before = {
        op_id: mr.getNodeOperatorWeight(op_id)
        for _gid, subs, _exts in real_groups_before
        for op_id, _share in subs
    }

    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        vote_id, _ = start_vote({"from": LDO_HOLDER_ADDRESS_FOR_TESTS}, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    proposal_id = vote_tx.events["ProposalSubmitted"][-1]["proposalId"]

    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    dg = interface.DualGovernance(DUAL_GOVERNANCE)

    chain.sleep(timelock.getAfterSubmitDelay() + 1)
    dg.scheduleProposal(proposal_id, {"from": stranger})

    chain.sleep(timelock.getAfterScheduleDelay() + 1)
    wait_for_target_time_to_satisfy_time_constrains()

    timelock.execute(proposal_id, {"from": stranger})

    # --- impl and group count
    assert proxy.proxy__getImplementation().lower() == new_impl.lower()
    assert mr.getOperatorGroupsCount() == len(real_groups_before)

    # --- group contents, reverse maps, weights
    for gid, sub_before, ext_before in real_groups_before:
        name, sub_after, ext_after = mr.getOperatorGroup(gid)
        assert name == "", f"Group #{gid} name must be empty, got {name!r}"

        assert [(int(o[0]), int(o[1])) for o in sub_after] == sub_before, (
            f"Group #{gid} subNodeOperators changed"
        )
        assert [(bytes(e[0]),) for e in ext_after] == ext_before, (
            f"Group #{gid} externalOperators changed"
        )

        for op_id, _share in sub_before:
            assert mr.getNodeOperatorGroupId(op_id) == gid
            assert mr.getNodeOperatorWeight(op_id) == weights_before[op_id]
        for (ext_data,) in ext_before:
            assert mr.getExternalOperatorGroupId((ext_data,)) == gid

    # --- Easy Track factory swap
    assert not easy_track.isEVMScriptFactory(EASYTRACK_CREATE_OR_UPDATE_OPERATOR_GROUP_OLD_FACTORY)
    assert easy_track.isEVMScriptFactory(new_factory)

    expected_perms = _new_factory_permissions().removeprefix("0x").lower()
    actual_perms = easy_track.evmScriptFactoryPermissions(new_factory).hex().removeprefix("0x").lower()
    assert actual_perms == expected_perms, (
        f"New factory permissions mismatch: expected {expected_perms}, got {actual_perms}"
    )
