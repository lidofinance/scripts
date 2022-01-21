import click
import requests
from ape_safe import ApeSafe
from brownie import *

multisig_address = "0x7FEa69d107A77B5817379d1254cc80D9671E171b"
ldo_contract = "0x5a98fcbea516cf06857215779fd812ca3bef1b32"

cowswap_contract = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"


def cowswap_sell(safe, sell_token, buy_token, amount):
    gnosis_settlement = safe.contract("0x9008D19f58AAbD9eD0D60971565AA8510560ab41")

    fee_and_quote = "https://protocol-mainnet.gnosis.io/api/v1/feeAndQuote/sell"
    get_params = {
        "sellToken": sell_token.address,
        "buyToken": buy_token.address,
        "sellAmountBeforeFee": amount,
    }
    r = requests.get(fee_and_quote, params=get_params)
    print(vars(r))
    assert r.ok and r.status_code == 200

    # These two values are needed to create an order
    fee_amount = int(r.json()["fee"]["amount"])
    buy_amount_after_fee = int(r.json()["buyAmountAfterFee"])
    assert fee_amount > 0
    assert buy_amount_after_fee > 0

    # Pretty random order deadline :shrug:
    deadline = chain.time() + 60 * 60 * 24 * 100  # 100 days

    # Submit order
    order_payload = {
        "sellToken": sell_token.address,
        "buyToken": buy_token.address,
        "sellAmount": str(
            amount - fee_amount
        ),  # amount that we have minus the fee we have to pay
        "buyAmount": str(
            buy_amount_after_fee
        ),  # buy amount fetched from the previous call
        "validTo": deadline,
        "appData": "0x2B8694ED30082129598720860E8E972F07AA10D9B81CAE16CA0E2CFB24743E24",  # maps to https://bafybeiblq2ko2maieeuvtbzaqyhi5fzpa6vbbwnydsxbnsqoft5si5b6eq.ipfs.dweb.link
        "feeAmount": str(fee_amount),
        "kind": "sell",
        "partiallyFillable": False,
        "receiver": safe.address,
        "signature": safe.address,
        "from": safe.address,
        "sellTokenBalance": "erc20",
        "buyTokenBalance": "erc20",
        "signingScheme": "presign",  # Very important. this tells the api you are going to sign on chain
    }
    orders_url = f"https://protocol-mainnet.gnosis.io/api/v1/orders"
    r = requests.post(orders_url, json=order_payload)
    assert r.ok and r.status_code == 201
    order_uid = r.json()
    print(f"Payload: {order_payload}")
    print(f"Order uid: {order_uid}")

    # With the order id, we set the flag, basically signing as the gnosis safe.
    gnosis_settlement.setPreSignature(order_uid, True)


def main():
    safe = ApeSafe(multisig_address)
    ldo_token = safe.contract(ldo_contract)
    dai_token = safe.contract("0x6b175474e89094c44da98b954eedeac495271d0f")

    gnosis_vault_relayer = safe.contract("0xC92E8bdf79f0507f65a392b0ab4667716BFE0110")
    ldo_token.approve(gnosis_vault_relayer, 2 ** 256 - 1)

    safe_tx = safe.multisend_from_receipts()
    account = click.prompt("signer", type=click.Choice(accounts.load()))
    safe_tx.sign(accounts.load(account).private_key)
    safe.preview(safe_tx, events=False, call_trace=False)
    safe.post_transaction(safe_tx)
    amount = ldo_token.balanceOf(safe.address)

    cowswap_sell(safe, ldo_token, dai_token, amount)

    safe_tx = safe.multisend_from_receipts()
    account = click.prompt("signer", type=click.Choice(accounts.load()))
    safe_tx.sign(accounts.load(account).private_key)
    safe.preview(safe_tx, events=False, call_trace=False)
    safe.post_transaction(safe_tx)
