import pytest
from utils.test.extra_data import ExtraDataService
from utils.test.oracle_report_helpers import oracle_report


@pytest.fixture()
def extra_data_service():
    return ExtraDataService()


def test_accounting_oracle_too_node_ops_per_extra_data_item(extra_data_service):
    nos_per_item_count = 30
    item_count = 2
    extra_data = extra_data_service.collect(
        {(1, i): i for i in range(10)}, {(1, i): i for i in range(30)}, item_count, nos_per_item_count
    )

    oracle_report(
        extraDataFormat=1,
        extraDataHash=extra_data.data_hash,
        extraDataItemsCount=2,
        extraDataList=extra_data.extra_data,
    )
