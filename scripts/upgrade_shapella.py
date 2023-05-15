"""
Voting 12/05/2023.

Lido V2 (Shapella-ready) protocol upgrade

1. Update `WithdrawalVault` proxy implementation
2. Call `ShapellaUpgradeTemplate.startUpgrade()`
3. Publish new `Lido` implementation in Lido app APM repo
4. Update `Lido` implementation
5. Publish new `NodeOperatorsRegistry` implementation in NodeOperatorsRegistry app APM repo
6. Update `NodeOperatorsRegistry` implementation
7. Publish new `LidoOracle` implementation in LidoOracle app APM repo
8. Update `LidoOracle` implementation to `LegacyOracle`
9. Create new role `STAKING_ROLE_ROLE` and assign to `StakingRouter`
10. Call `ShapellaUpgradeTemplate.finishUpgrade()`
11. Revoke `MANAGE_FEE` role from `Voting`
12. Revoke `MANAGE_WITHDRAWAL_KEY` role from `Voting`
13. Revoke `MANAGE_PROTOCOL_CONTRACTS_ROLE` role from `Voting`
14. Revoke `SET_EL_REWARDS_VAULT_ROLE` role from `Voting`
15. Revoke `SET_EL_REWARDS_WITHDRAWAL_LIMIT_ROLE` role from `Voting`
16. Revoke `DEPOSIT_ROLE` role from old `DepositSecurityModule`
17. Revoke `BURN_ROLE` role from `SelfOwnedStETHBurner`
18. Revoke `ADD_NODE_OPERATOR_ROLE` role from `Voting`
19. Revoke `SET_NODE_OPERATOR_ACTIVE_ROLE` role from `Voting`
20. Revoke `SET_NODE_OPERATOR_NAME_ROLE` role from `Voting`
21. Revoke `SET_NODE_OPERATOR_ADDRESS_ROLE` role from `Voting`
22. Revoke `REPORT_STOPPED_VALIDATORS_ROLE` role from `Voting`
23. Revoke `MANAGE_MEMBERS` role from `Voting`
24. Revoke `MANAGE_QUORUM` role from `Voting`
25. Revoke `SET_BEACON_SPEC` role from `Voting`
26. Revoke `SET_REPORT_BOUNDARIES` role from `Voting`
27. Revoke `SET_BEACON_REPORT_RECEIVER` role from `Voting`
28. Grant `MANAGE_TOKEN_URI_ROLE` role to `Voting`
29. Set `WithdrawalQueueERC721` baseUri to `https://wq-api.lido.fi/v1/nft`
30. Revoke `MANAGE_TOKEN_URI_ROLE` role from `Voting`
31. Fund Gas Funder multisig 0x5181d5D56Af4f823b96FE05f062D7a09761a5a53 for deposits with 50 stETH
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import ShapellaUpgradeTemplate  # type: ignore
from utils.agent import agent_forward
from utils.finance import make_steth_payout

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
    STAKING_ROUTER,
    WITHDRAWAL_VAULT,
    WITHDRAWAL_VAULT_IMPL,
    SELF_OWNED_STETH_BURNER,
    get_priority_fee,
)
from utils.permissions import (
    encode_oz_grant_role,
    encode_oz_revoke_role,
    encode_permission_create,
    encode_permission_revoke,
)

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *

# Content URI: https://github.com/lidofinance/lido-dao/blob/b70881f026096790308d7ac9e277ad7f609c7117/apps/lido/README.md
update_lido_app = {
    "new_address": "0x17144556fd3424EDC8Fc8A4C940B2D04936d17eb",
    "content_uri": "0x697066733a516d525358415a724632785235726762556445724456364c47746a7151315434415a677336796f586f734d516333",
    "id": "0x3ca7c3e38968823ccb4c78ea688df41356f182ae1d159e4ee608d30d68cef320",
    "version": (4, 0, 0),
}

# Content URI: https://github.com/lidofinance/lido-dao/blob/b70881f026096790308d7ac9e277ad7f609c7117/apps/node-operators-registry/README.md
update_nor_app = {
    "new_address": "0x8538930c385C0438A357d2c25CB3eAD95Ab6D8ed",
    "content_uri": "0x697066733a516d54346a64693146684d454b5576575351316877786e33365748394b6a656743755a7441684a6b6368526b7a70",
    "id": "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d",
    "version": (4, 0, 0),
}

# Content URI: https://github.com/lidofinance/lido-dao/blob/b70881f026096790308d7ac9e277ad7f609c7117/apps/lidooracle/README.md
update_oracle_app = {
    "new_address": "0xa29b819654cE6224A222bb5f586920105E2D7E0E",
    "content_uri": "0x697066733a516d575461635041557251614376414d5663716e5458766e7239544c666a57736861736334786a536865717a3269",
    "id": "0x8b47ba2a8454ec799cd91646e7ec47168e91fd139b23f017455f3e5898aaba93",
    "version": (4, 0, 0),
}

WITHDRAWAL_QUEUE_ERC721_BASE_URI = "https://wq-api.lido.fi/v1/nft"


def encode_template_start_upgrade(template_address: str) -> Tuple[str, str]:
    template = ShapellaUpgradeTemplate.at(template_address)
    return template.address, template.startUpgrade.encode_input()


def encode_template_finish_upgrade(template_address: str) -> Tuple[str, str]:
    template = ShapellaUpgradeTemplate.at(template_address)
    return template.address, template.finishUpgrade.encode_input()


def encode_withdrawal_vault_proxy_update(vault_proxy_address: str, implementation: str) -> Tuple[str, str]:
    proxy = interface.WithdrawalVaultManager(vault_proxy_address)
    return proxy.address, proxy.proxy_upgradeTo.encode_input(implementation, b"")


def encode_withdrawal_queue_base_uri_update(withdrawal_queue_address: str, base_uri: str) -> Tuple[str, str]:
    withdrawal_queue = interface.WithdrawalQueueERC721(withdrawal_queue_address)
    return withdrawal_queue.address, withdrawal_queue.setBaseURI.encode_input(base_uri)


def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""
    voting = contracts.voting
    node_operators_registry = contracts.node_operators_registry
    lido = contracts.lido
    legacy_oracle = contracts.legacy_oracle
    withdrawal_queue = contracts.withdrawal_queue

    call_script_items = [
    ]

    vote_desc_items = [
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
