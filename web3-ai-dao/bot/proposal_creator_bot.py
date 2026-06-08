import os
import time
import json
from datetime import datetime

from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    geth_poa_middleware = None
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
BOT_PRIVATE_KEY = os.getenv("BOT_PRIVATE_KEY")
TOKEN_ADDRESS = os.getenv("TOKEN_ADDRESS")
DAO_ADDRESS = os.getenv("DAO_ADDRESS")

STATE_FILE = os.path.join(os.path.dirname(__file__), 'proposal_creator_state.json')
CYCLE_INTERVAL = int(os.getenv("CREATOR_CYCLE_INTERVAL", "60"))

MARKETING_INTERVAL = 7 * 24 * 3600
REWARD_INTERVAL = 14 * 24 * 3600

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if os.getenv("CHAIN_ID") == "31337":
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

assert w3.is_connected(), "Failed to connect to RPC"

bot_account = w3.eth.account.from_key(BOT_PRIVATE_KEY)
bot_address = bot_account.address

DAO_ABI = json.loads('''[
  {"inputs":[{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address payable","name":"recipient","type":"address"}],"name":"createProposal","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[],"name":"proposalCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"proposals","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address payable","name":"recipient","type":"address"},{"internalType":"uint256","name":"createdAt","type":"uint256"},{"internalType":"uint256","name":"forVotes","type":"uint256"},{"internalType":"uint256","name":"againstVotes","type":"uint256"},{"internalType":"bool","name":"executed","type":"bool"},{"internalType":"bool","name":"exists","type":"bool"}],"stateMutability":"view","type":"function"}
]''')

TOKEN_ABI = json.loads('''[
  {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

dao_contract = w3.eth.contract(address=Web3.to_checksum_address(DAO_ADDRESS), abi=DAO_ABI)
token_contract = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESS), abi=TOKEN_ABI)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"proposals_created": [], "last_marketing": 0, "last_reward": 0}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_eth_balance(address):
    return w3.eth.get_balance(Web3.to_checksum_address(address)) / 1e18


def get_token_balance(address):
    try:
        return token_contract.functions.balanceOf(Web3.to_checksum_address(address)).call() / 1e18
    except Exception:
        return 0.0


def send_transaction(tx):
    signed = bot_account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt


def create_proposal(description, amount, recipient):
    nonce = w3.eth.get_transaction_count(bot_address)
    gas_price = int(w3.eth.gas_price * 1.3)
    tx = dao_contract.functions.createProposal(
        description,
        amount,
        Web3.to_checksum_address(recipient)
    ).build_transaction({
        'from': bot_address,
        'nonce': nonce,
        'gas': 350000,
        'gasPrice': gas_price,
    })
    return send_transaction(tx)


MIN_GAS_BALANCE = 0.005


def check_and_propose():
    state = load_state()
    now = time.time()
    treasury_bal = get_token_balance(DAO_ADDRESS)
    proposal_count = dao_contract.functions.proposalCount().call()

    eth_bal = get_eth_balance(bot_address)
    if eth_bal < MIN_GAS_BALANCE:
        print(f"[{datetime.now().isoformat()}] Low ETH ({eth_bal:.4f}) — skipping creation")
        return

    pid = proposal_count + 1
    created_any = False

    # Trigger 1: Treasury rebalancing (one-time per threshold tier)
    if treasury_bal > 40000 and "rebalance_1" not in state["proposals_created"]:
        desc = "Community development: allocate 5000 AIGOV for integrations and DAO tooling"
        receipt = create_proposal(desc, 5000 * 10**18, bot_address)
        state["proposals_created"].append("rebalance_1")
        save_state(state)
        print(f"[{datetime.now().isoformat()}] Treasury {treasury_bal:.0f} > 40k → Proposal #{pid} created — {receipt['transactionHash'].hex()}")
        created_any = True
        pid += 1

    # Trigger 2: Marketing proposal (weekly)
    if now - state.get("last_marketing", 0) > MARKETING_INTERVAL and treasury_bal > 10000:
        desc = "Marketing campaign: grow Projeto Icarus community through articles and social media presence"
        receipt = create_proposal(desc, 2000 * 10**18, bot_address)
        state["last_marketing"] = now
        save_state(state)
        print(f"[{datetime.now().isoformat()}] Marketing interval → Proposal #{pid} created — {receipt['transactionHash'].hex()}")
        created_any = True
        pid += 1

    # Trigger 3: Community reward (biweekly)
    if now - state.get("last_reward", 0) > REWARD_INTERVAL and treasury_bal > 10000:
        desc = "Community reward: distribute 3000 AIGOV to active members contributing proposals and votes"
        receipt = create_proposal(desc, 3000 * 10**18, bot_address)
        state["last_reward"] = now
        save_state(state)
        print(f"[{datetime.now().isoformat()}] Reward interval → Proposal #{pid} created — {receipt['transactionHash'].hex()}")
        created_any = True
        pid += 1

    if not created_any:
        print(f"[{datetime.now().isoformat()}] No triggers — treasury: {treasury_bal:.0f} AIGOV, proposals: {proposal_count}")


def print_status():
    state = load_state()
    print(f"\n{'='*50}")
    print(f"Proposal Creator Bot")
    print(f"Bot: {bot_address}")
    print(f"ETH: {get_eth_balance(bot_address):.4f}")
    print(f"AIGOV: {get_token_balance(bot_address):.0f}")
    print(f"Treasury: {get_token_balance(DAO_ADDRESS):.0f} AIGOV")
    print(f"Already created: {state['proposals_created']}")
    if state.get('last_marketing'):
        print(f"Last marketing: {datetime.fromtimestamp(state['last_marketing']).isoformat()}")
    if state.get('last_reward'):
        print(f"Last reward: {datetime.fromtimestamp(state['last_reward']).isoformat()}")
    print(f"{'='*50}\n")


def main_loop():
    print_status()
    while True:
        try:
            check_and_propose()
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Error: {e}")
        time.sleep(CYCLE_INTERVAL)


if __name__ == "__main__":
    if not all([RPC_URL, BOT_PRIVATE_KEY, TOKEN_ADDRESS, DAO_ADDRESS]):
        print("Missing env vars. Check .env")
        exit(1)

    print("Proposal Creator Bot started")
    print(f"Cycle interval: {CYCLE_INTERVAL}s\n")

    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nBot stopped.")
