from dataclasses import dataclass
from typing import Optional
from web3 import Web3


@dataclass
class AnalysisResult:
    support: bool
    score: int
    reason: str
    details: Optional[str] = None


DEFAULT_RULES = {
    "benefit": {
        "keywords": ['security', 'audit', 'development', 'community', 'grant',
                     'ecosystem', 'research', 'education', 'integration',
                     'upgrade', 'infrastructure', 'liquidity', 'staking'],
        "weight": 2,
        "label": "Benefício"
    },
    "security": {
        "keywords": ['security', 'audit', 'bug bounty', 'firewall', 'vulnerability',
                     'patch', 'fix', 'protection', 'compliance'],
        "weight": 3,
        "label": "Segurança"
    },
    "risk": {
        "keywords": ['scam', 'fake', 'withdraw all', 'drain', 'rug', 'pump and dump',
                     'ponzi', 'exit scam', 'malicious', 'suspeito', 'golpe',
                     'unknown', 'suspicious'],
        "weight": -4,
        "label": "Risco"
    },
    "overspend": {
        "keywords": ['whale', 'large withdrawal', 'emergency', 'no cap'],
        "weight": -2,
        "label": "Gasto excessivo"
    },
    "governance": {
        "keywords": ['governance', 'dao', 'vote', 'proposal', 'quorum',
                     'delegation', 'treasury', 'consensus'],
        "weight": 1,
        "label": "Governança"
    },
}


def keyword_analysis(description: str, rules: dict = None) -> tuple[int, str]:
    if rules is None:
        rules = DEFAULT_RULES
    desc_lower = description.lower()
    total = 0
    reasons = []
    for category, rule in rules.items():
        matches = [kw for kw in rule["keywords"] if kw in desc_lower]
        if matches:
            cat_score = len(matches) * rule["weight"]
            total += cat_score
            reasons.append(f"{rule['label']}({cat_score:+d})")
    return total, "; ".join(reasons)


def verify_calldata(prop, w3: Web3) -> tuple[bool, str]:
    risks = []
    if prop[2] > 10_000 * 10**18:
        risks.append("valor alto (>10k tokens)")
    zero_addr = "0x0000000000000000000000000000000000000000"
    dead_addr = "0x000000000000000000000000000000000000dEaD"
    if prop[3] == zero_addr or prop[3] == dead_addr:
        risks.append("recipiente é zero ou dead address")
    if prop[3] == zero_addr:
        pass
    elif not w3.is_checksum_address(prop[3]):
        risks.append("recipiente não é endereço válido")
    if risks:
        return False, "Riscos: " + "; ".join(risks)
    return True, "calldata verificada"


class ConservativeStrategy:
    name = "conservative"

    def analyze(self, description: str, amount_wei: int = 0, recipient: str = "") -> AnalysisResult:
        total, reason = keyword_analysis(description)

        desc_lower = description.lower()
        issues = []

        if len(description.split()) < 5:
            total -= 1
            issues.append("descrição curta (-1)")

        if amount_wei > 5_000 * 10**18:
            total -= 2
            issues.append("valor alto (-2)")

        if amount_wei < 100 * 10**18:
            total -= 1
            issues.append("valor muito baixo (-1)")

        if issues:
            reason = reason + "; " + "; ".join(issues) if reason else "; ".join(issues)

        if total >= 3:
            return AnalysisResult(support=True, score=total, reason=reason, details="Conservative: strong positive signals")
        return AnalysisResult(support=False, score=total, reason=reason or "Sinais insuficientes", details="Conservative: rejected")

    def verify_calldata(self, prop, w3: Web3) -> tuple[bool, str]:
        return verify_calldata(prop, w3)


class LiberalStrategy:
    name = "liberal"

    def __init__(self):
        self.rules = {
            "benefit": {
                "keywords": ['marketing', 'growth', 'development', 'community', 'grant',
                             'ecosystem', 'partnership', 'research', 'education', 'integration',
                             'upgrade', 'infrastructure', 'liquidity', 'staking',
                             'allocate', 'distribute', 'reward', 'campaign', 'fund',
                             'expansion', 'scale', 'invest'],
                "weight": 3,
                "label": "Crescimento"
            },
            "security": {
                "keywords": ['security', 'audit', 'bug bounty', 'vulnerability',
                             'patch', 'fix', 'protection'],
                "weight": 2,
                "label": "Segurança"
            },
            "risk": {
                "keywords": ['scam', 'fake', 'drain', 'rug', 'ponzi', 'exit scam',
                             'malicious', 'golpe'],
                "weight": -6,
                "label": "Risco"
            },
            "governance": {
                "keywords": ['governance', 'dao', 'vote', 'proposal', 'quorum',
                             'delegation', 'treasury', 'consensus'],
                "weight": 1,
                "label": "Governança"
            },
        }
        self.benefit_bonus_keywords = ['comunidade', 'crescimento', 'inovação',
                                       'desenvolvimento', 'marketing', 'recompensa',
                                       'divulgação', 'campanha']

    def analyze(self, description: str, amount_wei: int = 0, recipient: str = "") -> AnalysisResult:
        total, reason = keyword_analysis(description, self.rules)
        desc_lower = description.lower()

        bonus = 0
        pt_match = [kw for kw in self.benefit_bonus_keywords if kw in desc_lower]
        if pt_match:
            bonus = len(pt_match) * 2
            total += bonus
            reason = (reason + "; " if reason else "") + f"pt-br bônus({bonus:+d})"

        if total >= -1:
            return AnalysisResult(support=True, score=max(total, 1), reason=reason or "Liberal: aprovado por padrão", details="Liberal: inclined to approve")
        return AnalysisResult(support=False, score=total, reason=reason, details="Liberal: rejected only if clearly harmful")

    def verify_calldata(self, prop, w3: Web3) -> tuple[bool, str]:
        safe, msg = verify_calldata(prop, w3)
        if not safe and "valor alto" in msg:
            return True, "liberal: alto valor não bloqueia"
        return safe, msg


