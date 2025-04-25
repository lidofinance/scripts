cast rpc anvil_impersonateAccount 0xE25583099BA105D9ec0A67f5Ae86D90e50036425 --rpc-url http://127.0.0.1:8545 && \
cast send 0x60Ea774468B9397cCc04a88d8cc72e5dd2Cab7f7 "transfer(address,uint256)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 100 --from 0xE25583099BA105D9ec0A67f5Ae86D90e50036425 --unlocked --rpc-url http://127.0.0.1:8545


cast send --from 0xE25583099BA105D9ec0A67f5Ae86D90e50036425 --unlocked 0x2A011ba95b36edB50f4EC6Cd7596F6B7AC234f8b "vote(uint256,bool,bool)" 5 true false

## time travel
cast rpc evm_increaseTime 3000 && cast rpc anvil_mine

# exec
# cast send 0x2A011ba95b36edB50f4EC6Cd7596F6B7AC234f8b "executeVote(uint256)" <VOTE_ID>
cast send --from 0xE25583099BA105D9ec0A67f5Ae86D90e50036425 --unlocked 0x2A011ba95b36edB50f4EC6Cd7596F6B7AC234f8b "executeVote(uint256)" 5
