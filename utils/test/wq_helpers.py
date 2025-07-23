from utils.test.deposits_helpers import cover_wq_demand_and_submit
from utils.test.oracle_report_helpers import oracle_report
from utils.config import contracts

def finalize_all_wq_requests():
    withdrawal_queue = contracts.withdrawal_queue

    if withdrawal_queue.getLastRequestId() != withdrawal_queue.getLastFinalizedRequestId():
        # stake new ether to cover demand in wq
        cover_wq_demand_and_submit(0)

        # finalize all current requests
        oracle_report()[0]

    assert withdrawal_queue.getLastRequestId() == withdrawal_queue.getLastFinalizedRequestId()
