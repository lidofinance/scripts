#!/bin/bash

RPC_URL="http://localhost:33529"  # URL вашего RPC сервера
FROM="0x8943545177806ED17B9F23F0a21ee5948eCaa776"

PRIVATE_KEY="0xbcdf20249abf0ed6d944c0288fad489e33f66b3960d9e6229c1cd214ed3bbe31"  # или через CAST_PRIVATE_KEY
echo "Запрашиваем txpool..."
TXPOOL=$(cast rpc txpool_content --rpc-url "$RPC_URL")

# Получаем список всех nonces
NONCES=$(echo "$TXPOOL" | jq -r '.result.pending["'"${FROM,,}"'"] | keys_unsorted[]')
QUEUED_NONCES=$(echo "$TXPOOL" | jq -r '.result.queued["'"${FROM,,}"'"] | keys_unsorted[]')

ALL_NONCES=$(echo -e "$NONCES\n$QUEUED_NONCES" | sort -n | uniq)

for NONCE in $ALL_NONCES; do
  TX=$(echo "$TXPOOL" | jq -r '.result.pending["'"${FROM,,}"'"]["'"$NONCE"'"] // .result.queued["'"${FROM,,}"'"]["'"$NONCE"'"]')

  TYPE=$(echo "$TX" | jq -r '.type')
  echo "Обрабатываем nonce=$NONCE (type=$TYPE)"

  if [ "$TYPE" = "0x2" ]; then
    OLD_MAXFEE=$(echo "$TX" | jq -r '.maxFeePerGas')
    OLD_PRIORITY=$(echo "$TX" | jq -r '.maxPriorityFeePerGas')

    NEW_MAXFEE=$(( (OLD_MAXFEE * 15) / 10 ))
    NEW_PRIORITY=$(( (OLD_PRIORITY * 15) / 10 ))
    [ "$NEW_PRIORITY" -lt 1000000 ] && NEW_PRIORITY=1000000

    echo " → Отправка отменяющей EIP-1559 транзакции (maxFee=$NEW_MAXFEE, prio=$NEW_PRIORITY)"

    cast send "$FROM" \
      --from "$FROM" \
      --value 0 \
      --nonce "$NONCE" \
      --gas-limit 21000 \
      --max-fee-per-gas "$NEW_MAXFEE" \
      --priority-fee "$NEW_PRIORITY" \
      --private-key "$PRIVATE_KEY" \
      --rpc-url "$RPC_URL"

  elif [ "$TYPE" = "0x0" ]; then
    OLD_GASPRICE=$(echo "$TX" | jq -r '.gasPrice')
    NEW_GASPRICE=$(( (OLD_GASPRICE * 15) / 10 ))

    echo " → Отправка отменяющей Legacy транзакции (gasPrice=$NEW_GASPRICE)"

    cast send "$FROM" \
      --from "$FROM" \
      --value 0 \
      --nonce "$NONCE" \
      --gas-limit 21000 \
      --gas-price "$NEW_GASPRICE" \
      --private-key "$PRIVATE_KEY" \
      --rpc-url "$RPC_URL"

  else
    echo " ❌ Неизвестный тип транзакции: $TYPE"
  fi
done
