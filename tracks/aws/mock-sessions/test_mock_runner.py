from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from mock_runner import (
    SCORE_MAXIMA,
    QuestionResult,
    SessionValidationError,
    build_report,
    load_session,
    recommendation,
    validate_score,
)


VALID_SESSION = {
    "id": "test-session",
    "title": "Test Session",
    "description": "A valid session used by unit tests.",
    "rules": ["Tell the truth."],
    "questions": [
        {
            "id": "q1",
            "title": "Question One",
            "prompt": "Design a safe system.",
            "target_seconds": 90,
            "followups": ["What fails first?"],
            "must_cover": ["failure domains"],
            "unsafe_signals": ["unbounded retries"],
        }
    ],
}


class SessionLoadingTests(unittest.TestCase):
    def write_session(self, payload: dict) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "session.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_valid_session_loads(self) -> None:
        session = load_session(self.write_session(VALID_SESSION))
        self.assertEqual(session.session_id, "test-session")
        self.assertEqual(len(session.questions), 1)
        self.assertEqual(session.questions[0].target_seconds, 90)

    def test_duplicate_question_id_is_rejected(self) -> None:
        payload = dict(VALID_SESSION)
        payload["questions"] = [
            VALID_SESSION["questions"][0],
            dict(VALID_SESSION["questions"][0]),
        ]
        with self.assertRaises(SessionValidationError):
            load_session(self.write_session(payload))

    def test_empty_followups_are_rejected(self) -> None:
        payload = json.loads(json.dumps(VALID_SESSION))
        payload["questions"][0]["followups"] = []
        with self.assertRaises(SessionValidationError):
            load_session(self.write_session(payload))


class ScoreTests(unittest.TestCase):
    def test_score_validation(self) -> None:
        self.assertEqual(validate_score(0, 10), 0)
        self.assertEqual(validate_score(10, 10), 10)
        with self.assertRaises(ValueError):
            validate_score(11, 10)
        with self.assertRaises(ValueError):
            validate_score(-1, 10)

    def test_recommendation_thresholds(self) -> None:
        self.assertIn("Principal", recommendation(90))
        self.assertIn("Strong Staff", recommendation(82))
        self.assertIn("Staff hire", recommendation(74))
        self.assertIn("Senior hire", recommendation(65))
        self.assertIn("Mixed Senior", recommendation(50))
        self.assertIn("No hire", recommendation(49))


class ReportTests(unittest.TestCase):
    def test_report_contains_total_and_truth_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session_path = Path(directory) / "session.json"
            session_path.write_text(json.dumps(VALID_SESSION), encoding="utf-8")
            session = load_session(session_path)

            scores = {label: maximum for label, maximum in SCORE_MAXIMA.items()}
            report = build_report(
                session=session,
                results=[
                    QuestionResult(
                        question_id="q1",
                        title="Question One",
                        initial_seconds=87.2,
                        followup_seconds=(21.0,),
                        correction="State the invariant first.",
                    )
                ],
                scores=scores,
                notes={
                    "strongest_evidence": "Failure-domain reasoning",
                    "highest_risk_gap": "None observed",
                    "next_drill": "Repeat with interruption",
                    "truth_check": "No unsupported claims",
                },
                generated_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
            )

        self.assertIn("**100/100**", report)
        self.assertIn("No unsupported claims", report)
        self.assertIn("State the invariant first", report)


if __name__ == "__main__":
    unittest.main()
