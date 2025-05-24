test:
	@echo "Running all tests on Hardhat mainnet fork..."
	poetry run brownie test --network mfh-1


test-1/2:
	@echo "Running 1 (of 2) test part on Hardhat mainnet fork..."
	poetry run brownie test tests/*.py tests/regression/test_staking_router_stake_distribution.py --network mfh-1

test-2/2:
	@echo "Running 2 (of 2) test part on Hardhat mainnet fork..."
	poetry run brownie test -k 'not test_staking_router_stake_distribution.py' --network mfh-2

test-2: test-1/2 test-2/2


test-1/3:
	@echo "Running 1 (of 3) test part on Hardhat mainnet fork..."
	poetry run brownie test tests/*.py tests/regression/test_accounting_oracle_extra_data_full_items.py tests/regression/test_sanity_checks.py --network mfh-1

test-2/3:
	@echo "Running 2 (of 3) test part on Hardhat mainnet fork..."
	poetry run brownie test tests/*.py tests/regression/test_staking_router_stake_distribution.py --network mfh-2

test-3/3:
	@echo "Running 3 (of 3) test part on Hardhat mainnet fork..."
	poetry run brownie test -k 'not test_sanity_checks.py and not test_accounting_oracle_extra_data_full_items.py and not test_staking_router_stake_distribution.py' --network mfh-3

test-3: test-1/3 test-2/3 test-3/3