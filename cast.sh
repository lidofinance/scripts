#!/bin/bash

ADDRESS="0x5fd0dDbC3351d009eb3f88DE7Cd081a614C519F1"  # <-- укажи явно адрес
RPC_URL="https://lb.drpc.org/ogrpc?network=ethereum&dkey=AjFEGNLp008tnA4vdxRnw84iJmvW1JkR7oAnBvixPDgE"  # <-- RPC с поддержкой txpool_content (например, Erigon или Anvil)

# Приводим адрес к нижнему регистру
ADDRESS_LOWER=$(echo "$ADDRESS" | tr 'A-F' 'a-f')

# Делаем запрос к txpool_content
RESPONSE=$(curl -s -X POST "$RPC_URL" \
  -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"txpool_content","params":[],"id":1}')

echo "$RESPONSE" > jjss.json  # ← проверь, что там есть

echo "$RESPONSE" | jq -r --arg addr "$ADDRESS_LOWER" '
  .result.pending[$addr] // {} | to_entries[] |
  "Nonce: \(.key) | Hash: \(.value.hash) | To: \(.value.to) | Value: \(.value.value)"'
