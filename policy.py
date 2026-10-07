from dataclasses import dataclass, field

from models import AgentRequest, PolicyDecision


@dataclass(frozen=True)
class PolicyConfig:
    review_threshold: float = 0.60
    deny_threshold: float = 0.90
    review_actions: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"send_email", "update_crm", "create_invoice", "deploy_release"}
        )
    )
    denied_actions: frozenset[str] = field(
        default_factory=lambda: frozenset({"export_credentials", "disable_audit"})
    )


def evaluate_policy(
    request: AgentRequest, config: PolicyConfig | None = None
) -> tuple[PolicyDecision, str]:
    config = config or PolicyConfig()

    if not 0 <= request.risk_score <= 1:
        return PolicyDecision.DENY, "risk_score must be between 0 and 1"

    actions = set(request.requested_actions)
    denied = actions & config.denied_actions
    if denied:
        return PolicyDecision.DENY, f"blocked action: {sorted(denied)[0]}"

    if request.risk_score >= config.deny_threshold:
        return PolicyDecision.DENY, "risk score exceeds deny threshold"

    review_actions = actions & config.review_actions
    if request.risk_score >= config.review_threshold or review_actions:
        reason = "human approval required"
        if review_actions:
            reason += f" for {', '.join(sorted(review_actions))}"
        return PolicyDecision.REVIEW, reason

    return PolicyDecision.ALLOW, "request satisfies automatic-execution policy"
