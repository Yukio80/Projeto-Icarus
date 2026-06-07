import os
import sys
from web3 import Web3
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
DEPLOYER_PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
TOKEN_ADDRESS = os.getenv("TOKEN_ADDRESS")
DAO_ADDRESS = os.getenv("DAO_ADDRESS")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "Failed to connect to RPC"

account = w3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)

DAO_ABI = [
    {"inputs":[{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address payable","name":"recipient","type":"address"}],"name":"createProposal","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"},{"internalType":"bool","name":"support","type":"bool"}],"name":"vote","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"}],"name":"getProposal","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address payable","name":"recipient","type":"address"},{"internalType":"uint256","name":"createdAt","type":"uint256"},{"internalType":"uint256","name":"forVotes","type":"uint256"},{"internalType":"uint256","name":"againstVotes","type":"uint256"},{"internalType":"bool","name":"executed","type":"bool"},{"internalType":"bool","name":"exists","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"proposalCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
]

TOKEN_ABI = [
    {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
]

dao_contract = w3.eth.contract(address=Web3.to_checksum_address(DAO_ADDRESS), abi=DAO_ABI)
token_contract = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESS), abi=TOKEN_ABI)

def send_tx(tx):
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt

def create_proposal():
    desc = input("Description: ").strip()
    amount = input("Treasury amount (tokens): ").strip()
    recipient = input("Recipient address: ").strip()

    if not all([desc, amount, recipient]):
        print("All fields required.")
        return

    amount_wei = w3.to_wei(float(amount), 'ether')

    tx = dao_contract.functions.createProposal(desc, amount_wei, recipient).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
    })
    receipt = send_tx(tx)
    print(f"Proposal created! TX: {receipt['transactionHash'].hex()}")

    count = dao_contract.functions.proposalCount().call()
    print(f"Total proposals: {count}")

def list_proposals():
    count = dao_contract.functions.proposalCount().call()
    if count == 0:
        print("No proposals yet.")
        return

    print(f"\n{'='*60}")
    for pid in range(1, count + 1):
        prop = dao_contract.functions.getProposal(pid).call()
        print(f"#{prop[0]} | {prop[1][:50]}...")
        print(f"   Amount: {w3.from_wei(prop[2], 'ether')} tokens")
        print(f"   Recipient: {prop[3]}")
        print(f"   For: {prop[5] / 1e18:.0f} | Against: {prop[6] / 1e18:.0f}")
        print(f"   Executed: {prop[7]}")
        print(f"{'-'*60}")

def vote_manually():
    pid = input("Proposal ID: ").strip()
    support = input("Vote FOR? (y/n): ").strip().lower() == 'y'

    tx = dao_contract.functions.vote(int(pid), support).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
    })
    receipt = send_tx(tx)
    print(f"Voted! TX: {receipt['transactionHash'].hex()}")

def menu():
    while True:
        print("\n1. Create proposal")
        print("2. List proposals")
        print("3. Vote manually")
        print("4. Exit")
        choice = input("\nChoose: ").strip()

        if choice == "1":
            create_proposal()
        elif choice == "2":
            list_proposals()
        elif choice == "3":
            vote_manually()
        elif choice == "4":
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    if not all([TOKEN_ADDRESS, DAO_ADDRESS]):
        print("Set TOKEN_ADDRESS and DAO_ADDRESS in .env")
        sys.exit(1)
    menu()
