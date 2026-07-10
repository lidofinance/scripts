from brownie import ZERO_ADDRESS

from utils.balance import set_balance_in_wei
from utils.config import contracts
from utils.test.helpers import ETH
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.test.merkle_tree import AddressTree

MAX_KEYS_BATCH_SIZE = 30
DEFAULT_OPERATOR_WEIGHT = 10_000
HELPER_ROLE_HOLDER = "0xce00000000000000000000000000000000000001"
GENERATED_NODE_OPERATOR_PREFIX = "cf"
TREE_EXTRA_MEMBER_PREFIX = "df"


def _get_role_member_or_grant(contract, role):
    if contract.getRoleMemberCount(role) > 0:
        return set_balance_in_wei(contract.getRoleMember(role, 0), ETH(10))

    admin = set_balance_in_wei(
        contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0),
        ETH(10),
    )
    role_holder = set_balance_in_wei(HELPER_ROLE_HOLDER, ETH(10))
    contract.grantRole(role, role_holder, {"from": admin})
    return role_holder


def _ensure_meta_registry_setup(node_operator_id):
    meta_registry = contracts.cm_meta_registry

    group_manager = _get_role_member_or_grant(meta_registry, meta_registry.MANAGE_OPERATOR_GROUPS_ROLE())

    if meta_registry.getNodeOperatorGroupId(node_operator_id) == meta_registry.NO_GROUP_ID():
        meta_registry.createOrUpdateOperatorGroup(
            meta_registry.NO_GROUP_ID(),
            (
                "test",
                [(node_operator_id, DEFAULT_OPERATOR_WEIGHT)],
                [],
            ),
            {"from": group_manager},
        )

    assert meta_registry.getNodeOperatorWeight(node_operator_id) > 0


def _prepare_curated_gate(node_operator):
    gate = contracts.cm_professional_operator_gate
    tree_manager = _get_role_member_or_grant(gate, gate.SET_TREE_ROLE())

    nonce = contracts.cm.getNodeOperatorsCount()
    extra_member = f"0x{TREE_EXTRA_MEMBER_PREFIX}{nonce:038x}"
    tree = AddressTree.new([node_operator.address, extra_member])
    tree_cid = f"ipfs://scripts-regression-cm-{nonce}"

    gate.setTreeParams(tree.root, tree_cid, {"from": tree_manager})
    proof = tree.get_proof(node_operator.address)
    assert gate.verifyProof(node_operator, proof)
    return gate, proof


def _get_fresh_node_operator(node_operator):
    gate = contracts.cm_professional_operator_gate
    if not gate.isConsumed(node_operator):
        return node_operator

    nonce = contracts.cm.getNodeOperatorsCount()
    while True:
        candidate = f"0x{GENERATED_NODE_OPERATOR_PREFIX}{nonce:038x}"
        if not gate.isConsumed(candidate):
            return set_balance_in_wei(candidate, ETH(10))
        nonce += 1


def _get_remaining_keys_capacity(node_operator_id):
    module = contracts.cm
    accounting = contracts.cm_accounting
    parameters_registry = contracts.cm_parameters_registry

    curve_id = accounting.getBondCurveId(node_operator_id)
    keys_limit = parameters_registry.getKeysLimit(curve_id)
    non_withdrawn_keys = module.getNodeOperatorNonWithdrawnKeys(node_operator_id)
    return max(keys_limit - non_withdrawn_keys, 0)


def curated_v2_upload_keys(node_operator_id, keys_count):
    if keys_count <= 0:
        return

    assert keys_count <= _get_remaining_keys_capacity(node_operator_id)

    module = contracts.cm
    accounting = contracts.cm_accounting
    node_operator = module.getNodeOperator(node_operator_id)
    manager_address = node_operator["managerAddress"]

    remaining_keys = keys_count
    while remaining_keys > 0:
        batch_size = min(remaining_keys, MAX_KEYS_BATCH_SIZE)
        value = accounting.getRequiredBondForNextKeys(node_operator_id, batch_size)
        manager = set_balance_in_wei(manager_address, value + ETH(10))

        module.addValidatorKeysETH(
            manager_address,
            node_operator_id,
            batch_size,
            random_pubkeys_batch(batch_size),
            random_signatures_batch(batch_size),
            {"from": manager, "value": value},
        )
        remaining_keys -= batch_size


def curated_v2_add_node_operator(node_operator, keys_count):
    module = contracts.cm
    gate, proof = _prepare_curated_gate(node_operator)

    node_operators_count_before = module.getNodeOperatorsCount()
    gate.createNodeOperator(
        "test",
        "test",
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        proof,
        {"from": node_operator},
    )
    assert module.getNodeOperatorsCount() == node_operators_count_before + 1

    node_operator_id = node_operators_count_before
    _ensure_meta_registry_setup(node_operator_id)
    curated_v2_upload_keys(node_operator_id, keys_count)
    assert module.getNodeOperator(node_operator_id)["depositableValidatorsCount"] >= keys_count

    return node_operator_id


def ensure_curated_v2_depositable_keys(required_depositable_keys, node_operator):
    module = contracts.cm
    meta_registry = contracts.cm_meta_registry

    module_depositable_keys = module.getStakingModuleSummary()["depositableValidatorsCount"]
    if module_depositable_keys >= required_depositable_keys:
        return

    # Prefer topping up an existing active operator without changing its group or share.
    for node_operator_id in range(module.getNodeOperatorsCount()):
        if not module.getNodeOperatorIsActive(node_operator_id):
            continue
        if meta_registry.getNodeOperatorWeight(node_operator_id) == 0:
            continue

        remaining_keys_capacity = _get_remaining_keys_capacity(node_operator_id)
        if remaining_keys_capacity == 0:
            continue

        keys_to_add = min(
            required_depositable_keys - module_depositable_keys,
            remaining_keys_capacity,
        )
        curated_v2_upload_keys(
            node_operator_id,
            keys_to_add,
        )
        module_depositable_keys = module.getStakingModuleSummary()["depositableValidatorsCount"]
        if module_depositable_keys >= required_depositable_keys:
            return

    gate_curve_id = contracts.cm_professional_operator_gate.curveId()
    keys_limit = contracts.cm_parameters_registry.getKeysLimit(gate_curve_id)

    while module_depositable_keys < required_depositable_keys:
        node_operator = _get_fresh_node_operator(node_operator)
        keys_to_add = min(required_depositable_keys - module_depositable_keys, keys_limit)
        curated_v2_add_node_operator(node_operator, keys_to_add)

        updated_depositable_keys = module.getStakingModuleSummary()["depositableValidatorsCount"]
        assert updated_depositable_keys > module_depositable_keys
        module_depositable_keys = updated_depositable_keys

    assert module.getStakingModuleSummary()["depositableValidatorsCount"] >= required_depositable_keys
