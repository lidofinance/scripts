from contextlib import contextmanager
from brownie import chain, accounts, interface

from utils.config import VOTING, network_name


@contextmanager
def chain_snapshot():
    try:
        print("Making chain snapshot...")
        chain.snapshot()
        yield
    finally:
        print("Reverting the chain...")
        chain.revert()


def pass_and_exec_dao_vote(vote_id):
    dao_voting = interface.Voting(VOTING)

    if dao_voting.getVote(vote_id)["executed"]:
        print(f"[ok] Vote {vote_id} already executed")
        return

    helper_acct = accounts[0]

    if not dao_voting.canExecute(vote_id):
        print(f"Passing vote {vote_id}")

        if network_name() == "mainnet-fork":
            # together these accounts hold 15% of LDO total supply
            ldo_holders = [
                "0x3e40d73eb977dc6a537af587d48316fee66e9c8c",
                "0xb8d83908aab38a159f3da47a59d84db8e1838712",
                "0xa2dfc431297aee387c05beef507e5335e684fbcd",
            ]
        elif network_name() == "holesky-fork":
            ldo_holders = ["0xBA59A84C6440E8cccfdb5448877E26F1A431Fc8B", "0x1D835790d93a28fb30d998C0CB27426E5D2D7C8c"]
        elif network_name() == "hoodi-fork":
            ldo_holders = ["0xc3C65cB7aa6D36F051f875708b8E17f9a0B210eD"]

        for holder_addr in ldo_holders:
            print(f"  voting from {holder_addr}")
            helper_acct.transfer(holder_addr, "1 ether", silent=True)
            account = accounts.at(holder_addr, force=True)
            dao_voting.vote(vote_id, True, False, {"from": account, "silent": True})

        # wait for the vote to end
        chain.sleep(3 * 60 * 60 * 24)
        chain.mine()

        assert dao_voting.canExecute(vote_id)

    print(f"Executing vote {vote_id}")

    dao_voting.executeVote(vote_id, {"from": helper_acct, "silent": True})
    assert dao_voting.getVote(vote_id)["executed"]

    print(f"[ok] Vote {vote_id} executed")
