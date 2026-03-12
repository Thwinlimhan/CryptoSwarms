from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DebateVote:
    solver_id: str
    stance: str
    confidence: float
    rationale: str


@dataclass(frozen=True)
class DebateRound:
    round_index: int
    votes: list[DebateVote]
    dissent_solver_ids: list[str]


@dataclass(frozen=True)
class DebateAggregate:
    decision: str
    confidence: float
    dissent_ratio: float
    vote_count: int


def run_cross_critique(
    *,
    votes: list[DebateVote],
    rounds: int,
    confidence_decay_per_dissent: float = 0.06,
) -> list[DebateRound]:
    current = list(votes)
    history: list[DebateRound] = []
    total_rounds = max(1, int(rounds))

    for idx in range(total_rounds):
        stances = [v.stance for v in current]
        majority = _majority(stances)
        next_votes: list[DebateVote] = []
        dissenters: list[str] = []

        for vote in current:
            confidence = vote.confidence
            if vote.stance != majority:
                dissenters.append(vote.solver_id)
                confidence = max(0.05, confidence - confidence_decay_per_dissent)
            next_votes.append(
                DebateVote(
                    solver_id=vote.solver_id,
                    stance=vote.stance,
                    confidence=round(confidence, 4),
                    rationale=vote.rationale,
                )
            )

        history.append(DebateRound(round_index=idx + 1, votes=next_votes, dissent_solver_ids=dissenters))
        current = next_votes

    return history


def aggregate_weighted(votes: list[DebateVote]) -> DebateAggregate:
    if not votes:
        return DebateAggregate(decision="hold", confidence=0.0, dissent_ratio=0.0, vote_count=0)

    go_weight = sum(max(0.0, v.confidence) for v in votes if v.stance == "go")
    hold_weight = sum(max(0.0, v.confidence) for v in votes if v.stance != "go")
    total = max(1e-6, go_weight + hold_weight)

    if go_weight >= hold_weight:
        decision = "go"
        confidence = go_weight / total
    else:
        decision = "hold"
        confidence = hold_weight / total

    dissent_count = sum(1 for v in votes if v.stance != decision)
    return DebateAggregate(
        decision=decision,
        confidence=round(confidence, 4),
        dissent_ratio=round(dissent_count / float(len(votes)), 4),
        vote_count=len(votes),
    )


def _majority(stances: list[str]) -> str:
    go = sum(1 for s in stances if s == "go")
    hold = len(stances) - go
    return "go" if go >= hold else "hold"
