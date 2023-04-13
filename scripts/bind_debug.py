import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import ProtocolDebugBinder
from utils.shapella_upgrade import prepare_transfer_ownership_to_template
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.repo import (
    add_implementation_to_lido_app_repo,
    add_implementation_to_nor_app_repo,
    add_implementation_to_oracle_app_repo,
)
from utils.kernel import update_app_implementation
from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    lido_dao_staking_router,
    lido_dao_withdrawal_vault,
    lido_dao_withdrawal_vault_implementation,
    get_priority_fee,
    deployer_eoa,
)
from utils.permissions import encode_permission_create

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


def transfer_ownership(owner, template, tx_params):
    admin_role = interface.AccessControlEnumerable(contracts.burner).DEFAULT_ADMIN_ROLE()

    def transfer_oz_admin_to_template(contract):
        assert interface.AccessControlEnumerable(contract).getRoleMember(admin_role, 0) == owner
        interface.AccessControlEnumerable(contract).grantRole(admin_role, template, tx_params)
        interface.AccessControlEnumerable(contract).revokeRole(admin_role, owner, tx_params)

    def transfer_proxy_admin_to_template(contract):
        assert interface.OssifiableProxy(contract).proxy__getAdmin() == owner
        interface.OssifiableProxy(contract).proxy__changeAdmin(template, tx_params)

    assert contracts.deposit_security_module.getOwner() == owner
    contracts.deposit_security_module.setOwner(template, tx_params)

    transfer_oz_admin_to_template(contracts.burner)
    transfer_oz_admin_to_template(contracts.hash_consensus_for_accounting_oracle)
    transfer_oz_admin_to_template(contracts.hash_consensus_for_validators_exit_bus_oracle)

    transfer_proxy_admin_to_template(contracts.accounting_oracle)
    transfer_proxy_admin_to_template(contracts.staking_router)
    transfer_proxy_admin_to_template(contracts.validators_exit_bus_oracle)
    transfer_proxy_admin_to_template(contracts.withdrawal_queue)


def bind(tx_params: Dict[str, str]) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    binder = ProtocolDebugBinder.deploy(tx_params)
    print(f"binder address ${binder.address}")

    transfer_ownership(deployer_eoa, binder.address, tx_params)

    binder.bind(tx_params)


def main():
    tx_params = {"from": deployer_eoa}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = bind(tx_params=tx_params)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
