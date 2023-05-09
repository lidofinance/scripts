from brownie import interface, accounts
from utils.config import contracts, lido_dao_legacy_oracle


def legacy_report(_epochId, _beaconBalance, _beaconValidators):
    oracle = interface.LidoOracle(lido_dao_legacy_oracle)
    quorum = oracle.getQuorum()
    members = oracle.getOracleMembers()

    for i in range(quorum):
        member = accounts.at(members[i], force=True)
        oracle.reportBeacon(_epochId, _beaconBalance, _beaconValidators, {"from": member})
