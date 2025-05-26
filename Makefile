define run_2nd_test
	@if [ -n \"$$ETH_RPC_URL2\" ]; then \\
		ETH_RPC_URL=\"$$ETH_RPC_URL2\"; \\
	fi; \\
	if [ -n \"$$ETHERSCAN_TOKEN2\" ]; then \\
		ETHERSCAN_TOKEN=\"$$ETHERSCAN_TOKEN2\"; \\
	fi; \\
	poetry run $(1)
endef

define run_3rd_test
	@if [ -n \"$$ETH_RPC_URL3\" ]; then \\
		ETH_RPC_URL=\"$$ETH_RPC_URL3\"; \\
	fi; \\
	if [ -n \"$$ETHERSCAN_TOKEN3\" ]; then \\
		ETHERSCAN_TOKEN=\"$$ETHERSCAN_TOKEN3\"; \\
	fi; \\
	poetry run $(1)
endef

test:
	poetry run brownie test --network mfh-1

test-1/2:
	poetry run brownie test tests/*.py tests/regression/test_staking_router_stake_distribution.py --network mfh-1

test-2/2:
	$(call run_2nd_test,brownie test -k 'not test_staking_router_stake_distribution.py' --network mfh-2)

test-1/3:
	poetry run brownie test tests/*.py tests/regression/test_accounting_oracle_extra_data_full_items.py --network mfh-1

test-2/3:
	$(call run_2nd_test,brownie test tests/*.py tests/regression/test_staking_router_stake_distribution.py tests/regression/test_sanity_checks.py --network mfh-2)

test-3/3:
	$(call run_3rd_test,brownie test -k 'not test_sanity_checks.py and not test_accounting_oracle_extra_data_full_items.py and not test_staking_router_stake_distribution.py' --network mfh-3)
