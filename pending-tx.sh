#!/usr/bin/env bash

# Аргументы: RPC_URL и ADDRESS
ADDRESS="0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1"  # <-- укажи явно адрес
DRPC_RPC_URL="https://lb.drpc.org/ogrpc?network=gnosis&dkey=AjFEGNLp008tnA4vdxRnw84iJmvW1JkR7oAnBvixPDgE"
ALCHEMY_RPC_URL="https://gnosis-mainnet.g.alchemy.com/v2/F7yuLiJiCDgVmPb-4oeF_Z6K8OSz31Yb"
# DRPC_RPC_URL="https://gnosis-mainnet.g.alchemy.com/v2/F7yuLiJiCDgVmPb-4oeF_Z6K8OSz31Yb"
STABLE_RPC_URL="https://rpc.gnosis.gateway.fm"  # <-- RPC с поддержкой txpool_content (например, Erigon или Anvil)

RPC_URL=$DRPC_RPC_URL
# Проверка аргументов
if [[ -z "$RPC_URL" || -z "$ADDRESS" ]]; then
    echo "Использование: $0 <RPC_URL> <ADDRESS>"
    exit 1
fi

# # Получить current nonce (pending)
# NONCE_PENDING=$(curl -s -X POST "$RPC_URL" \
#   -H "Content-Type: application/json" \
#   --data '{"jsonrpc":"2.0","method":"eth_getTransactionCount","params":["'"$ADDRESS"'","pending"],"id":1}' | jq -r .result)
# echo "Pending nonce: $NONCE_PENDING"
# # Получить confirmed nonce (latest)
# NONCE_LATEST=$(curl -s -X POST "$RPC_URL" \
#   -H "Content-Type: application/json" \
#   --data '{"jsonrpc":"2.0","method":"eth_getTransactionCount","params":["'"$ADDRESS"'","latest"],"id":1}' | jq -r .result)
# echo "Latest nonce: $NONCE_LATEST"
# # Перевести из hex в десятичную
# NONCE_PENDING_DEC=$((16#${NONCE_PENDING:2}))
# NONCE_LATEST_DEC=$((16#${NONCE_LATEST:2}))

# if (( NONCE_PENDING_DEC == NONCE_LATEST_DEC )); then
#     echo "Нет pending-транзакций для $ADDRESS"
#     exit 0
# fi

# echo "Pending nonces для $ADDRESS: $NONCE_LATEST_DEC .. $((NONCE_PENDING_DEC-1))"

# echo "Подробнее по pending-транзакциям получить через RPC невозможно без txpool_content или трекинга собственных tx_hash."

echo "STABLE_RPC_URL"
cast rpc eth_getTransactionCount 0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1 "pending" --rpc-url $STABLE_RPC_URL
cast rpc eth_getTransactionCount 0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1 "latest" --rpc-url $STABLE_RPC_URL

echo "DRPC_RPC_URL"
cast rpc eth_getTransactionCount 0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1 "pending" --rpc-url $DRPC_RPC_URL
cast rpc eth_getTransactionCount 0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1 "latest" --rpc-url $DRPC_RPC_URL


echo "ALCHEMY_RPC_URL"
cast rpc eth_getTransactionCount 0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1 "pending" --rpc-url $ALCHEMY_RPC_URL
cast rpc eth_getTransactionCount 0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1 "latest" --rpc-url $ALCHEMY_RPC_URL

# STABLE_RPC_URL
# "0xb44b6"
# "0xb44b6"
# DRPC_RPC_URL
# "0xb4763"
# "0xb44b6"
# ALCHEMY_RPC_URL
# "0xb4763"
# "0xb44b6"
