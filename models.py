from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any
from uuid import uuid4


class WorkflowStatus(str, Enum):
    RECEIVED = "received"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTED = "executed"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    REVIEW = "review"
    DENY = "deny"


@dataclass(frozen=True)
class AgentRequest:
    objective: str
    requested_actions: tuple[str, ...]
    risk_score: float
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    idempotency_key: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class AuditEvent:
    correlation_id: str
    event_type: str
    detail: dict[str, Any]
    timestamp: float = field(default_factory=time)


@dataclass
class WorkflowResult:
    correlation_id: str
    status: WorkflowStatus
    decision: PolicyDecision
    reason: str
    output: dict[str, Any] = field(default_factory=dict)
    audit_events: list[AuditEvent] = field(default_factory=list)
