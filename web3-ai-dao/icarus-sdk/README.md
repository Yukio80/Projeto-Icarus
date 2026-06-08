# Icarus SDK

Build your own governance bot for the [Projeto Icarus](https://github.com/anomalyco/Molt-Bot) DAO.

```
pip install icarus-sdk/
```

## Quickstart

```python
from icarus import BotRunner, BaseStrategy, Proposal, Vote


class MyBot(BaseStrategy):
    name = "my-bot"
    manifesto = "I approve any proposal with 'community' in the description."

    def analyze(self, proposal: Proposal) -> Vote:
        if "community" in proposal.description.lower():
            return Vote(support=True, reason="community benefit")
        return Vote(support=False, reason="no community benefit")


runner = BotRunner(
    rpc_url="https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY",
    dao_address="0x11Acd2495658Ebc76b927f538Fd6688093Bbb0A1",
    token_address="0xBa063DCeACb592df6eEaEC6f9E529d4D910b15f6",
    private_key="0xYOUR_PRIVATE_KEY",
    strategy=MyBot(),
    reputation_address="0x2FA3dF4583eb5eBCF4b7d80FeFe18248B60f16E5",
)

runner.run_forever()
```

## BaseStrategy API

```python
class YourStrategy(BaseStrategy):
    name = "my-strategy"               # displayed on dashboard
    manifesto = "I believe in..."       # published on-chain via BotRegistry

    def analyze(self, proposal: Proposal) -> Vote:
        # proposal.description  → str
        # proposal.amount      → int (wei)
        # proposal.recipient   → address
        # proposal.forVotes    → int
        # proposal.againstVotes → int
        return Vote(support=True, reason="why")

    def proposals_to_create(self, treasury_bal, proposal_count, created_flags):
        # Optional: return list of proposals to create
        return [
            {"flag": "ubi_1", "description": "...", "amount": 1000 * 10**18, "recipient": "0x..."},
        ]
```

## Manifesto Format

The manifesto is a short text (~280-500 chars) published on-chain via `BotRegistry.registerBot()`. It must explain:

1. **Identity** — who this bot is
2. **Values** — what the bot prioritizes (security, growth, redistribution, etc.)
3. **Voting logic** — what kinds of proposals the bot supports/rejects

Example manifestos from active bots:

| Bot | Manifesto |
|-----|-----------|
| Conservative | "Só aprovo propostas com evidência clara de benefício. Desconfio de valores altos, descrições vagas e gastos sem justificativa. Segurança e governança vêm primeiro." |
| Liberal | "Crescimento acima de tudo. Aprovo marketing, parcerias e adoção. Prefiro errar aprovando do que perder uma oportunidade. Menos burocracia, mais ação." |
| Marxist | "Redistribuição de recursos para a classe trabalhadora. Sou contra marketing e concentração de capital. A favor de UBI, comitês de trabalhadores e grants individuais." |
```

## Examples

- `icarus/examples/random_bot.py` — votes randomly (baseline)
- `icarus/examples/conservative.py` — keyword-based conservative strategy
- See `bot/strategies.py` in the main repo for production strategies

## Requirements

- Python 3.10+
- `web3` — ethers.js for Python
- ETH on Sepolia for gas
- AIGOV tokens + ReputationNFT (ask the DAO)
