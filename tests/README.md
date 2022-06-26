# Tests

There are two groups of common tests in `tests` directory: regression
(`tests/regression/test_*.py`) and snapshot (`tests/snapshot/test_*.py`).

The regression tests check the on-chain protocol state:

1) after executing the vote script `scripts/vote_*.py` if it exists
2) just the current on-chain state otherwise

The snapshot tests run only if the vote script exists.

If there are multiple vote scripts all the scripts are run and executed
sequentially in lexicographical order by script name.

## Regression tests in master branch

As there is no vote script (as the workflow defines) only the regression tests run.

## Regression tests in omnibus branch

As the vote script exists (as the workflow defines):
a) the regression tests run after executing the vote
b) the snapshot tests run

## Snapshot tests

Snapshot tests now are run only for and if `upgrade_*.py` vote script
are present in the `/scripts` directory. NB.

By snapshot here we denote a subset of storage data of a contract (or multiple contracts).
The ideas is to check that the voting doesn't modify a contract storage other than the
expected changes.

Snapshot tests work as follows:

1) Go over some protocol use scenario (e. g. stake by use + oracle report)
2) Store the snapshot along the steps
3) Revert the chain changes
4) Execute the vote
5) Do (1) and (2) again
6) Compare the snapshots got during the first and the second scenario runs
7) The expected outcome is that the voting doesn't change

Current snapshot implementation in kind of MVP and need a number of issues to
be addressed in the future:

1) expand the number of storage variables observed
2) allow modification of the storage variables supposed not to be changed after
the voting without modification of the common test files
3) extract getters from ABIs automatically
