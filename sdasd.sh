poetry run brownie run scripts/tw_vote.py --network=holesky-fork-test

# poetry run brownie networks import network-config.yaml True
# 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
poetry run brownie accounts new "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

# anvil --fork-url https://ethereum-holesky-rpc.publicnode.com --auto-impersonate
export DEPLOYER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266


# https://hackmd.io/@george-avs/SyaBlsZrkx
export DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80


poetry run brownie run scripts/tw_vote.py --network=devnet-444


#   - cmd: ./ganache.sh
#     cmd_settings:
#       accounts: 10
#       chain_id: 17000
#       gas_limit: 30000000
#       mnemonic: brownie
#       port: 8545
#     host: http://127.0.0.1
#     id: devnet-444
#     name: Devnet444
#     timeout: 360
# account with ldo on holesky
# 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f

# 0x14ae7daeecdf57034f3E9db8564e46Dba8D97344 ldo toketn


cast send 0x14ae7daeecdf57034f3E9db8564e46Dba8D97344 "transfer(address,uint256)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 820000000000000000000000 --from 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f


cast rpc anvil_impersonateAccount 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f --rpc-url http://127.0.0.1:8545 && \
cast send 0x14ae7daeecdf57034f3E9db8564e46Dba8D97344 "transfer(address,uint256)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 820000000000000000000000 --from 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f


cast rpc anvil_impersonateAccount 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f --rpc-url http://127.0.0.1:8545 && \
cast send 0x14ae7daeecdf57034f3E9db8564e46Dba8D97344 "transfer(address,uint256)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 100 --from 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f --unlocked --rpc-url http://127.0.0.1:8545
## time travel
cast rpc evm_increaseTime 3000 && cast rpc anvil_mine

# vote
# ​​​​​cast send --from 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f 0xdA7d2573Df555002503F29aA4003e398d28cc00f vote(uint256,bool,bool) <VOTE_ID> true false
cast send --from 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f --unlocked 0xdA7d2573Df555002503F29aA4003e398d28cc00f "vote(uint256,bool,bool)" 22 true false

# exec
# cast send 0xdA7d2573Df555002503F29aA4003e398d28cc00f "executeVote(uint256)" <VOTE_ID>
cast send --from 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f --unlocked 0xdA7d2573Df555002503F29aA4003e398d28cc00f "executeVote(uint256)" 22

# _____

## Отправка 100 токенов для того чтобы можно было создавать голосования
cast rpc anvil_impersonateAccount 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f --rpc-url http://127.0.0.1:8545 && \
cast send 0x14ae7daeecdf57034f3E9db8564e46Dba8D97344 "transfer(address,uint256)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 100 --from 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f --unlocked --rpc-url http://127.0.0.1:8545



cast call 0xF0179dEC45a37423EAD4FaD5fCb136197872EAd9 "proxy_getAdmin()(address)"


# отправка обновления импл из под аккаунта воутинга
cast send 0xF0179dEC45a37423EAD4FaD5fCb136197872EAd9 "proxy_upgradeTo(address,bytes)" 0x9Fe653933300a05BF60d19901031DA8008653a6e "0x" --from 0xdA7d2573Df555002503F29aA4003e398d28cc00f --unlocked --rpc-url http://127.0.0.1:8545



cast send 0xdA7d2573Df555002503F29aA4003e398d28cc00f "executeVote(uint256)" 514 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80




cast rpc anvil_impersonateAccount 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f --rpc-url http://127.0.0.1:8545 && \
cast send 0x14ae7daeecdf57034f3E9db8564e46Dba8D97344 "transfer(address,uint256)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 100 --from 0xCD1f9954330AF39a74Fd6e7B25781B4c24ee373f --unlocked --rpc-url http://127.0.0.1:8545



# ???????
