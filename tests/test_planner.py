from types import SimpleNamespace

import pytest

from app.services.planner import (
    InvalidPlannerResponseError,
    MockPlanner,
    OpenAIPlanner,
    get_planner,
)


class FakeResponse:
    def __init__(self, content: str):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


def fake_client(content: str):
    return SimpleNamespace(post=lambda *args, **kwargs: FakeResponse(content))


def test_mock_planner_selected_without_api_key():
    planner = get_planner(None)
    assert isinstance(planner, MockPlanner)
    assert planner.create_plan("Document this").proposed_file_operations[0].path == "AI_PLAN.md"


def test_openai_planner_selected_with_api_key():
    assert isinstance(get_planner("test-key"), OpenAIPlanner)


def test_openai_response_is_validated():
    planner = OpenAIPlanner(
        "test-key",
        client=fake_client(
            '{"title":"Plan","summary":"Summary","steps":["One"],'
            '"proposed_file_operations":[{"operation":"write","path":"notes.md","content":"ok"}]}'
        ),
    )
    plan = planner.create_plan("Make notes")
    assert plan.title == "Plan"
    assert plan.operations[0].path == "notes.md"


def test_openai_invalid_json_has_clear_error():
    planner = OpenAIPlanner("test-key", client=fake_client("not json"))
    with pytest.raises(InvalidPlannerResponseError, match="invalid plan JSON"):
        planner.create_plan("Make notes")
