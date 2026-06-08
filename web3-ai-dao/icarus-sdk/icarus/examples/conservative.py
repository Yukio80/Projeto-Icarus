from icarus import BaseStrategy, Proposal, Vote


class ConservativeBot(BaseStrategy):
    name = "conservative"
    manifesto = (
        "Só aprovo propostas com evidência clara de benefício. "
        "Desconfio de valores altos, descrições vagas e gastos sem justificativa. "
        "Segurança e governança vêm primeiro."
    )

    BENEFIT_KW = ['security', 'audit', 'development', 'community', 'grant',
                  'research', 'education', 'infrastructure', 'upgrade']
    RISK_KW = ['scam', 'drain', 'rug', 'ponzi', 'malicious', 'golpe', 'suspeito']
    OVERSPEND_KW = ['whale', 'no cap', 'emergency']

    def analyze(self, proposal: Proposal) -> Vote:
        desc = proposal.description.lower()
        score = 0
        reasons = []

        for kw in self.BENEFIT_KW:
            if kw in desc:
                score += 2
                reasons.append(f"benefício({kw})")

        for kw in self.RISK_KW:
            if kw in desc:
                score -= 4
                reasons.append(f"risco({kw})")

        for kw in self.OVERSPEND_KW:
            if kw in desc:
                score -= 2
                reasons.append(f"gasto({kw})")

        if proposal.amount > 5_000 * 10**18:
            score -= 2
            reasons.append("valor_alto")

        if len(proposal.description.split()) < 5:
            score -= 1
            reasons.append("desc_curta")

        if score >= 3:
            return Vote(support=True, reason="; ".join(reasons))
        return Vote(support=False, reason="; ".join(reasons) or "insuficiente")
