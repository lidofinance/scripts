import time

from utils.shapella_upgrade import prepare_transfer_ownership_to_template_no_locator
from utils.config import (
    get_deployer_account,
    network_name,
    deployer_eoa,
    lido_dao_template_address,
)

# noinspection PyUnresolvedReferences
from utils.brownie_prelude import *


def main():
    assert get_deployer_account() == deployer_eoa, "Need to set DEPLOYER to the deployer_eoa"

    prepare_transfer_ownership_to_template_no_locator(deployer_eoa, lido_dao_template_address)
    time.sleep(5)  # hack for waiting thread #2.
