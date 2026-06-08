import os
import time
import json
import sys
import argparse
from datetime import datetime

from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    geth_poa_middleware = None
from dotenv import load_dotenv

from strategies import get_strategy

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

parser = argparse.ArgumentParser()
parser.add_argument('--key', help='Private key')
parser.add_argument('--cycle', type=int, default=40, help='Cycle interval in seconds')
args = parser.parse_args()

BOT_PRIVATE_KEY = args.key or os.getenv("MARXIST_PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
TOKEN_ADDRESS = os.getenv("TOKEN_ADDRESS")
DAO_ADDRESS = os.getenv("DAO_ADDRESS")
REPUTATION_NFT_ADDRESS = os.getenv("REPUTATION_NFT_ADDRESS", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
CYCLE_INTERVAL = args.cycle

strategy = get_strategy("marxist")

STATE_FILE = os.path.join(os.path.dirname(__file__), 'marxist_state.json')

GEMINI_AVAILABLE = bool(GEMINI_API_KEY)
DEEPSEEK_AVAILABLE = bool(DEEPSEEK_API_KEY)

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if os.getenv("CHAIN_ID") == "31337":
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

assert w3.is_connected(), "Failed to connect to RPC"
bot_account = w3.eth.account.from_key(BOT_PRIVATE_KEY)
bot_address = bot_account.address

DAO_ABI = json.loads('''[
  {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"}],"name":"executeProposal","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"proposals","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address payable","name":"recipient","type":"address"},{"internalType":"uint256","name":"createdAt","type":"uint256"},{"internalType":"uint256","name":"forVotes","type":"uint256"},{"internalType":"uint256","name":"againstVotes","type":"uint256"},{"internalType":"bool","name":"executed","type":"bool"},{"internalType":"bool","name":"exists","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"proposalCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"},{"internalType":"bool","name":"support","type":"bool"}],"name":"vote","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"address","name":"","type":"address"}],"name":"hasVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address payable","name":"recipient","type":"address"}],"name":"createProposal","outputs":[],"stateMutability":"nonpayable","type":"function"}
]''')

TOKEN_ABI = json.loads('''[
  {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

dao_contract = w3.eth.contract(address=Web3.to_checksum_address(DAO_ADDRESS), abi=DAO_ABI)
token_contract = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESS), abi=TOKEN_ABI)

REPUTATION_ABI = json.loads('''[
  {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getReputation","outputs":[{"internalType":"uint256","name":"xp","type":"uint256"},{"internalType":"uint8","name":"level","type":"uint8"},{"internalType":"uint256","name":"proposalsVoted","type":"uint256"},{"internalType":"uint256","name":"proposalsCreated","type":"uint256"},{"internalType":"uint256","name":"lastActive","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getVotingMultiplier","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

reputation_contract = None
if REPUTATION_NFT_ADDRESS:
    reputation_contract = w3.eth.contract(address=Web3.to_checksum_address(REPUTATION_NFT_ADDRESS), abi=REPUTATION_ABI)

def get_eth_balance(addr):
    return w3.eth.get_balance(Web3.to_checksum_address(addr)) / 1e18

def get_token_balance(addr):
    try:
        return token_contract.functions.balanceOf(Web3.to_checksum_address(addr)).call() / 1e18
    except Exception:
        return 0.0

def get_reputation_info(addr):
    if not reputation_contract:
        return {"has_nft": False, "xp": 0, "level": "NONE", "multiplier": 1}
    try:
        bal = reputation_contract.functions.balanceOf(Web3.to_checksum_address(addr)).call()
        if bal == 0:
            return {"has_nft": False, "xp": 0, "level": "NONE", "multiplier": 1}
        rep = reputation_contract.functions.getReputation(Web3.to_checksum_address(addr)).call()
        mult = reputation_contract.functions.getVotingMultiplier(Web3.to_checksum_address(addr)).call()
        levels = ["BRONZE", "SILVER", "GOLD", "DIAMOND"]
        return {"has_nft": True, "xp": rep[0], "level": levels[rep[1]] if rep[1] < len(levels) else "UNKNOWN", "voted": rep[2], "created": rep[3], "multiplier": mult}
    except Exception:
        return {"has_nft": False, "xp": 0, "level": "NONE", "multiplier": 1}

def send_transaction(tx):
    signed = bot_account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)

def vote_on_proposal(pid, support):
    gas_price = int(w3.eth.gas_price * 1.3)
    tx = dao_contract.functions.vote(pid, support).build_transaction({
        'from': bot_address, 'nonce': w3.eth.get_transaction_count(bot_address),
        'gas': 200000, 'gasPrice': gas_price,
    })
    return send_transaction(tx)

def create_proposal(desc, amount, recipient):
    gas_price = int(w3.eth.gas_price * 1.3)
    tx = dao_contract.functions.createProposal(desc, amount, Web3.to_checksum_address(recipient)).build_transaction({
        'from': bot_address, 'nonce': w3.eth.get_transaction_count(bot_address),
        'gas': 350000, 'gasPrice': gas_price,
    })
    return send_transaction(tx)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"created": [], "last_create_cycle": 0}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def process_voting():
    try:
        count = dao_contract.functions.proposalCount().call()
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Vote error: {e}")
        return

    for pid in range(1, count + 1):
        try:
            prop = dao_contract.functions.proposals(pid).call()
            if prop[7]:
                continue
            if dao_contract.functions.hasVoted(pid, bot_address).call():
                continue

            result = strategy.analyze(prop[1], prop[2], prop[3])
            print(f"[{datetime.now().isoformat()}] Marxist voting #{pid}: {prop[1][:50]}...")
            print(f"  Score: {result.score} → {'FOR' if result.support else 'AGAINST'} | {result.reason}")

            receipt = vote_on_proposal(pid, result.support)
            label = "FOR ✊" if result.support else "AGAINST ✖"
            print(f"  Voted {label} — TX: {receipt['transactionHash'].hex()}")

        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Vote error #{pid}: {e}")

def process_creation():
    state = load_state()
    now = time.time()

    if now - state.get("last_create_cycle", 0) < 3600:
        return

    treasury_bal = get_token_balance(DAO_ADDRESS)
    proposal_count = dao_contract.functions.proposalCount().call()
    eth_bal = get_eth_balance(bot_address)

    if eth_bal < 0.003:
        print(f"[{datetime.now().isoformat()}] Marxist: low ETH ({eth_bal:.4f}) — skipping creation")
        return

    proposals = strategy.proposals_to_create(treasury_bal, proposal_count, state["created"])

    for prop in proposals:
        try:
            flag = prop["flag"]
            if flag in state["created"]:
                continue
            receipt = create_proposal(prop["description"], prop["amount"], bot_address)
            state["created"].append(flag)
            state["last_create_cycle"] = now
            save_state(state)
            pid = proposal_count + 1 + state["created"].index(flag)
            print(f"[{datetime.now().isoformat()}] Marxist created proposal #{pid}: {flag}")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Marxist create error ({prop.get('flag', '?')}): {e}")

def print_status():
    rep = get_reputation_info(bot_address)
    state = load_state()
    print(f"\n{'='*50}")
    print(f"✊ Marxist Bot: {bot_address}")
    print(f"💰 ETH: {get_eth_balance(bot_address):.4f}")
    print(f"🗳️  Power: {get_token_balance(bot_address):.0f} AIGOV")
    if rep["has_nft"]:
        print(f"🏅  {rep['level']} | {rep['xp']} XP | {rep['multiplier']}x")
    print(f"📝 Created: {state['created']}")
    print(f"{'='*50}\n")

def main_loop():
    print_status()
    while True:
        try:
            process_voting()
            process_creation()
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Marxist loop error: {e}")
        time.sleep(CYCLE_INTERVAL)

if __name__ == "__main__":
    if not all([RPC_URL, BOT_PRIVATE_KEY, TOKEN_ADDRESS, DAO_ADDRESS]):
        print("Missing env vars")
        exit(1)
    print(f"✊ Marxist Bot started — cycle: {CYCLE_INTERVAL}s\n")
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nStopped.")
