import json
import unittest
from types import SimpleNamespace

from model_adapter import (
    HF_DEFAULT_BASE_URL,
    HuggingFaceChatClient,
    ModelConfigurationError,
    StructuredModelError,
    _service_message,
)
from models import MissionRequest
from planner import generate_structured_plan


class FakeCompletions:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeOpenAIClient:
    def __init__(self, content):
        self.chat = SimpleNamespace(completions=FakeCompletions(content))


def request():
    return MissionRequest(
        mission_id="sar-test",
        objective="Locate a missing hiker.",
        environment="Wilderness trail.",
        search_area="30-meter radius",
        available_resources=["1 drone", "1 ground team"],
        sensors=["RGB camera"],
        constraints=["Maintain visual line of sight"],
        approval_rules=["Coordinator approves search-area expansion"],
        success_criteria=["Complete one documented sweep"],
    )


def valid_plan_json():
    return json.dumps(
        {
            "mission_id": "sar-test",
            "summary": "Conduct a bounded search around the last known location.",
            "assumptions": [],
            "unresolved_questions": [],
            "milestones": ["Initial sweep complete"],
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "Confirm search area",
                    "description": "Coordinator confirms the bounded search area.",
                    "dependencies": [],
                    "assigned_resources": ["1 ground team"],
                    "risk_level": "low",
                    "human_approval_required": True,
                    "completion_criteria": ["Search area confirmed"],
                    "status": "planned",
                }
            ],
            "risks": [],
            "covered_constraints": ["Maintain visual line of sight"],
            "approval_gates": ["Coordinator approves search-area expansion"],
            "success_criteria": ["Complete one documented sweep"],
            "next_action": "Confirm the search area with the coordinator.",
            "plan_status": "DRAFT",
        }
    )


class ModelAdapterTests(unittest.TestCase):
    def test_from_env_requires_token(self):
        with self.assertRaises(ModelConfigurationError):
            HuggingFaceChatClient.from_env(
                env={"MODEL_ID": "Qwen/Qwen3.8-27B:ovhcloud"}
            )

    def test_from_env_requires_model_id(self):
        with self.assertRaises(ModelConfigurationError):
            HuggingFaceChatClient.from_env(env={"HF_TOKEN": "test-token"})

    def test_from_env_uses_router_default(self):
        client = HuggingFaceChatClient.from_env(
            env={
                "HF_TOKEN": "test-token",
                "MODEL_ID": "Qwen/Qwen3.8-27B:ovhcloud",
            }
        )
        self.assertEqual(client.base_url, HF_DEFAULT_BASE_URL)

    def test_rejects_non_https_base_url(self):
        with self.assertRaises(ModelConfigurationError):
            HuggingFaceChatClient.from_env(
                env={
                    "HF_TOKEN": "test-token",
                    "MODEL_ID": "model",
                    "HF_BASE_URL": "http://example.com/v1",
                }
            )

    def test_fake_client_returns_content(self):
        fake = FakeOpenAIClient('{"ok": true}')
        client = HuggingFaceChatClient(
            model_id="model",
            token="test-token",
            client=fake,
        )
        content = client.complete_json(system_prompt="system", user_prompt="user")
        self.assertEqual(content, '{"ok": true}')
        self.assertEqual(fake.chat.completions.calls[0]["model"], "model")

    def test_empty_response_fails_closed(self):
        client = HuggingFaceChatClient(
            model_id="model",
            token="test-token",
            client=FakeOpenAIClient("   "),
        )
        with self.assertRaises(StructuredModelError):
            client.complete_json(system_prompt="system", user_prompt="user")

    def test_service_messages_are_sanitized(self):
        self.assertIn("authentication failed", _service_message(401).lower())
        self.assertIn("credits or billing", _service_message(402).lower())
        self.assertIn("rate limit", _service_message(429).lower())
        self.assertNotIn("traceback", _service_message(500).lower())

    def test_planner_accepts_provider_neutral_client(self):
        fake_adapter = HuggingFaceChatClient(
            model_id="model",
            token="test-token",
            client=FakeOpenAIClient(valid_plan_json()),
        )
        plan = generate_structured_plan(
            mission_request=request(),
            hf_token="ignored-by-injected-client",
            model_client=fake_adapter,
        )
        self.assertEqual(plan.mission_id, "sar-test")
        self.assertEqual(plan.tasks[0].task_id, "T1")


if __name__ == "__main__":
    unittest.main()
