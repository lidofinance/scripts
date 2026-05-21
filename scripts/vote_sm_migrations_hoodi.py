"""
Vote [HOODI] - SM migrations.
"""

import eth_abi
from brownie import interface, web3
from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    AGENT,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
)
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.dual_governance import submit_proposals
from utils.agent import agent_forward
from utils.easy_track import add_evmscript_factory, remove_evmscript_factory
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role


META_REGISTRY_ADDRESS = "0x857289cCBFBc4C134Cc312022a104CD9b38d8AAE"
META_REGISTRY_INTERMEDIATE_IMPL = "0x21050e0b934f486e5E587e5ee5Dd3C0C8D8D1A6c"
META_REGISTRY_NEW_IMPL = "0x775a73fBAFa783aC8c04764b6875FC23BAEA5815"

VETTED_GATE_ADDRESS = "0x10a254E724fe2b7f305F76f3F116a3969c53845f"
VETTED_GATE_IMPL = "0x5Dd9dDC953f2a4352D9C8C42B8D5E2bf535e602F"
VETTED_GATE_NAME = "Identified Community Stakers Gate"

CURATED_GATE_IMPL = "0xA8347dD3fe2f0c8d100B7e224E2B243dF99bA941"
CURATED_GATES = (
    ("0xF1862d120831eBE31f7202378Ff3Ae63A5658ae3", "Professional Operator Gate"),
    ("0x410A309dF81B782190188CDB3d215729cc6bC1f3", "Professional Trusted Operator Gate"),
    ("0xa5A604b172787e017b1b118F02fE54fC1D696519", "Public Good Operator Gate"),
    ("0xE966874cDB6A4282ED75Cd10439e3799e5531a2D", "Decentralization Operator Gate"),
    ("0x5c063da03e3f21443716D75a2205EE16706e1153", "Extra Effort Operator Gate"),
    ("0x1cD655Ac53CfE8269DE0DBfc0140B074623C4A6B", "Intra-Operator DVT Cluster Gate"),
    ("0x28518be9894C20135F280a9539617783b08a04c7", "Intra-Operator DVT Cluster Plus Gate"),
)

EASYTRACK_CREATE_OR_UPDATE_OPERATOR_GROUP_OLD_FACTORY = "0x44D9b39bBdc2182Aa1af6f16f8F55E0eA038294d"
EASYTRACK_CREATE_OR_UPDATE_OPERATOR_GROUP_NEW_FACTORY = "0x47DA6206965CD722591e87f5eC43604812705e88"

_OLD_GROUP_SIG = "createOrUpdateOperatorGroup(uint256,((uint64,uint16)[],(bytes)[]))"
_NEW_GROUP_SIG = "createOrUpdateOperatorGroup(uint256,(string,(uint64,uint16)[],(bytes)[]))"
_OLD_GROUP_TUPLE_TYPE = "((uint64,uint16)[],(bytes)[])"
_NEW_GROUP_TUPLE_TYPE = "(string,(uint64,uint16)[],(bytes)[])"
_NO_GROUP_ID = 0

DG_PROPOSAL_DESCRIPTION = "Hoodi named Gates and MetaRegistry (CMv2) migration"

IPFS_DESCRIPTION = """
# Hoodi named Gates and MetaRegistry (CMv2) migration

1. Upgrade existing Vetted and Curated gate proxies to name-aware implementations.
2. Set human-readable names for existing Vetted and Curated gates.
3. Wipe every operator group via OLD `createOrUpdateOperatorGroup`.
4. Upgrade impl to the intermediate one and call `finalizeUpgrade()`.
5. Upgrade impl to the final mapping-based one.
6. Re-create every group with an empty name via NEW `createOrUpdateOperatorGroup`.
7. Swap the `CreateOrUpdateOperatorGroup` Easy Track factory.
"""


def _eth_call(selector_text: str, args_types: List[str] = (), args=()) -> bytes:
    selector = web3.keccak(text=selector_text)[:4]
    data = bytes(selector) + (eth_abi.encode(list(args_types), list(args)) if args_types else b"")
    return web3.eth.call({"to": META_REGISTRY_ADDRESS, "data": data})


def _encode_proxy_upgrade_to(proxy_address: str, implementation: str) -> Tuple[str, str]:
    proxy = interface.OssifiableProxy(proxy_address)
    return proxy.address, proxy.proxy__upgradeTo.encode_input(implementation)


def _encode_set_name(gate_address: str, name: str) -> Tuple[str, str]:
    selector = web3.keccak(text="setName(string)")[:4]
    args = eth_abi.encode(["string"], [name])
    return gate_address, "0x" + (selector + args).hex()


def _encode_finalize_upgrade() -> Tuple[str, str]:
    selector = web3.keccak(text="finalizeUpgrade()")[:4]
    return META_REGISTRY_ADDRESS, "0x" + bytes(selector).hex()


