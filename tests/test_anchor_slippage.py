
import pytest

def test_max_slippage(accounts, interface):
    admin = accounts.at('0x3cd9F71F80AB08ea5a7Dca348B5e94BC595f26A0', force=True)
    bot = accounts.at('0x1a9967a7b0c3dd39962296e53f5cf56471385df2', force=True)

    vault = interface.AnchorVault('0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf')
    liquidator = interface.AnchorLiquidator('0xE3c8A4De3b8A484ff890a38d6D7B5D278d697Fb7')

    liquidator.configure(0.03*10**18,10**18,10**18,10**18,{"from":admin})
    vault.collect_rewards({"from": bot})
