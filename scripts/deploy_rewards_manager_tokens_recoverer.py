from brownie import chain, network, RewardsManagerTokensRecoverer
from utils import config


def main():
    deployer = config.get_deployer_account()

    print(f"Current network: {network.show_active()} (chain id: {chain.id})")
    print(f"Deployer: {deployer}")
    print(f"Agent address: {config.lido_dao_agent_address}")

    print("Proceed? [y/n]: ")

    if not config.prompt_bool():
        print("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "300 gwei"}

    RewardsManagerTokensRecoverer.deploy(config.lido_dao_agent_address, tx_params)
