import unittest

from models import AgentRequest, PolicyDecision, WorkflowStatus
from workflow import AgentControlPlane


class AgentControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.control_plane = AgentControlPlane()

    def request(self, actions: tuple[str, ...], risk: float = 0.2) -> AgentRequest:
        return AgentRequest("Complete a controlled business task", actions, risk)

    def test_low_risk_read_executes_automatically(self) -> None:
        result = self.control_plane.submit(self.request(("read_crm",)))
        self.assertEqual(result.status, WorkflowStatus.EXECUTED)
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_external_action_requires_approval(self) -> None:
        result = self.control_plane.submit(self.request(("send_email",)))
        self.assertEqual(result.status, WorkflowStatus.AWAITING_APPROVAL)

    def test_approved_workflow_executes(self) -> None:
        request = self.request(("update_crm",))
        self.control_plane.submit(request)
        result = self.control_plane.resolve_approval(request, approved=True)
        self.assertEqual(result.status, WorkflowStatus.EXECUTED)
        self.assertEqual(len(result.audit_events), 3)

    def test_denied_action_never_executes(self) -> None:
        result = self.control_plane.submit(self.request(("export_credentials",)))
        self.assertEqual(result.status, WorkflowStatus.BLOCKED)
        self.assertEqual(result.output, {})

    def test_idempotency_prevents_duplicate_execution(self) -> None:
        calls = []
        plane = AgentControlPlane(executor=lambda request: calls.append(request) or {"ok": True})
        request = self.request(("read_crm",))
        first = plane.submit(request)
        second = plane.submit(request)
        self.assertIs(first, second)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
