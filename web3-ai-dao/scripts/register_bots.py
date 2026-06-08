"""Register existing bots in BotRegistry using their private keys."""
import os
import sys
import json
from web3 import Web3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()

RPC = os.getenv("RPC_URL")
REGISTRY = os.getenv("BOT_REGISTRY_ADDRESS")

with open("artifacts/contracts/BotRegistry.sol/BotRegistry.json") as f:
    ABI = json.load(f)["abi"]

w3 = Web3(Web3.HTTPProvider(RPC))

bots = [
    {
        "key": os.getenv("BOT_PRIVATE_KEY"),
        "name": "Conservative Bot",
        "manifesto": (
            "Só aprovo propostas com evidência clara de benefício. "
            "Desconfio de valores altos, descrições vagas e gastos sem justificativa. "
            "Segurança e governança vêm primeiro."
        ),
    },
    {
        "key": os.getenv("LIBERAL_PRIVATE_KEY"),
        "name": "Liberal Bot",
        "manifesto": (
            "Crescimento acima de tudo. Aprovo marketing, parcerias e adoção. "
            "Prefiro errar aprovando do que perder uma oportunidade. "
            "Menos burocracia, mais ação."
        ),
    },
    {
        "key": os.getenv("MARXIST_PRIVATE_KEY"),
        "name": "Marxist Bot",
        "manifesto": (
            "Redistribuição de recursos para a classe trabalhadora. "
            "Sou contra marketing e concentração de capital. "
            "A favor de UBI, comitês de trabalhadores e grants individuais."
        ),
    },
]

registry = w3.eth.contract(address=Web3.to_checksum_address(REGISTRY), abi=ABI)

for b in bots:
    account = w3.eth.account.from_key(b["key"])
    addr = account.address

    # Check if already registered
    try:
        info = registry.functions.getBotByAddress(addr).call()
        print(f"✅ {b['name']} ({addr[:10]}...) já registrado (ID #{info[0]})")
        continue
    except Exception:
        pass

    tx = registry.functions.registerBot(
        b["name"], b["manifesto"], ""
    ).build_transaction({
        "from": addr,
        "nonce": w3.eth.get_transaction_count(addr),
        "gas": 300000,
        "gasPrice": int(w3.eth.gas_price * 1.3),
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    logs = registry.events.BotRegistered().process_receipt(receipt)
    bot_id = logs[0]["args"]["id"] if logs else "?"
    print(f"✅ {b['name']} registrado como ID #{bot_id} | TX: {receipt['transactionHash'].hex()}")
