from __future__ import annotations

from collections.abc import Callable
from typing import Any

from models import AgentRequest, AuditEvent, PolicyDecision, WorkflowResult, WorkflowStatus
from policy import PolicyConfig, evaluate_policy

ToolExecutor = Callable[[AgentRequest], dict[str, Any]]


def default_executor(request: AgentRequest) -> dict[str, Any]:
    """Deterministic stand-in for a real tool gateway."""
    return {
        "objective": request.objective,
        "actions_completed": list(request.requested_actions),
        "message": "Reference execution completed",
    }


class AgentControlPlane:
    def __init__(
        self,
        executor: ToolExecutor = default_executor,
        policy: PolicyConfig | None = None,
    ) -> None:
        self.executor = executor
        self.policy = policy or PolicyConfig()
        self._completed: dict[str, WorkflowResult] = {}

    def submit(self, request: AgentRequest) -> WorkflowResult:
        if request.idempotency_key in self._completed:
            return self._completed[request.idempotency_key]

        decision, reason = evaluate_policy(request, self.policy)
        audit = [
            AuditEvent(
                request.correlation_id,
                "policy_evaluated",
                {"decision": decision.value, "reason": reason},
            )
        ]

        if decision is PolicyDecision.DENY:
            result = WorkflowResult(
                request.correlation_id,
                WorkflowStatus.BLOCKED,
                decision,
                reason,
                audit_events=audit,
            )
        elif decision is PolicyDecision.REVIEW:
            result = WorkflowResult(
                request.correlation_id,
                WorkflowStatus.AWAITING_APPROVAL,
                decision,
                reason,
                audit_events=audit,
            )
        else:
            result = self._execute(request, decision, reason, audit)

        self._completed[request.idempotency_key] = result
        return result

    def resolve_approval(self, request: AgentRequest, approved: bool) -> WorkflowResult:
        current = self._completed.get(request.idempotency_key)
        if current is None or current.status is not WorkflowStatus.AWAITING_APPROVAL:
            raise ValueError("workflow is not awaiting approval")

        current.audit_events.append(
            AuditEvent(
                request.correlation_id,
                "approval_resolved",
                {"approved": approved},
            )
        )
        if not approved:
            current.status = WorkflowStatus.REJECTED
            current.reason = "request rejected by human reviewer"
            return current

        result = self._execute(
            request,
            PolicyDecision.REVIEW,
            "approved by human reviewer",
            current.audit_events,
        )
        self._completed[request.idempotency_key] = result
        return result

    def _execute(
        self,
        request: AgentRequest,
        decision: PolicyDecision,
        reason: str,
        audit: list[AuditEvent],
    ) -> WorkflowResult:
        output = self.executor(request)
        audit.append(
            AuditEvent(
                request.correlation_id,
                "tools_executed",
                {"actions": list(request.requested_actions)},
            )
        )
        return WorkflowResult(
            request.correlation_id,
            WorkflowStatus.EXECUTED,
            decision,
            reason,
            output,
            audit,
        )
