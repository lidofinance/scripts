#!/bin/bash

ADDRESS="0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1"  # <-- укажи явно адрес
RPC_URL="https://rpc.gnosis.gateway.fm"  # <-- RPC с поддержкой txpool_content (например, Erigon или Anvil)

# Приводим адрес в нижний регистр
ADDRESS_LOWER=$(echo "$ADDRESS" | tr 'A-F' 'a-f')

# Получаем текущий nonce
CURRENT_NONCE=$(cast nonce "$ADDRESS" --rpc-url "$RPC_URL")
echo "Current nonce: $CURRENT_NONCE"

# Начинаем с nonce = 0
for (( NONCE=0; NONCE<CURRENT_NONCE; NONCE++ ))
do
  # Получаем tx hash по адресу и nonce
  TX_HASH=$(cast rpc eth_getTransactionBySenderAndNonce "$ADDRESS" "0x$(printf "%x" $NONCE)" --rpc-url "$RPC_URL" | grep -o '"hash": *"[^"]*"' | cut -d'"' -f4)

  if [[ -z "$TX_HASH" ]]; then
    echo "Nonce $NONCE: no tx found (possibly dropped or replaced)"
    continue
  fi

  # Получаем статус транзакции
  TX_RECEIPT=$(cast tx "$TX_HASH" --rpc-url "$RPC_URL" 2>/dev/null)

  if [[ -z "$TX_RECEIPT" ]]; then
    echo "Nonce $NONCE: tx $TX_HASH is PENDING"
  else
    echo "Nonce $NONCE: tx $TX_HASH is MINED"
  fi
done
