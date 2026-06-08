from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Proposal:
    id: int
    description: str
    amount: int
    recipient: str
    createdAt: int
    forVotes: int
    againstVotes: int
    executed: bool
    exists: bool


@dataclass
class Vote:
    support: bool
    reason: str = ""


@dataclass
class AnalysisResult:
    support: bool
    score: int
    reason: str
    details: Optional[str] = None


class BaseStrategy:
    name: str = "base"
    manifesto: str = ""

    def analyze(self, proposal: Proposal) -> Vote:
        raise NotImplementedError

    def verify_calldata(self, proposal: Proposal, w3=None) -> tuple[bool, str]:
        return True, "ok"

    def proposals_to_create(self, treasury_bal: float, proposal_count: int, created_flags: list) -> list:
        return []
