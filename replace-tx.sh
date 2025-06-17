#!/bin/bash

# ==== НАСТРОЙКИ ====

RPC_URL="http://localhost:33637"  # URL вашего RPC сервера
FROM="0x8943545177806ED17B9F23F0a21ee5948eCaa776"
PRIVATE_KEY="0xbcdf20249abf0ed6d944c0288fad489e33f66b3960d9e6229c1cd214ed3bbe31"  # или через CAST_PRIVATE_KEY
# ===================

cast send $FROM \
  $FROM \
  --value 0 \
  --from $FROM \
  --nonce 449 \
   --gas-limit 30000 \
  --priority-gas-price 35000000000 \
  --gas-price 40000000000 \
  --rpc-url $RPC_URL \
  --private-key $PRIVATE_KEY
# # Получаем nonce (pending)
# NONCE=$(cast nonce $FROM --rpc-url $RPC_URL)
# echo "Nonce: $NONCE"

# # Получаем текущий gas price
# GAS_PRICE=$(cast gas-price --rpc-url $RPC_URL)
# # Увеличиваем на 30%
# GAS_PRICE=$(cast --to-wei "$(echo "$GAS_PRICE * 1.4" | bc -l)" wei)
# echo "Increased gas price: $GAS_PRICE wei"

# # Отправляем пустую транзакцию самому себе
# cast send $FROM \
#   --from $FROM \
#   --value 0 \
#   --nonce 279 \
#   --gas-limit 321000 \
#   --gas-price $GAS_PRICE \
#   --private-key $PRIVATE_KEY \
#   --rpc-url $RPC_URL \
#   --legacy \
