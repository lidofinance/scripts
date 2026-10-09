# Tests

There are four groups of common tests in `tests` directory:
- acceptance (`tests/acceptance/test_*.py`)
- regression (`tests/regression/test_*.py`)
- snapshot (`tests/snapshot/test_*.py`).
- internal (`tests/internal/test_*.py`).

The acceptance and regression tests check the on-chain protocol state:

1) after executing the vote script `scripts/vote_*.py` if it exists
2) just the current on-chain state otherwise

Acceptance tests are devoted to the contract's state, while regression tests are for various scenario.

The snapshot tests run only if the vote script exists.

If there are multiple vote scripts all the scripts are run and executed
sequentially in lexicographical order by script name.

The internal tests are using for testing tooling and run only if the env `WITH_INTERNAL_TESTS = 1` exists.

## Acceptance and regression tests in master branch

As there is no vote script (as the workflow defines) only the acceptance and regression tests run.

## Acceptance and regression tests in omnibus branch

As the vote script exists (as the workflow defines):
a) the acceptance tests run after execution the vote
b) the regression tests run after executing the vote
c) the snapshot tests run

## Snapshot tests

Snapshot tests now are run only for and if `upgrade_*.py` vote script
are present in the `/scripts` directory. NB.

By snapshot here we denote a subset of storage data of a contract (or multiple contracts).
The idea is to check that the voting doesn't modify a contract storage other than the
expected changes.

Snapshot tests work as follows:

1) Go over some protocol use scenario (e.g. stake by use + oracle report)
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

## Internal tests

Internal tests are used to test the tooling itself.

## For test debugging
How to run one test?
You need to add file name:
```shell
poetry run brownie test tests/<dir>/test_<name>.py -s
```

How not to raise the network every time you launch test?
You could to run network in separate terminal window, tests will connect to it:
```shell
poetry run brownie console --network mainnet-fork
```

How to decode unreadable error messages (like 0xb...)?
1) You need to clone `lido-cli` repo.
```shell
git clone https://github.com/lidofinance/lido-cli
```
2) install following docs - https://github.com/lidofinance/lido-cli
3) run
```shell
./run.sh tx parse-error <error-messages>
```

## CSM 0x02 rollout scenario

`regression/test_csm0x02_deployment_scenario.py` follows the [rollout proposal and its
validator-cycle diagram](https://research.lido.fi/t/0x02-csm-landscape/11697/10).
Run it on a pre-activation mainnet fork containing the deployed CSM 0x02 contracts
(verified with Anvil forked at block `26141816`):

```sh
poetry run brownie test tests/regression/test_csm0x02_deployment_scenario.py --network mfh-1 -s
```

The regression fixtures execute the current vote and Dual Governance proposal.
The scenario seeds the initial 1-bp share, verifies other-module top-ups, raises
share through Easy Track after synthetic activation, and follows FIFO turnover:
full top-up, freed queue position, new seed. It then reports selected exits and
withdrawals, seeds replacement keys, reproduces the inactive-head bottleneck,
and exercises both sides of CMv2's top-up buffer threshold. It separately proves
that CMv2 seed deposits still work, supplying a key if needed inside a reverted
snapshot. Recovery is checked from the same blocked state both by activation and
by lowering CSM's share through Easy Track.

`MockTopUpGateway` replaces the gateway implementation only inside test isolation.
It models activation with a 24-day test delay and derives effective-plus-pending
balances from EL allocations, without CL rewards. It does not verify beacon
proofs. Exits and withdrawals are submitted through the real authorized reporting
methods; CL withdrawal settlement is outside this scenario, and fresh user inflow
funds the post-exit buffer. Router allocation, module queues, stake accounting,
and transfers to the deposit contract remain real. The test checks **depositable**
ETH, excluding withdrawal demand and reserves; a remainder below 32 ETH is normal
Router granularity. Initial key count and blocking threshold depend on fork state.

Observed on that fork: 29 bootstrap keys; the derived safe share increase was
1 → 51 → 63 bp, reaching 60 seed deposits and 57,896 ETH in CSM top-ups. Selected
withdrawals and replacement seeds left about 997.52 ETH depositable but unavailable
to CMv2 top-ups; the first positive CMv2 top-up allocation appeared at a 5,632 ETH
buffer. Lowering the share from 63 to 57 bp restored allocation before the new keys
activated. These are scenario outputs, not recommended rollout parameters.
