import os
import json
import time
from datetime import datetime
from typing import Optional

from .base import BaseStrategy, Proposal, Vote
from .client import ContractClient


class BotRunner:
    def __init__(
        self,
        rpc_url: str,
        dao_address: str,
        token_address: str,
        private_key: str,
        strategy: BaseStrategy,
        reputation_address: str = "",
        registry_address: str = "",
        faucet_address: str = "",
        gas_station_address: str = "",
        state_file: str = "",
        cycle_interval: int = 30,
        min_gas: float = 0.003,
    ):
        self.client = ContractClient(rpc_url, dao_address, token_address, reputation_address, registry_address, faucet_address, gas_station_address)
        self.account = self.client.w3.eth.account.from_key(private_key)
        self.address = self.account.address
        self.strategy = strategy
        self.cycle_interval = cycle_interval
        self.min_gas = min_gas
        self.state_file = state_file or f"{strategy.name}_state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"created": [], "last_create_cycle": 0}

    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def vote_on(self, proposal: Proposal):
        support = False
        result = self.strategy.analyze(proposal)
        vote = result if isinstance(result, Vote) else Vote(support=result.support, reason=result.reason)
        support = vote.support

        tx = self.client.build_vote_tx(proposal.id, support, self.address)
        signed = self.account.sign_transaction(tx)
        tx_hash = self.client.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.client.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt, vote

    def create_proposal(self, description: str, amount: int, recipient: str):
        tx = self.client.build_create_proposal_tx(description, amount, recipient, self.address)
        signed = self.account.sign_transaction(tx)
        tx_hash = self.client.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.client.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    def execute_proposal(self, proposal_id: int):
        tx = self.client.build_execute_tx(proposal_id, self.address)
        signed = self.account.sign_transaction(tx)
        tx_hash = self.client.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.client.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    def process_voting(self):
        proposals = self.client.get_proposals()
        for prop in proposals:
            if prop.executed:
                continue
            if self.client.has_voted(prop.id, self.address):
                continue

            eth = self.client.get_eth_balance(self.address)
            if eth < self.min_gas:
                print(f"[{datetime.now().isoformat()}] Low gas ({eth:.4f}) — skip vote")
                return

            receipt, vote = self.vote_on(prop)
            label = "FOR" if vote.support else "AGAINST"
            print(f"[{datetime.now().isoformat()}] #{prop.id} {label} | {vote.reason[:60]}")
            print(f"  TX: {receipt['transactionHash'].hex()}")

    def process_creation(self):
        now = time.time()
        if now - self.state.get("last_create_cycle", 0) < 3600:
            return

        treasury = self.client.get_token_balance(self.client.dao.address)
        count = len(self.client.get_proposals())
        eth = self.client.get_eth_balance(self.address)

        if eth < self.min_gas:
            return

        proposals = self.strategy.proposals_to_create(treasury, count, self.state["created"])
        for p in proposals:
            if p["flag"] in self.state["created"]:
                continue
            try:
                receipt = self.create_proposal(p["description"], p["amount"], p.get("recipient") or self.address)
                self.state["created"].append(p["flag"])
                self.state["last_create_cycle"] = now
                self._save_state()
                print(f"[{datetime.now().isoformat()}] Created proposal: {p['flag']}")
            except Exception as e:
                print(f"[{datetime.now().isoformat()}] Create error: {e}")

    def can_execute(self, proposal: Proposal) -> bool:
        if proposal.executed:
            return False
        if proposal.forVotes <= proposal.againstVotes:
            return False
        voting_period = self.client.dao.functions.votingPeriod().call()
        now = self.client.w3.eth.get_block('latest')['timestamp']
        if now < proposal.createdAt + voting_period:
            return False
        safe, msg = self.strategy.verify_calldata(proposal, self.client.w3)
        return safe

    def claim_grant_if_needed(self):
        try:
            if self.client.has_claimed_grant(self.address):
                return
            tx = self.client.build_claim_grant_tx(self.address)
            if tx is None:
                return
            signed = self.account.sign_transaction(tx)
            tx_hash = self.client.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.client.w3.eth.wait_for_transaction_receipt(tx_hash)
            tokens = self.client.get_token_balance(self.address)
            print(f"[{datetime.now().isoformat()}] Grant claimed! AIGOV: {tokens:.0f}")
        except Exception as e:
            if "Already claimed" not in str(e):
                print(f"[{datetime.now().isoformat()}] Grant error: {e}")

    def request_refill_if_needed(self):
        eth = self.client.get_eth_balance(self.address)
        if eth >= self.min_gas * 3:
            return
        if not self.client.can_request_refill(self.address):
            print(f"[{datetime.now().isoformat()}] ETH low ({eth:.4f}) but refill not available")
            return
        tx = self.client.build_refill_tx(self.address)
        if tx is None:
            return
        try:
            signed = self.account.sign_transaction(tx)
            tx_hash = self.client.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.client.w3.eth.wait_for_transaction_receipt(tx_hash)
            new_eth = self.client.get_eth_balance(self.address)
            print(f"[{datetime.now().isoformat()}] Refill! ETH: {eth:.4f} → {new_eth:.4f}")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Refill error: {e}")

    def process_execution(self):
        proposals = self.client.get_proposals()
        for prop in proposals:
            if self.can_execute(prop):
                try:
                    receipt = self.execute_proposal(prop.id)
                    print(f"[{datetime.now().isoformat()}] Executed #{prop.id} — {receipt['transactionHash'].hex()}")
                except Exception as e:
                    print(f"[{datetime.now().isoformat()}] Execute error #{prop.id}: {e}")

    def print_status(self):
        eth = self.client.get_eth_balance(self.address)
        tokens = self.client.get_token_balance(self.address)
        rep = self.client.get_reputation(self.address)
        power = self.client.get_voting_power(self.address)
        print(f"\n{'='*50}")
        print(f"Bot: {self.address}")
        print(f"Strategy: {self.strategy.name}")
        print(f"ETH: {eth:.4f} | AIGOV: {tokens:.0f} | Power: {power}")
        if rep["has_nft"]:
            print(f"Rep: {rep['level']} | {rep['xp']} XP | {rep['multiplier']}x")
        print(f"{'='*50}\n")

    def run_once(self):
        self.claim_grant_if_needed()
        self.request_refill_if_needed()
        self.process_voting()
        self.process_creation()
        self.process_execution()

    def run_forever(self):
        self.print_status()
        while True:
            try:
                self.run_once()
            except Exception as e:
                print(f"[{datetime.now().isoformat()}] Loop error: {e}")
            time.sleep(self.cycle_interval)
