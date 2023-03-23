"""
Auxiliary script needed to be run to prepare on-chain state for the Shapella upgrade.
Includes:
- deployment of the ShapellaUpgradeTemplate
- transferring admin roles from deployerEAO to ShapellaUpgradeTemplate
- transferring a bit of steth to dead address (known aka "putting the stone")
- upgrade lido locator implementation
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import ShapellaUpgradeTemplate

from utils.shapella_upgrade import prepare_for_voting
from utils.config import (
    get_deployer_account,
    deployer_eoa,
)
from utils.permissions import encode_permission_create, encode_permission_revoke

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


def main():
    assert get_deployer_account() == deployer_eoa, "Need to set DEPLOYER to the deployer_eoa"
    assert network_name() != "mainnet" and network_name() != "mainnet-fork"

    prepare_for_voting(deployer_eoa)
    time.sleep(5)  # hack for waiting thread #2.