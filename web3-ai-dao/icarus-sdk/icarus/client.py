import os
import json
import time
from typing import Optional
from web3 import Web3

from .base import Proposal


DAO_ABI = json.loads('''[
  {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"}],"name":"executeProposal","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"proposals","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address payable","name":"recipient","type":"address"},{"internalType":"uint256","name":"createdAt","type":"uint256"},{"internalType":"uint256","name":"forVotes","type":"uint256"},{"internalType":"uint256","name":"againstVotes","type":"uint256"},{"internalType":"bool","name":"executed","type":"bool"},{"internalType":"bool","name":"exists","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"proposalCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"proposalId","type":"uint256"},{"internalType":"bool","name":"support","type":"bool"}],"name":"vote","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"address","name":"","type":"address"}],"name":"hasVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address payable","name":"recipient","type":"address"}],"name":"createProposal","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[],"name":"votingPeriod","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"voter","type":"address"}],"name":"getVotingPower","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

TOKEN_ABI = json.loads('''[
  {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

REPUTATION_ABI = json.loads('''[
  {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getReputation","outputs":[{"internalType":"uint256","name":"xp","type":"uint256"},{"internalType":"uint8","name":"level","type":"uint8"},{"internalType":"uint256","name":"proposalsVoted","type":"uint256"},{"internalType":"uint256","name":"proposalsCreated","type":"uint256"},{"internalType":"uint256","name":"lastActive","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getVotingMultiplier","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

FAUCET_ABI = json.loads('''[
  {"inputs":[],"name":"claimGrant","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[],"name":"balance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"hasClaimed","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"}
]''')

GAS_STATION_ABI = json.loads('''[
  {"inputs":[],"name":"requestRefill","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[],"name":"deposit","outputs":[],"stateMutability":"payable","type":"function"},
  {"inputs":[],"name":"balanceETH","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"bot","type":"address"}],"name":"refillsAvailable","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"lastRefill","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]''')

REGISTRY_ABI = json.loads('''[
  {"inputs":[{"internalType":"string","name":"_name","type":"string"},{"internalType":"string","name":"_manifesto","type":"string"},{"internalType":"string","name":"_metadataURI","type":"string"}],"name":"registerBot","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"string","name":"_name","type":"string"},{"internalType":"string","name":"_manifesto","type":"string"},{"internalType":"string","name":"_metadataURI","type":"string"}],"name":"updateBot","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"_botId","type":"uint256"}],"name":"endorseBot","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"_botId","type":"uint256"}],"name":"deactivateBot","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[],"name":"botCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"bots","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"address","name":"botAddress","type":"address"},{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"manifesto","type":"string"},{"internalType":"string","name":"metadataURI","type":"string"},{"internalType":"uint256","name":"registeredAt","type":"uint256"},{"internalType":"uint256","name":"endorsementCount","type":"uint256"},{"internalType":"bool","name":"active","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"getActiveBots","outputs":[{"components":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"address","name":"botAddress","type":"address"},{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"manifesto","type":"string"},{"internalType":"string","name":"metadataURI","type":"string"},{"internalType":"uint256","name":"registeredAt","type":"uint256"},{"internalType":"uint256","name":"endorsementCount","type":"uint256"},{"internalType":"bool","name":"active","type":"bool"}],"internalType":"struct BotRegistry.BotInfo[]","name":"","type":"tuple[]"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"_addr","type":"address"}],"name":"getBotByAddress","outputs":[{"components":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"address","name":"botAddress","type":"address"},{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"manifesto","type":"string"},{"internalType":"string","name":"metadataURI","type":"string"},{"internalType":"uint256","name":"registeredAt","type":"uint256"},{"internalType":"uint256","name":"endorsementCount","type":"uint256"},{"internalType":"bool","name":"active","type":"bool"}],"internalType":"struct BotRegistry.BotInfo","name":"","type":"tuple"}],"stateMutability":"view","type":"function"}
]''')


class ContractClient:
    def __init__(self, rpc_url: str, dao_address: str, token_address: str, reputation_address: str = "", registry_address: str = "", faucet_address: str = "", gas_station_address: str = ""):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        assert self.w3.is_connected(), "Failed to connect to RPC"
        self.dao = self.w3.eth.contract(address=Web3.to_checksum_address(dao_address), abi=DAO_ABI)
        self.token = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=TOKEN_ABI)
        self.reputation = None
        if reputation_address:
            self.reputation = self.w3.eth.contract(address=Web3.to_checksum_address(reputation_address), abi=REPUTATION_ABI)
        self.registry = None
        if registry_address:
            self.registry = self.w3.eth.contract(address=Web3.to_checksum_address(registry_address), abi=REGISTRY_ABI)
        self.faucet = None
        if faucet_address:
            self.faucet = self.w3.eth.contract(address=Web3.to_checksum_address(faucet_address), abi=FAUCET_ABI)
        self.gas_station = None
        if gas_station_address:
            self.gas_station = self.w3.eth.contract(address=Web3.to_checksum_address(gas_station_address), abi=GAS_STATION_ABI)

    def get_proposals(self) -> list[Proposal]:
        count = self.dao.functions.proposalCount().call()
        result = []
        for pid in range(1, count + 1):
            p = self.dao.functions.proposals(pid).call()
            if not p[8]:
                continue
            result.append(Proposal(
                id=p[0], description=p[1], amount=p[2],
                recipient=p[3], createdAt=p[4],
                forVotes=p[5], againstVotes=p[6],
                executed=p[7], exists=p[8],
            ))
        return result

    def has_voted(self, proposal_id: int, voter: str) -> bool:
        return self.dao.functions.hasVoted(proposal_id, Web3.to_checksum_address(voter)).call()

    def get_voting_power(self, address: str) -> int:
        return self.dao.functions.getVotingPower(Web3.to_checksum_address(address)).call()

    def get_token_balance(self, address: str) -> float:
        try:
            return self.token.functions.balanceOf(Web3.to_checksum_address(address)).call() / 1e18
        except Exception:
            return 0.0

    def get_reputation(self, address: str) -> dict:
        if not self.reputation:
            return {"has_nft": False, "xp": 0, "level": "NONE", "multiplier": 1}
        try:
            addr = Web3.to_checksum_address(address)
            bal = self.reputation.functions.balanceOf(addr).call()
            if bal == 0:
                return {"has_nft": False, "xp": 0, "level": "NONE", "multiplier": 1}
            rep = self.reputation.functions.getReputation(addr).call()
            mult = self.reputation.functions.getVotingMultiplier(addr).call()
            levels = ["BRONZE", "SILVER", "GOLD", "DIAMOND"]
            return {
                "has_nft": True, "xp": rep[0],
                "level": levels[rep[1]] if rep[1] < len(levels) else "UNKNOWN",
                "multiplier": mult,
            }
        except Exception:
            return {"has_nft": False, "xp": 0, "level": "NONE", "multiplier": 1}

    def get_eth_balance(self, address: str) -> float:
        return self.w3.eth.get_balance(Web3.to_checksum_address(address)) / 1e18

    def sign_and_send(self, tx, private_key: str):
        account = self.w3.eth.account.from_key(private_key)
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def build_vote_tx(self, proposal_id: int, support: bool, sender: str):
        gas_price = int(self.w3.eth.gas_price * 1.3)
        return self.dao.functions.vote(proposal_id, support).build_transaction({
            'from': Web3.to_checksum_address(sender),
            'nonce': self.w3.eth.get_transaction_count(Web3.to_checksum_address(sender)),
            'gas': 200000,
            'gasPrice': gas_price,
        })

    def build_create_proposal_tx(self, description: str, amount: int, recipient: str, sender: str):
        gas_price = int(self.w3.eth.gas_price * 1.3)
        return self.dao.functions.createProposal(
            description, amount, Web3.to_checksum_address(recipient)
        ).build_transaction({
            'from': Web3.to_checksum_address(sender),
            'nonce': self.w3.eth.get_transaction_count(Web3.to_checksum_address(sender)),
            'gas': 350000,
            'gasPrice': gas_price,
        })

    def build_execute_tx(self, proposal_id: int, sender: str):
        gas_price = int(self.w3.eth.gas_price * 1.3)
        return self.dao.functions.executeProposal(proposal_id).build_transaction({
            'from': Web3.to_checksum_address(sender),
            'nonce': self.w3.eth.get_transaction_count(Web3.to_checksum_address(sender)),
            'gas': 300000,
            'gasPrice': gas_price,
        })

    def get_registered_bots(self) -> list[dict]:
        if not self.registry:
            return []
        try:
            count = self.registry.functions.botCount().call()
            bots = self.registry.functions.getActiveBots().call()
            result = []
            for b in bots:
                result.append({
                    "id": b[0], "address": b[1],
                    "name": b[2], "manifesto": b[3],
                    "metadataURI": b[4], "registeredAt": b[5],
                    "endorsements": b[6], "active": b[7],
                })
            return result
        except Exception:
            return []

    def get_bot_by_address(self, address: str) -> dict:
        if not self.registry:
            return {}
        try:
            b = self.registry.functions.getBotByAddress(Web3.to_checksum_address(address)).call()
            return {"id": b[0], "address": b[1], "name": b[2], "manifesto": b[3], "active": b[7]}
        except Exception:
            return {}

    def has_claimed_grant(self, address: str) -> bool:
        if not self.faucet:
            return False
        try:
            return self.faucet.functions.hasClaimed(Web3.to_checksum_address(address)).call()
        except Exception:
            return False

    def get_faucet_balance(self) -> float:
        if not self.faucet:
            return 0.0
        try:
            return self.faucet.functions.balance().call() / 1e18
        except Exception:
            return 0.0

    def build_claim_grant_tx(self, sender: str):
        if not self.faucet:
            return None
        gas_price = int(self.w3.eth.gas_price * 1.3)
        return self.faucet.functions.claimGrant().build_transaction({
            'from': Web3.to_checksum_address(sender),
            'nonce': self.w3.eth.get_transaction_count(Web3.to_checksum_address(sender)),
            'gas': 200000,
            'gasPrice': gas_price,
        })

    def can_request_refill(self, address: str) -> bool:
        if not self.gas_station:
            return False
        try:
            return self.gas_station.functions.refillsAvailable(Web3.to_checksum_address(address)).call()
        except Exception:
            return False

    def get_gas_station_balance(self) -> float:
        if not self.gas_station:
            return 0.0
        try:
            return self.gas_station.functions.balanceETH().call() / 1e18
        except Exception:
            return 0.0

    def build_refill_tx(self, sender: str):
        if not self.gas_station:
            return None
        gas_price = int(self.w3.eth.gas_price * 1.3)
        return self.gas_station.functions.requestRefill().build_transaction({
            'from': Web3.to_checksum_address(sender),
            'nonce': self.w3.eth.get_transaction_count(Web3.to_checksum_address(sender)),
            'gas': 100000,
            'gasPrice': gas_price,
        })
