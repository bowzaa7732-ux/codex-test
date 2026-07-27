import json
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class PlannerError(RuntimeError):
    """A planner failure safe to display to the user."""


class MissingAPIKeyError(PlannerError):
    pass


class PlannerAPIError(PlannerError):
    pass


class PlannerTimeoutError(PlannerError):
    pass


class InvalidPlannerResponseError(PlannerError):
    pass


class ProposedOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["write"]
    path: str = Field(min_length=1)
    content: str

    @field_validator("path")
    @classmethod
    def path_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Operation path cannot be blank")
        return value


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    proposed_file_operations: list[ProposedOperation]

    @property
    def operations(self) -> list[ProposedOperation]:
        """Compatibility name used by the unchanged approval workflow."""
        return self.proposed_file_operations


class Planner(Protocol):
    def create_plan(self, instruction: str) -> ExecutionPlan: ...


class MockPlanner:
    """Safe deterministic fallback planner that requires no network access."""

    def create_plan(self, instruction: str) -> ExecutionPlan:
        cleaned = instruction.strip()
        if not cleaned:
            raise ValueError("Instruction cannot be blank")
        operation = ProposedOperation(
            operation="write",
            path="AI_PLAN.md",
            content=f"# AI Cloud OS Plan\n\nUser instruction:\n\n{cleaned}\n",
        )
        return ExecutionPlan(
            title="AI Cloud OS Plan",
            summary="Record the requested work in the project workspace.",
            steps=["Validate the requested path", "Write AI_PLAN.md after explicit approval"],
            proposed_file_operations=[operation],
        )


class OpenAIPlanner:
    """Requests plans only; it has no access to the filesystem or approval executor."""

    def __init__(
        self,
        api_key: str | None,
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
        client=None,
    ):
        if not api_key or not api_key.strip():
            raise MissingAPIKeyError("OPENAI_API_KEY is not configured")
        self.model = model
        self.client = client or httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def create_plan(self, instruction: str) -> ExecutionPlan:
        cleaned = instruction.strip()
        if not cleaned:
            raise ValueError("Instruction cannot be blank")
        try:
            response = self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a planning service. Return only the requested JSON plan. "
                                "You may propose write operations, but you cannot execute them. "
                                "All paths must be relative to the project workspace."
                            ),
                        },
                        {"role": "user", "content": cleaned},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "execution_plan",
                            "strict": True,
                            "schema": ExecutionPlan.model_json_schema(),
                        },
                    },
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except httpx.TimeoutException as exc:
            raise PlannerTimeoutError("OpenAI planning request timed out") from exc
        except httpx.HTTPError as exc:
            raise PlannerAPIError("OpenAI planning request failed") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise InvalidPlannerResponseError("OpenAI returned an empty response") from exc

        try:
            return ExecutionPlan.model_validate(json.loads(content or ""))
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise InvalidPlannerResponseError("OpenAI returned invalid plan JSON") from exc


def get_planner(api_key: str | None, model: str = "gpt-4o-mini", timeout: float = 30.0) -> Planner:
    """Select OpenAI when configured, otherwise retain the mock fallback."""
    if api_key and api_key.strip():
        return OpenAIPlanner(api_key=api_key, model=model, timeout=timeout)
    return MockPlanner()
