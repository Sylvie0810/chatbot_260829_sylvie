import ast
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


SOURCE_PATH = Path(__file__).with_name("streamlit_app.py")
FUNCTIONS = {
    "build_download_filename",
    "calculate_progress",
    "conversation_markdown",
    "get_eligibility_status",
    "profile_to_text",
}


def load_functions():
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS
    ]
    found = {node.name for node in selected}
    missing = FUNCTIONS - found
    if missing:
        raise AssertionError(f"missing production functions: {sorted(missing)}")

    module = ast.Module(body=selected, type_ignores=[])
    namespace = {
        "datetime": datetime,
        "ZoneInfo": ZoneInfo,
        "SEOUL_TZ": ZoneInfo("Asia/Seoul"),
        "APP_NAME": "GrantMate",
        "APPLICATION_DEADLINE": "2026-08-31",
        "KNOWLEDGE_VERIFIED_AT": "2026-08-29",
        "MAX_PROFILE_VALUE_CHARS": 2000,
        "SOURCE_PUBLISHED_AT": "2026-08-11",
        "SOURCE_TITLE": "2026년 공공데이터 활용 지원 공식 모집공고",
    }
    exec(compile(module, str(SOURCE_PATH), "exec"), namespace)
    return namespace


class EligibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.functions = load_functions()

    def test_ready_requires_all_official_gate_evidence(self):
        profile = {
            "startup_eligible": "예",
            "portal_applied": "예",
            "request_date": "2026-08-20",
            "data_result": "제공 불가",
            "refusal_notice": "예",
            "legal_restriction": "아니오",
        }

        result = self.functions["get_eligibility_status"](profile)

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["icon"], "✅")
        self.assertEqual(result["issues"], [])

    def test_processing_request_is_blocked_from_submission_ready(self):
        profile = {
            "startup_eligible": "예",
            "portal_applied": "예",
            "request_date": "2026-08-20",
            "data_result": "처리 중",
            "refusal_notice": "아니오",
            "legal_restriction": "아니오",
        }

        result = self.functions["get_eligibility_status"](profile)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("제공 불가", " ".join(result["issues"]))

    def test_unknown_official_gate_is_not_treated_as_ready(self):
        result = self.functions["get_eligibility_status"]({})

        self.assertEqual(result["status"], "needs_confirmation")
        self.assertEqual(result["icon"], "⚠️")
        self.assertGreaterEqual(len(result["issues"]), 4)


class ProgressAndExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.functions = load_functions()

    def test_chat_does_not_make_application_progress_complete(self):
        profile = {
            "business_item": "서비스",
            "problem": "문제",
        }

        completed, total, ratio = self.functions["calculate_progress"](profile)

        self.assertEqual((completed, total), (1, 4))
        self.assertEqual(ratio, 0.25)

    def test_export_contains_profile_gate_and_source_authority(self):
        profile = {
            "business_item": "합성 데이터 기반 서비스",
            "problem": "데이터 부족",
        }
        eligibility = {
            "status": "needs_confirmation",
            "label": "확인 필요",
            "icon": "⚠️",
            "issues": ["제공 불가 결정 통지서를 확인해야 합니다."],
        }
        messages = [
            {"role": "user", "content": "검토해 주세요."},
            {"role": "assistant", "content": "[확인 질문] 통지서가 있나요?"},
        ]
        now = datetime(2026, 8, 29, 9, 30, tzinfo=ZoneInfo("Asia/Seoul"))

        markdown = self.functions["conversation_markdown"](
            profile,
            messages,
            "제출 전 점검",
            "전체",
            eligibility,
            now,
        )

        self.assertIn("합성 데이터 기반 서비스", markdown)
        self.assertIn("확인 필요", markdown)
        self.assertIn("공식 모집공고", markdown)
        self.assertIn("2026-08-29 09:30 KST", markdown)

    def test_export_filename_uses_workspace_naming_convention(self):
        now = datetime(2026, 8, 29, 9, 30, tzinfo=ZoneInfo("Asia/Seoul"))

        filename = self.functions["build_download_filename"](now)

        self.assertEqual(
            filename,
            "20260829_government-program_chat-record_grantmate.md",
        )

    def test_profile_context_caps_untrusted_values(self):
        text = self.functions["profile_to_text"](
            {"business_item": "가" * 5000},
            max_chars_per_value=120,
        )

        self.assertLess(len(text), 300)
        self.assertIn("참고용 데이터", text)


class StreamlitSmokeTests(unittest.TestCase):
    def test_app_renders_and_preserves_quick_question_without_api_key(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file("streamlit_app.py").run(timeout=30)
        self.assertEqual(len(app.exception), 0)

        quick_button = next(
            button
            for button in app.button
            if button.label == "🧩 데이터 필요성 점검"
        )
        quick_button.click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.session_state["pending_prompt"])
        self.assertTrue(
            any("질문을 보관했습니다" in warning.value for warning in app.warning)
        )


if __name__ == "__main__":
    unittest.main()
