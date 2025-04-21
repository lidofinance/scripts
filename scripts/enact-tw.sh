cast rpc anvil_impersonateAccount 0xc3C65cB7aa6D36F051f875708b8E17f9a0B210eD --rpc-url http://127.0.0.1:8545 && \
cast send 0xEf2573966D009CcEA0Fc74451dee2193564198dc "transfer(address,uint256)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 100 --from 0xc3C65cB7aa6D36F051f875708b8E17f9a0B210eD --unlocked --rpc-url http://127.0.0.1:8545


cast send --from 0xc3C65cB7aa6D36F051f875708b8E17f9a0B210eD --unlocked 0x49B3512c44891bef83F8967d075121Bd1b07a01B "vote(uint256,bool,bool)" 22 true false

## time travel
cast rpc evm_increaseTime 3000 && cast rpc anvil_mine

# exec
# cast send 0x49B3512c44891bef83F8967d075121Bd1b07a01B "executeVote(uint256)" <VOTE_ID>
cast send --from 0xc3C65cB7aa6D36F051f875708b8E17f9a0B210eD --unlocked 0x49B3512c44891bef83F8967d075121Bd1b07a01B "executeVote(uint256)" 22
