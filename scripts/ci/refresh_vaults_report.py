from brownie import web3

from utils.config import contracts
from utils.test.oracle_report_helpers import oracle_report

def get_vaults_report_age() -> int:
    # Not chain.time(): it is the wall clock plus the offset this very process slept, so it does not
    # see the warp done by the vote enactment. VaultHub compares the report against block.timestamp.
    return web3.eth.get_block("latest").timestamp - contracts.lazy_oracle.latestReportTimestamp()

def main():
    """Bring a fresh AccountingOracle report so that VaultHub stops treating vaults as stale.

    Enacting a vote moves the fork clock ~9 days ahead while the vaults report stays at the fork
    block, and VaultHub reverts with VaultReportStale on a report older than REPORT_FRESHNESS_DELTA.
    """
    freshness_delta = contracts.vault_hub.REPORT_FRESHNESS_DELTA()
    report_age = get_vaults_report_age()
    print(f"Vaults report age: {report_age}s, freshness delta: {freshness_delta}s")

    if report_age < freshness_delta:
        print("Vaults report is fresh, skipping the oracle report.")
        return

    # The report is only needed to move the timestamp, so keep the rebase itself at zero.
    oracle_report(cl_diff=0, exclude_vaults_balances=True, skip_withdrawals=True, silent=True)

    report_age = get_vaults_report_age()
    print(f"Vaults report age after the oracle report: {report_age}s")

    assert report_age < freshness_delta, "Vaults report is still stale after the oracle report"