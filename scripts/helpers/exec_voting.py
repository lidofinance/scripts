from brownie import network, Contract, accounts, rpc, chain


def main():
    # ABI of the contract (replace with actual ABI of your contract)
    abi = [
        {
            "constant": False,
            "inputs": [
                {"name": "_voteId", "type": "uint256"},
                {"name": "_supports", "type": "bool"},
                {"name": "_executesIfDecided_deprecated", "type": "bool"},
            ],
            "name": "vote",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [{"name": "_voteId", "type": "uint256"}],
            "name": "executeVote",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]
    # mainnet
    # account1 = accounts.at("0xb8d83908aab38a159f3da47a59d84db8e1838712", force=True)
    # account2 = accounts.at("0xa2dfc431297aee387c05beef507e5335e684fbcd", force=True)
    # vote_executor = "0x3e40d73eb977dc6a537af587d48316fee66e9c8c"

    # сontract_address = "0x2e59A20f205bB85a89C53f1936454680651E618e"

    # holesky
    account1 = accounts.at("0xBA59A84C6440E8cccfdb5448877E26F1A431Fc8B", force=True)
    account2 = accounts.at("0x1D835790d93a28fb30d998C0CB27426E5D2D7C8c", force=True)
    vote_executor = "0xaa6bfBCD634EE744CB8FE522b29ADD23124593D3"

    сontract_address = "0xdA7d2573Df555002503F29aA4003e398d28cc00f"

    contract = Contract.from_abi("Vote", сontract_address, abi)

    vote_id = 84  # Replace with the actual vote ID
    supports = True  # Set to True or False based on your requirement
    executes_if_decided = False  # Set to True or False based on your requirement

    contract.vote(vote_id, supports, executes_if_decided, {"from": account1})
    contract.vote(vote_id, supports, executes_if_decided, {"from": account2})

    days = 3
    hours = 5
    total_sleep_time = (days * 24 * 60 * 60) + (hours * 60 * 60)  # 3 days and 2 hours in seconds

    chain.sleep(total_sleep_time)
    # Mine a block
    chain.mine()

    tx = contract.executeVote(vote_id, {"from": vote_executor})

    # Print the transaction details
    print(f"Transaction hash: {tx.txid}")
    print(f"Gas used: {tx.gas_used}")

    # Disconnect from the network
    network.disconnect()
