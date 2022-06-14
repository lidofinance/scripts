import json


def deploy_from_prepared_tx(deployer, tx_file_path) -> str:
    tx_data = json.load(open(tx_file_path))["data"]
    tx = deployer.transfer(data=tx_data)
    return tx.contract_address

