from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from models import AgentRequest
from workflow import AgentControlPlane

app = FastAPI(title="Agentic AI Control Plane", version="1.0.0")
control_plane = AgentControlPlane()
requests: dict[str, AgentRequest] = {}


class SubmitPayload(BaseModel):
    objective: str = Field(min_length=3, max_length=500)
    requested_actions: list[str] = Field(min_length=1)
    risk_score: float = Field(ge=0, le=1)
    idempotency_key: str | None = None


class ApprovalPayload(BaseModel):
    approved: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/workflows")
def submit(payload: SubmitPayload) -> dict:
    values = payload.model_dump(exclude_none=True)
    values["requested_actions"] = tuple(values["requested_actions"])
    request = AgentRequest(**values)
    result = control_plane.submit(request)
    requests[result.correlation_id] = request
    return asdict(result)


@app.post("/workflows/{correlation_id}/approval")
def resolve(correlation_id: str, payload: ApprovalPayload) -> dict:
    request = requests.get(correlation_id)
    if request is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    try:
        return asdict(control_plane.resolve_approval(request, payload.approved))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
