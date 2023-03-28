"""
Auxiliary script needed to be run to prepare on-chain state for the Shapella upgrade.
Includes:
- deployment of the ShapellaUpgradeTemplate
- transferring admin roles from deployerEAO to ShapellaUpgradeTemplate
- transferring a bit of steth to dead address (known aka "putting the stone")
- upgrade lido locator implementation
"""

import time

from brownie import ShapellaUpgradeTemplate
from utils.shapella_upgrade import deploy_shapella_upgrade_template
from utils.config import (
    get_deployer_account,
    network_name,
    deployer_eoa,
)

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


def main():
    deployer = get_deployer_account()
    assert deployer == deployer_eoa, "Need to set DEPLOYER to the deployer_eoa"

    template = ShapellaUpgradeTemplate.deploy({"from": deployer})
    print(f"Shapella upgrade template is deployed at {template}")

    ShapellaUpgradeTemplate.publish_source(template)

    time.sleep(5)  # hack for waiting thread #2.
