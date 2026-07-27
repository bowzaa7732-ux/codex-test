from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProposedOperation:
    operation: str
    path: str
    content: str


@dataclass(frozen=True)
class ExecutionPlan:
    summary: str
    steps: list[str]
    operations: list[ProposedOperation]


class Planner(Protocol):
    def create_plan(self, instruction: str) -> ExecutionPlan: ...


class MockPlanner:
    """Safe deterministic planner; replace through dependency injection later."""

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
            summary="Record the requested work in the project workspace.",
            steps=["Validate the requested path", "Write AI_PLAN.md after explicit approval"],
            operations=[operation],
        )

