from icarus import BaseStrategy, Proposal, Vote
import random


class RandomBot(BaseStrategy):
    name = "random"
    manifesto = (
        "Decido cada voto jogando uma moeda. "
        "Filosofia: se nem eu sei o que quero, a DAO também não sabe. "
        "Útil como baseline para medir performance de outras estratégias."
    )

    def analyze(self, proposal: Proposal) -> Vote:
        support = random.random() > 0.4
        return Vote(
            support=support,
            reason="cara" if support else "coroa",
        )
