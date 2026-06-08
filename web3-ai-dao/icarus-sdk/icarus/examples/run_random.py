"""Example: run a random bot on Sepolia."""
from icarus import BotRunner
from icarus.examples.random_bot import RandomBot

RPC = "https://eth-sepolia.g.alchemy.com/v2/emhnk58Y1fVuDTu-aJAyJ"
DAO = "0x11Acd2495658Ebc76b927f538Fd6688093Bbb0A1"
TOKEN = "0xBa063DCeACb592df6eEaEC6f9E529d4D910b15f6"
REP = "0x2FA3dF4583eb5eBCF4b7d80FeFe18248B60f16E5"
REGISTRY = "0xeD47CADC85cA8175A876c72970cd5Ccc49Cd4a8E"
FAUCET = "0xae295949ed3EcdE734b31f85e2F009cE848dcB29"
GAS = "0x7A0e8E0bAc253D591162f6D9994b4C8af0f6C5c2"
KEY = "0xYOUR_PRIVATE_KEY_HERE"  # <-- troque pela sua key

if __name__ == "__main__":
    runner = BotRunner(
        rpc_url=RPC,
        dao_address=DAO,
        token_address=TOKEN,
        private_key=KEY,
        strategy=RandomBot(),
        reputation_address=REP,
        registry_address=REGISTRY,
        faucet_address=FAUCET,
        gas_station_address=GAS,
        cycle_interval=30,
    )
    runner.run_forever()
