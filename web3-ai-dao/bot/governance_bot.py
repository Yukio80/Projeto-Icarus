import os
import time
import json
import re
import threading
from datetime import datetime
from typing import Optional

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
REPUTATION_NFT_ADDRESS = os.getenv("REPUTATION_NFT_ADDRESS", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

CYCLE_INTERVAL = int(os.getenv("BOT_CYCLE_INTERVAL", "30"))

GEMINI_AVAILABLE = False
if GEMINI_API_KEY:
    try:
        import google.genai as genai
        GEMINI_AVAILABLE = True
    except Exception as e:
        print(f"Gemini init failed: {e}")

DEEPSEEK_AVAILABLE = False
if DEEPSEEK_API_KEY:
    try:
        from openai import OpenAI
        DEEPSEEK_AVAILABLE = True
    except Exception as e:
        print(f"DeepSeek init failed: {e}")

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
  {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"delegates","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"voter","type":"address"}],"name":"getVotingPower","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"votingPeriod","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

TOKEN_ABI = json.loads('''[
  {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}
]''')

dao_contract = w3.eth.contract(address=Web3.to_checksum_address(DAO_ADDRESS), abi=DAO_ABI)
token_contract = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESS), abi=TOKEN_ABI)

REPUTATION_ABI = json.loads('''[
  {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getReputation","outputs":[{"internalType":"uint256","name":"xp","type":"uint256"},{"internalType":"uint8","name":"level","type":"uint8"},{"internalType":"uint256","name":"proposalsVoted","type":"uint256"},{"internalType":"uint256","name":"proposalsCreated","type":"uint256"},{"internalType":"uint256","name":"lastActive","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getVotingMultiplier","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"recordVote","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

reputation_contract = None
if REPUTATION_NFT_ADDRESS:
    reputation_contract = w3.eth.contract(
        address=Web3.to_checksum_address(REPUTATION_NFT_ADDRESS),
        abi=REPUTATION_ABI
    )

def get_eth_balance(address: str) -> float:
    return w3.eth.get_balance(Web3.to_checksum_address(address)) / 1e18

def get_token_balance(address: str) -> float:
    try:
        return token_contract.functions.balanceOf(Web3.to_checksum_address(address)).call() / 1e18
    except Exception:
        return 0.0

def get_reputation_info(address: str) -> dict:
    if not reputation_contract:
        return {"has_nft": False, "xp": 0, "level": "NONE", "multiplier": 1}
    try:
        bal = reputation_contract.functions.balanceOf(Web3.to_checksum_address(address)).call()
        if bal == 0:
            return {"has_nft": False, "xp": 0, "level": "NONE", "multiplier": 1}
        rep = reputation_contract.functions.getReputation(Web3.to_checksum_address(address)).call()
        mult = reputation_contract.functions.getVotingMultiplier(Web3.to_checksum_address(address)).call()
        levels = ["BRONZE", "SILVER", "GOLD", "DIAMOND"]
        return {
            "has_nft": True,
            "xp": rep[0],
            "level": levels[rep[1]] if rep[1] < len(levels) else "UNKNOWN",
            "voted": rep[2],
            "created": rep[3],
            "multiplier": mult,
        }
    except Exception:
        return {"has_nft": False, "xp": 0, "level": "NONE", "multiplier": 1}

def _build_analysis_prompt(description: str, amount_wei: int, recipient: str) -> str:
    return (
        'You are an AI governance analyst for a DAO.\n'
        'Analyze this proposal and respond with ONLY a JSON object:\n\n'
        '{"support": true/false, "reason": "short explanation in Portuguese, max 15 words"}\n\n'
        f'Proposal: {description}\n'
        f'Amount: {amount_wei / 1e18:.0f} tokens\n'
        f'Recipient: {recipient}\n\n'
        'Rules:\n'
        '- Say true if it benefits the community\n'
        '- Say false if it is suspicious, scam, drain, or harmful\n'
        '- Be conservative: if uncertain, say false'
    )

def _parse_llm_response(text: str, source: str) -> tuple[bool, int, str] | None:
    try:
        clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
        result = json.loads(clean)
        support = bool(result.get("support", False))
        reason = result.get("reason", "")
        score = 5 if support else -5
        print(f"  {source}: {reason}")
        return support, score, reason
    except Exception:
        return None

def analyze_proposal(description: str, amount_wei: int = 0, recipient: str = "") -> tuple[bool, int, str]:
    prompt = _build_analysis_prompt(description, amount_wei, recipient)

    if GEMINI_AVAILABLE:
        try:
            import google.genai as genai
            client = genai.Client(api_key=GEMINI_API_KEY, http_options={"timeout": 10000})
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            result = _parse_llm_response(resp.text, "Gemini")
            if result:
                return result
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                print("  Gemini: quota exaurida")
            else:
                print(f"  Gemini error: {e}")

    if DEEPSEEK_AVAILABLE:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            result = _parse_llm_response(resp.choices[0].message.content, "DeepSeek")
            if result:
                return result
        except Exception as e:
            print(f"  DeepSeek error: {e}")

    desc_lower = description.lower()

    positive_keywords = [
        'marketing', 'growth', 'security', 'audit', 'development',
        'community', 'grant', 'ecosystem', 'partnership', 'research',
        'education', 'open source', 'integration', 'upgrade', 'bug bounty',
        'infrastructure', 'governance', 'staking', 'liquidity', 'dao'
    ]

    negative_keywords = [
        'scam', 'fake', 'withdraw all', 'drain', 'rug', 'pump and dump',
        'ponzi', 'exit scam', 'malicious'
    ]

    score = 0
    for kw in positive_keywords:
        if kw in desc_lower:
            score += 1
    for kw in negative_keywords:
        if kw in desc_lower:
            score -= 3

    return score > 0, score, ""

def send_transaction(tx):
    signed = bot_account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt

def vote_on_proposal(proposal_id: int, support: bool):
    tx = dao_contract.functions.vote(proposal_id, support).build_transaction({
        'from': bot_address,
        'nonce': w3.eth.get_transaction_count(bot_address),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
    })
    receipt = send_transaction(tx)
    return receipt

def execute_proposal(proposal_id: int):
    tx = dao_contract.functions.executeProposal(proposal_id).build_transaction({
        'from': bot_address,
        'nonce': w3.eth.get_transaction_count(bot_address),
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
    })
    receipt = send_transaction(tx)
    return receipt

def process_proposals():
    try:
        count = dao_contract.functions.proposalCount().call()
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Error reading proposal count: {e}")
        return

    for pid in range(1, count + 1):
        try:
            prop = dao_contract.functions.proposals(pid).call()
            if prop[7]:
                continue

            if not has_voted(pid):
                support, score, reason = analyze_proposal(prop[1], prop[2], prop[3])
                print(f"[{datetime.now().isoformat()}] Proposal #{pid}: {prop[1][:60]}...")
                print(f"  Score: {score} → {'FOR' if support else 'AGAINST'}{' | ' + reason if reason else ''}")

                if support:
                    receipt = vote_on_proposal(pid, True)
                    print(f"  Voted FOR — TX: {receipt['transactionHash'].hex()}")
                else:
                    receipt = vote_on_proposal(pid, False)
                    print(f"  Voted AGAINST — TX: {receipt['transactionHash'].hex()}")
            else:
                print(f"[{datetime.now().isoformat()}] Already voted on #{pid}")

            if can_execute(pid, prop):
                receipt = execute_proposal(pid)
                print(f"[{datetime.now().isoformat()}] Executed proposal #{pid} — TX: {receipt['transactionHash'].hex()}")

        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Error processing #{pid}: {e}")

def has_voted(proposal_id: int) -> bool:
    try:
        return dao_contract.functions.hasVoted(proposal_id, bot_address).call()
    except Exception:
        return False

def can_execute(proposal_id: int, prop) -> bool:
    if prop[7]:
        return False
    if not prop[5] > prop[6]:
        return False
    now = w3.eth.get_block('latest')['timestamp']
    if now < prop[4] + dao_contract.functions.votingPeriod().call():
        return False
    return True

def print_status():
    eth_bal = get_eth_balance(bot_address)
    token_bal = get_token_balance(bot_address)
    rep = get_reputation_info(bot_address)
    print(f"\n{'='*50}")
    print(f"🤖 Bot: {bot_address}")
    print(f"⛓️  Chain ID: {w3.eth.chain_id}")
    print(f"💰 ETH: {eth_bal:.2f}")
    print(f"🗳️  Voting Power: {token_bal:.2f} tokens")
    if rep["has_nft"]:
        effective = token_bal * rep["multiplier"]
        print(f"🏅  Reputation: {rep['level']} | {rep['xp']} XP | {rep['multiplier']}x voting multiplier")
        print(f"📊  Proposals voted: {rep['voted']} | created: {rep['created']} | Effective power: {effective:.0f}")
    print(f"📡 RPC: {RPC_URL}")
    print(f"{'='*50}\n")

def main_loop():
    print_status()

    while True:
        try:
            process_proposals()
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Loop error: {e}")

        time.sleep(CYCLE_INTERVAL)

if __name__ == "__main__":
    if not all([RPC_URL, BOT_PRIVATE_KEY, TOKEN_ADDRESS, DAO_ADDRESS]):
        print("Missing env vars. Check .env")
        exit(1)

    print("AI Governance Bot started")
    print(f"Cycle interval: {CYCLE_INTERVAL}s\n")

    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
