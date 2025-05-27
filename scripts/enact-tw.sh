cast rpc anvil_impersonateAccount 0xE25583099BA105D9ec0A67f5Ae86D90e50036425 --rpc-url http://127.0.0.1:8545 && \
cast send 0x60Ea774468B9397cCc04a88d8cc72e5dd2Cab7f7 "transfer(address,uint256)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 100 --from 0xE25583099BA105D9ec0A67f5Ae86D90e50036425 --unlocked --rpc-url http://127.0.0.1:8545


cast send --from 0xE25583099BA105D9ec0A67f5Ae86D90e50036425 --unlocked 0x3745af762d930b86D47dbf886F49Bb66e86840d9 "vote(uint256,bool,bool)" 3 true false

## time travel
cast rpc evm_increaseTime 3000 && cast rpc anvil_mine

# exec
# cast send 0x3745af762d930b86D47dbf886F49Bb66e86840d9 "executeVote(uint256)" <VOTE_ID>
cast send --from 0xE25583099BA105D9ec0A67f5Ae86D90e50036425 --unlocked 0x3745af762d930b86D47dbf886F49Bb66e86840d9 "executeVote(uint256)" 3


# cast logs "Upgraded(address indexed implementation)" \
#   --to-block latest \
#   --address 0x57E5d642648F54973e504f10D21Ea06360151cAf
