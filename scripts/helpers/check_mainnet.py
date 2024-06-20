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

    contract_address = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"

    contract = Contract.from_abi("LidoLocator", contract_address, abi)

    address = contract.proxy__getImplementation()

    # Print the transaction details
    print(f"Locator impl: {address}")

    # Staking router implementation
    STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"

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
    ADDRESS1 = "0xC77F8768774E1c9244BEed705C4354f2113CFc09"

    sr = Contract.from_abi("StakingRouter", STAKING_ROUTER, srAbi)
    res = sr.hasRole(PAUSE_ROLE, ADDRESS1)

    print(f"old dsm pause role: {res}")

    UNVETTING_ROLE = "0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57"
    ADDRESS2 = "0xf9C8Cf55f2E520B08d869df7bc76aa3d3ddDF913"

    res2 = sr.hasRole(UNVETTING_ROLE, ADDRESS2)

    print(f"new dsm unvetting role: {res2}")

    sdvt_proxy = "0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433"
    sdvt = Contract.from_abi("SimpleDVT", sdvt_proxy, abi)

    sdvt_impl = sdvt.implementation()

    # Print the transaction details
    print(f"Sdvt impl: {sdvt_impl}")
