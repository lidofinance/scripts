from brownie import network, Contract, accounts, rpc, chain


def main():
    # ABI of the contract (replace with actual ABI of your contract)
    abi = [
        {
            "inputs": [],
            "name": "proxy__getImplementation",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "implementation",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    contract_address = "0x28FAB2059C713A7F9D8c86Db49f9bb0e96Af1ef8"

    contract = Contract.from_abi("LidoLocator", contract_address, abi)

    address = contract.proxy__getImplementation()

    # Print the transaction details
    print(f"Locator impl: {address}")

    # Staking router implementation
    STAKING_ROUTER = "0xd6EbF043D30A7fe46D1Db32BA90a0A51207FE229"

    srAbi = [
        {
            "inputs": [
                {"internalType": "bytes32", "name": "role", "type": "bytes32"},
                {"internalType": "address", "name": "account", "type": "address"},
            ],
            "name": "hasRole",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]
    # Pause role
    PAUSE_ROLE = "0x00b1e70095ba5bacc3202c3db9faf1f7873186f0ed7b6c84e80c0018dcc6e38e"
    ADDRESS1 = "0x045dd46212A178428c088573A7d102B9d89a022A"

    sr = Contract.from_abi("StakingRouter", STAKING_ROUTER, srAbi)
    res = sr.hasRole(PAUSE_ROLE, ADDRESS1)

    print(f"old dsm pause role: {res}")

    UNVETTING_ROLE = "0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57"
    ADDRESS2 = "0xe0aA552A10d7EC8760Fc6c246D391E698a82dDf9"

    res2 = sr.hasRole(UNVETTING_ROLE, ADDRESS2)

    print(f"new dsm unvetting role: {res2}")

    sdvt_proxy = "0x11a93807078f8BB880c1BD0ee4C387537de4b4b6"
    sdvt = Contract.from_abi("SimpleDVT", sdvt_proxy, abi)

    sdvt_impl = sdvt.implementation()

    # Print the transaction details
    print(f"Sdvt impl: {sdvt_impl}")

    sandbox_proxy_addr = "0xD6C2ce3BB8bea2832496Ac8b5144819719f343AC"
    sandbox_proxy = Contract.from_abi("Sandbox", sandbox_proxy_addr, abi)

    sandbox_proxy_impl = sandbox_proxy.implementation()

    # Print the transaction details
    print(f"Sandbox impl: {sandbox_proxy_impl }")
