#!/bin/bash
# filepath: change_proxy_admin.sh

# Configuration - Edit these variables
PRIVATE_KEY="0xbcdf20249abf0ed6d944c0288fad489e33f66b3960d9e6229c1cd214ed3bbe31"  # Private key for transaction signing
RPC_URL="http://localhost:33405"  # RPC node URL

# Check if required parameters are provided
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <new_admin_address> <proxy_address1> [proxy_address2] ..."
    echo "Example: $0 0x1234...5678 0xabcd...9876 0xdefa...4321"
    exit 1
fi

# Extract the new admin address from the first argument
NEW_ADMIN=$1
shift

# Validate the new admin address
if [[ ! "$NEW_ADMIN" =~ ^0x[a-fA-F0-9]{40}$ ]]; then
    echo "Error: Invalid Ethereum address format for new admin: $NEW_ADMIN"
    exit 1
fi

echo "🔄 Changing admin to $NEW_ADMIN for the following proxies:"

# Loop through each proxy address provided
for PROXY_ADDRESS in "$@"; do
    # Validate the proxy address
    if [[ ! "$PROXY_ADDRESS" =~ ^0x[a-fA-F0-9]{40}$ ]]; then
        echo "⚠️  Warning: Invalid Ethereum address format: $PROXY_ADDRESS, skipping..."
        continue
    fi

    echo "📝 Processing proxy: $PROXY_ADDRESS"

    # Call the proxy__changeAdmin function with the new admin address using explicit private key and RPC URL
    echo "   Calling proxy__changeAdmin with new admin: $NEW_ADMIN"
    RESULT=$(cast send --private-key $PRIVATE_KEY --rpc-url $RPC_URL --from "0x8943545177806ED17B9F23F0a21ee5948eCaa776" --legacy --json $PROXY_ADDRESS "proxy__changeAdmin(address)" $NEW_ADMIN 2>&1)

    # Check if the call was successful
    if [ $? -eq 0 ]; then
        TX_HASH=$(echo $RESULT | jq -r '.transactionHash')
        echo "   ✅ Admin changed successfully. Transaction: $TX_HASH"

        # Verify the change (optional)
        echo "   🔍 Verifying the admin change..."
        CURRENT_ADMIN=$(cast call --rpc-url $RPC_URL $PROXY_ADDRESS "proxy__getAdmin()(address)" 2>/dev/null)
        if [ "$CURRENT_ADMIN" = "$NEW_ADMIN" ]; then
            echo "   ✅ Verification successful. New admin is set."
        else
            echo "   ⚠️  Verification warning: Current admin is $CURRENT_ADMIN"
        fi
    else
        echo "   ❌ Failed to change admin: $RESULT"
    fi

    echo "-------------------------------------------"
done

echo "✨ Script execution completed."
