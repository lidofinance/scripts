import os


# This is help to total ignore this test at CI
# They are disrepair, not even marked as skipped.
# Works with `brownie test` and `brownie test tests/internal`
# Doesn't work for direct run `brownie test tests/internal/test_ipfs.py`
def pytest_ignore_collect(path, config):
    return not os.getenv("WITH_INTERNAL_TESTS")