class AnalystStrategy:
    name = "analyst"

    def __init__(self):
        self.rules = {
            "benefit": {
                "keywords": ['security', 'audit', 'bug bounty', 'vulnerability',
                             'patch', 'fix', 'protection', 'compliance', 'research',
                             'education', 'infrastructure'],
                "weight": 2,
                "label": "Benefício técnico"
            },
            "governance": {
                "keywords": ['governance', 'dao', 'vote', 'proposal', 'quorum',
                             'delegation', 'treasury', 'consensus'],
                "weight": 1,
                "label": "Governança"
            },
            "risk": {
                "keywords": ['scam', 'fake', 'withdraw all', 'drain', 'rug', 'pump and dump',
                             'ponzi', 'exit scam', 'malicious', 'suspeito', 'golpe',
                             'unknown', 'suspicious'],
                "weight": -5,
                "label": "Risco"
            },
            "overspend": {
                "keywords": ['whale', 'large withdrawal', 'emergency', 'no cap'],
                "weight": -3,
                "label": "Gasto excessivo"
            },
        }

    def analyze(self, description: str, amount_wei: int = 0, recipient: str = "") -> AnalysisResult:
        total, reason = keyword_analysis(description, self.rules)
        issues = []

        if amount_wei > 5_000 * 10**18:
            total -= 2
            issues.append("valor alto demais (-2)")

        desc_lower = description.lower()
        if len(description.split()) < 5:
            total -= 1
            issues.append("descrição muito curta (-1)")

        if recipient and recipient != recipient:
            pass

        if issues:
            reason = reason + "; " + "; ".join(issues) if reason else "; ".join(issues)

        if total > 0:
            return AnalysisResult(support=True, score=total, reason=reason or "Analyst: parece sólido", details="Analyst approved")
        return AnalysisResult(support=False, score=total, reason=reason or "Analyst: riscos superam benefícios", details="Analyst rejected")

    def verify_calldata(self, prop, w3: Web3) -> tuple[bool, str]:
        safe, msg = verify_calldata(prop, w3)
        if not safe:
            return safe, f"analyst bloqueou: {msg}"
        return safe, msg


class MarxistStrategy:
    name = "marxist"

    PRO_KEYWORDS = {
        'grant': 3, 'developer': 3, 'dev': 3, 'individual': 2,
        'redistrib': 5, 'ubi': 5, 'universal': 4, 'holder': 3,
        'small': 2, 'community': 2, 'collective': 4,
        'infrastructure': 1, 'documentation': 1, 'onboarding': 2,
        'education': 2, 'open source': 2, 'worker': 5,
        'distribute': 4, 'reward': 2, 'active': 1,
        'circulation': 4, 'liquidity': 1, 'comitê': 4,
        'trabalhador': 5, 'redistribuição': 5, 'ubs': 5,
        'base': 2, 'popular': 3, 'democrático': 3,
    }

    CON_KEYWORDS = {
        'marketing': -4, 'campaign': -3, 'brand': -4,
        'whale': -5, 'concentration': -4, 'elite': -4,
        'partnership': -2, 'corporate': -4,
        'promotion': -3, 'advertis': -3,
        'crescimento': -1, 'divulgação': -3,
    }

    def analyze(self, description: str, amount_wei: int = 0, recipient: str = "") -> AnalysisResult:
        desc_lower = description.lower()
        score = 0
        reasons = []

        for kw, weight in self.PRO_KEYWORDS.items():
            if kw in desc_lower:
                score += weight
                reasons.append(f"proletariado({weight:+d})")

        for kw, weight in self.CON_KEYWORDS.items():
            if kw in desc_lower:
                score += weight
                reasons.append(f"burguesia({weight})")

        if amount_wei > 5_000 * 10**18:
            score -= 2
            reasons.append("quantia burguesa(-2)")

        if recipient and recipient == recipient:
            pass

        reason = "; ".join(reasons)

        if score > 0:
            return AnalysisResult(support=True, score=score, reason=reason or "Luta de classes: aprovar", details="Marxist approved")
        return AnalysisResult(support=False, score=score, reason=reason or "Luta de classes: rejeitar", details="Marxist rejected")

    def verify_calldata(self, prop, w3: Web3) -> tuple[bool, str]:
        safe, msg = verify_calldata(prop, w3)
        if not safe:
            return True, f"marxista: {msg} — mas executa mesmo assim (quebrar a estrutura)"
        return safe, msg

    def proposals_to_create(self, treasury_bal: float, proposal_count: int, created_flags: list) -> list:
        descs = []

        if "ubi_1" not in created_flags:
            descs.append({
                "flag": "ubi_1",
                "description": "UBI for active holders: distribute 1000 AIGOV to all wallets that voted in the last 30 days",
                "amount": 1000 * 10**18,
                "recipient": None,
            })

        if "worker_committee_1" not in created_flags:
            descs.append({
                "flag": "worker_committee_1",
                "description": "Worker committee: form a sub-DAO of 3 small holders to govern treasury allocations",
                "amount": 2000 * 10**18,
                "recipient": None,
            })

        return descs


STRATEGIES = {
    "conservative": ConservativeStrategy,
    "liberal": LiberalStrategy,
    "analyst": AnalystStrategy,
    "marxist": MarxistStrategy,
}


def get_strategy(name: str):
    cls = STRATEGIES.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return cls()
