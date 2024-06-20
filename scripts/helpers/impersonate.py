from brownie import accounts


def main():
    # Address to impersonate
    holder = "0xa2dfc431297aee387c05beef507e5335e684fbcd"
    holder2 = "0xb8d83908aab38a159f3da47a59d84db8e1838712"

    accounts.at(holder, force=True)
    accounts.at(holder2, force=True)