def _encode_clean_group_old(group_id: int) -> Tuple[str, str]:
    selector = web3.keccak(text=_OLD_GROUP_SIG)[:4]
    args = eth_abi.encode(
        ["uint256", _OLD_GROUP_TUPLE_TYPE],
        [group_id, ([], [])],
    )
    return META_REGISTRY_ADDRESS, "0x" + (selector + args).hex()


def _encode_recreate_group_new(
    sub_node_operators: List[Tuple[int, int]],
    external_operators: List[Tuple[bytes]],
) -> Tuple[str, str]:
    selector = web3.keccak(text=_NEW_GROUP_SIG)[:4]
    args = eth_abi.encode(
        ["uint256", _NEW_GROUP_TUPLE_TYPE],
        [_NO_GROUP_ID, ("", sub_node_operators, external_operators)],
    )
    return META_REGISTRY_ADDRESS, "0x" + (selector + args).hex()


def _new_factory_permissions() -> str:
    selector_hex = web3.keccak(text=_NEW_GROUP_SIG)[:4].hex()
    if selector_hex.startswith("0x"):
        selector_hex = selector_hex[2:]
    return META_REGISTRY_ADDRESS + selector_hex


def _read_all_groups() -> List[Tuple[int, List[Tuple[int, int]], List[Tuple[bytes]]]]:
    (count,) = eth_abi.decode(["uint256"], _eth_call("getOperatorGroupsCount()"))
    groups = []
    for gid in range(1, count):
        (sub_ops, ext_ops) = eth_abi.decode(
            [_OLD_GROUP_TUPLE_TYPE],
            _eth_call("getOperatorGroup(uint256)", ["uint256"], [gid]),
        )[0]
        groups.append(
            (
                gid,
                [(int(o[0]), int(o[1])) for o in sub_ops],
                [(bytes(e[0]),) for e in ext_ops],
            )
        )
    return groups


def _get_gate_upgrade_and_name_calls() -> List[Tuple[str, str]]:
    calls = [
        _encode_proxy_upgrade_to(VETTED_GATE_ADDRESS, VETTED_GATE_IMPL),
        _encode_set_name(VETTED_GATE_ADDRESS, VETTED_GATE_NAME),
    ]

    for gate_address, name in CURATED_GATES:
        calls.append(_encode_proxy_upgrade_to(gate_address, CURATED_GATE_IMPL))
        calls.append(_encode_set_name(gate_address, name))

    return calls


def get_dg_items() -> List[Tuple[str, str]]:
    groups = _read_all_groups()
    assert groups, "MetaRegistry has no operator groups to migrate"

    clean_calls = [_encode_clean_group_old(gid) for gid, _, _ in groups]
    recreate_calls = [_encode_recreate_group_new(ops, pks) for _gid, ops, pks in groups]

    meta_registry = interface.AccessControl(META_REGISTRY_ADDRESS)
    return [
        agent_forward(_get_gate_upgrade_and_name_calls()),
        agent_forward([encode_oz_grant_role(meta_registry, "MANAGE_OPERATOR_GROUPS_ROLE", AGENT)]),
        agent_forward(clean_calls),
        agent_forward([_encode_proxy_upgrade_to(META_REGISTRY_ADDRESS, META_REGISTRY_INTERMEDIATE_IMPL)]),
        agent_forward([_encode_finalize_upgrade()]),
        agent_forward([_encode_proxy_upgrade_to(META_REGISTRY_ADDRESS, META_REGISTRY_NEW_IMPL)]),
        agent_forward(recreate_calls),
        agent_forward([encode_oz_revoke_role(meta_registry, "MANAGE_OPERATOR_GROUPS_ROLE", AGENT)]),
    ]


def get_easytrack_swap_items() -> List[Tuple[str, str]]:
    return [
        remove_evmscript_factory(EASYTRACK_CREATE_OR_UPDATE_OPERATOR_GROUP_OLD_FACTORY),
        add_evmscript_factory(
            factory=EASYTRACK_CREATE_OR_UPDATE_OPERATOR_GROUP_NEW_FACTORY,
            permissions=_new_factory_permissions(),
        ),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    dg_items = get_dg_items()
    et_items = get_easytrack_swap_items()

    dg_call_script = submit_proposals([(dg_items, DG_PROPOSAL_DESCRIPTION)])

    vote_desc_items = [
        "1. Submit DG proposal: named Gates and MetaRegistry migration",
        "2. Remove the OLD CreateOrUpdateOperatorGroup Easy Track factory",
        "3. Add the NEW CreateOrUpdateOperatorGroup Easy Track factory",
    ]
    call_script_items = [dg_call_script[0], et_items[0], et_items[1]]

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
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
