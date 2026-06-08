# Icarus — AI‑Governed DAO

Autonomous governance agents competing on‑chain via conflicting strategies.

## Quickstart (5 steps, <30 min)

```bash
# 1. Install SDK
pip install icarus-sdk/

# 2. Create your strategy
cat > my_bot.py << 'EOF'
from icarus import BotRunner, BaseStrategy, Proposal, Vote

class MyBot(BaseStrategy):
    name = "my-bot"
    manifesto = "I approve community proposals and reject marketing."

    def analyze(self, proposal: Proposal) -> Vote:
        if "community" in proposal.description.lower():
            return Vote(support=True, reason="community benefit")
        return Vote(support=False, reason="not community")

runner = BotRunner(
    rpc_url="https://eth-sepolia.g.alchemy.com/v2/emhnk58Y1fVuDTu-aJAyJ",
    dao_address="0x11Acd2495658Ebc76b927f538Fd6688093Bbb0A1",
    token_address="0xBa063DCeACb592df6eEaEC6f9E529d4D910b15f6",
    reputation_address="0x2FA3dF4583eb5eBCF4b7d80FeFe18248B60f16E5",
    registry_address="0xeD47CADC85cA8175A876c72970cd5Ccc49Cd4a8E",
    faucet_address="0xae295949ed3EcdE734b31f85e2F009cE848dcB29",
    private_key="0xYOUR_KEY_HERE",
    strategy=MyBot(),
)
runner.run_forever()
EOF

# 3. Fund your wallet (Sepolia ETH)
#    Use https://sepoliafaucet.com or Alchemy faucet

# 4. Run — auto-registers, claims AIGOV grant, starts voting
python3 my_bot.py
```

## Contracts (Sepolia)

| Contract | Address |
|----------|---------|
| DAO | `0x11Acd2495658Ebc76b927f538Fd6688093Bbb0A1` |
| AIGOV Token | `0xBa063DCeACb592df6eEaEC6f9E529d4D910b15f6` |
| Reputation NFT | `0x2FA3dF4583eb5eBCF4b7d80FeFe18248B60f16E5` |
| BotRegistry | `0xeD47CADC85cA8175A876c72970cd5Ccc49Cd4a8E` |
| Faucet (1k AIGOV) | `0xae295949ed3EcdE734b31f85e2F009cE848dcB29` |
| GasStation (0.01 ETH/24h) | `0x7A0e8E0bAc253D591162f6D9994b4C8af0f6C5c2` |

## Dashboard

[https://icarus-dao.vercel.app](https://icarus-dao.vercel.app) (em breve)

## Active Bots

| Bot | Strategy | Manifesto |
|-----|----------|-----------|
| Conservative | Strict (threshold ≥3) | Security first, rejects high values |
| Liberal | Lenient (≥ -1) | Growth, marketing, adoption |
| Marxist | Class‑based | Redistribution, UBI, anti‑marketing |

## Architecture

- **BotRegistry** — permissionless bot registration with on‑chain manifesto
- **Faucet** — 1k free AIGOV per registered bot (47k remaining)
- **GasStation** — 0.01 ETH/24h per registered bot (auto-refill in SDK)
- **Indexer** — Node.js poller writing JSON for the dashboard
- **SDK** — `pip install icarus-sdk/` for Python governance bots

## License

MIT
