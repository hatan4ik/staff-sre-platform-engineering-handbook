#!/usr/bin/env python3
"""Run a structured AWS Staff/Principal mock interview from a JSON session.

The runner uses only Python's standard library. It does not record audio or video;
use a phone, meeting client, or screen recorder separately when desired.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCORE_MAXIMA: dict[str, int] = {
    "Requirement clarification": 10,
    "Architecture and service semantics": 15,
    "Distributed-systems reasoning": 15,
    "Reliability and failure containment": 15,
    "Security and trust boundaries": 10,
    "Operability and observability": 10,
    "Incident response": 10,
    "Communication and leadership": 10,
    "Validation and evidence": 5,
}


@dataclass(frozen=True, slots=True)
class Question:
    question_id: str
    title: str
    prompt: str
    target_seconds: int
    followups: tuple[str, ...]
    must_cover: tuple[str, ...]
    unsafe_signals: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Session:
    session_id: str
    title: str
    description: str
    rules: tuple[str, ...]
    questions: tuple[Question, ...]


@dataclass(frozen=True, slots=True)
class QuestionResult:
    question_id: str
    title: str
    initial_seconds: float
    followup_seconds: tuple[float, ...]
    correction: str


class SessionValidationError(ValueError):
    """Raised when a session JSON file is incomplete or unsafe to run."""


def _require_string(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SessionValidationError(f"{key!r} must be a non-empty string")
    return value.strip()


def _require_string_list(mapping: dict[str, Any], key: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value:
        raise SessionValidationError(f"{key!r} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise SessionValidationError(f"every entry in {key!r} must be a string")
    return tuple(item.strip() for item in value)


def load_session(path: Path) -> Session:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SessionValidationError(f"session file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SessionValidationError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise SessionValidationError("session root must be a JSON object")

    raw_questions = raw.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise SessionValidationError("questions must be a non-empty list")

    questions: list[Question] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_questions, start=1):
        if not isinstance(item, dict):
            raise SessionValidationError(f"question {index} must be an object")
        question_id = _require_string(item, "id")
        if question_id in seen_ids:
            raise SessionValidationError(f"duplicate question id: {question_id}")
        seen_ids.add(question_id)

        target_seconds = item.get("target_seconds")
        if not isinstance(target_seconds, int) or target_seconds <= 0:
            raise SessionValidationError(
                f"question {question_id}: target_seconds must be a positive integer"
            )

        questions.append(
            Question(
                question_id=question_id,
                title=_require_string(item, "title"),
                prompt=_require_string(item, "prompt"),
                target_seconds=target_seconds,
                followups=_require_string_list(item, "followups"),
                must_cover=_require_string_list(item, "must_cover"),
                unsafe_signals=_require_string_list(item, "unsafe_signals"),
            )
        )

    return Session(
        session_id=_require_string(raw, "id"),
        title=_require_string(raw, "title"),
        description=_require_string(raw, "description"),
        rules=_require_string_list(raw, "rules"),
        questions=tuple(questions),
    )


def validate_score(value: int, maximum: int) -> int:
    if not 0 <= value <= maximum:
        raise ValueError(f"score must be between 0 and {maximum}")
    return value


def recommendation(total: int) -> str:
    if total >= 90:
        return "Strong Principal / exceptional Staff"
    if total >= 82:
        return "Strong Staff hire; Principal possible with leadership evidence"
    if total >= 74:
        return "Staff hire or strong Senior depending on consistency"
    if total >= 65:
        return "Senior hire; Staff gaps"
    if total >= 50:
        return "Mixed Senior signal; significant production gaps"
    return "No hire for a senior infrastructure role"


def _read_score(label: str, maximum: int) -> int:
    while True:
        raw = input(f"{label} / {maximum}: ").strip()
        try:
            return validate_score(int(raw), maximum)
        except (ValueError, TypeError):
            print(f"Enter an integer from 0 through {maximum}.")


def _timed_response(label: str) -> float:
    input(f"\n{label}\nPress Enter when ready to begin. ")
    started = time.monotonic()
    input("Answer now. Press Enter only when the response is complete. ")
    return time.monotonic() - started


def _print_guidance(question: Question) -> None:
    print("\nExpected Staff-level coverage:")
    for item in question.must_cover:
        print(f"  + {item}")
    print("Unsafe or down-level signals:")
    for item in question.unsafe_signals:
        print(f"  - {item}")


def run_interactive(session: Session, practice_mode: bool) -> tuple[list[QuestionResult], dict[str, int], dict[str, str]]:
    print(f"\n{session.title}\n{'=' * len(session.title)}")
    print(session.description)
    print("\nRules:")
    for rule in session.rules:
        print(f"  - {rule}")

    input("\nStart an external recording now. Press Enter to begin the session. ")

    results: list[QuestionResult] = []
    for position, question in enumerate(session.questions, start=1):
        print(f"\n\nQuestion {position}/{len(session.questions)} — {question.title}")
        print("-" * 78)
        print(question.prompt)
        print(f"Initial-answer target: {question.target_seconds} seconds")

        initial_seconds = _timed_response("Initial response")
        followup_seconds: list[float] = []
        for followup_index, followup in enumerate(question.followups, start=1):
            print(f"\nFollow-up {followup_index}: {followup}")
            followup_seconds.append(_timed_response("Follow-up response"))

        if practice_mode:
            _print_guidance(question)

        correction = input(
            "\nWrite one correction for your next attempt (do not defend the answer): "
        ).strip()
        results.append(
            QuestionResult(
                question_id=question.question_id,
                title=question.title,
                initial_seconds=initial_seconds,
                followup_seconds=tuple(followup_seconds),
                correction=correction,
            )
        )

    if not practice_mode:
        print("\n\nModel coverage review")
        print("=" * 78)
        for question in session.questions:
            print(f"\n{question.title}")
            _print_guidance(question)

    print("\n\nScore the complete session using the repository's 100-point rubric.")
    scores = {
        label: _read_score(label, maximum)
        for label, maximum in SCORE_MAXIMA.items()
    }

    notes = {
        "strongest_evidence": input("\nStrongest evidence demonstrated: ").strip(),
        "highest_risk_gap": input("Highest-risk gap: ").strip(),
        "next_drill": input("Single next drill: ").strip(),
        "truth_check": input(
            "Any unsupported claim, guessed metric, or lab presented as production? "
        ).strip(),
    }
    return results, scores, notes


def build_report(
    session: Session,
    results: list[QuestionResult],
    scores: dict[str, int],
    notes: dict[str, str],
    generated_at: datetime,
) -> str:
    total = sum(scores.values())
    lines = [
        f"# {session.title} — Result",
        "",
        f"- Session ID: `{session.session_id}`",
        f"- Completed UTC: `{generated_at.isoformat()}`",
        f"- Total score: **{total}/100**",
        f"- Calibration: **{recommendation(total)}**",
        "",
        "## Timing and immediate corrections",
        "",
        "| Question | Initial answer | Follow-ups total | Correction |",
        "|---|---:|---:|---|",
    ]

    for result in results:
        followup_total = sum(result.followup_seconds)
        correction = result.correction.replace("|", "\\|") or "Not recorded"
        lines.append(
            f"| {result.title} | {result.initial_seconds:.1f}s | "
            f"{followup_total:.1f}s | {correction} |"
        )

    lines.extend(["", "## Score", "", "| Dimension | Score |", "|---|---:|"])
    for label, maximum in SCORE_MAXIMA.items():
        lines.append(f"| {label} | {scores[label]}/{maximum} |")
    lines.extend(
        [
            f"| **Total** | **{total}/100** |",
            "",
            "## Review",
            "",
            f"- Strongest evidence: {notes.get('strongest_evidence') or 'Not recorded'}",
            f"- Highest-risk gap: {notes.get('highest_risk_gap') or 'Not recorded'}",
            f"- Single next drill: {notes.get('next_drill') or 'Not recorded'}",
            f"- Truth check: {notes.get('truth_check') or 'Not recorded'}",
            "",
            "## Readiness decision",
            "",
        ]
    )

    if total >= 82:
        lines.append(
            "This run meets the numerical Staff target. Repeat with different prompts before "
            "declaring readiness, and confirm that no unsafe state, security, or incident behavior occurred."
        )
    else:
        lines.append(
            "This run does not yet meet the repeated 82/100 Staff target. Correct the single "
            "highest-risk behavior, then rerun the weakest two questions rather than rereading everything."
        )

    lines.extend(
        [
            "",
            "## Evidence integrity",
            "",
            "- Production facts, assignments/labs, and hypothetical designs remained separate.",
            "- Current AWS quotas were verified or explicitly left as verification work.",
            "- No unsupported availability, cost, traffic, or incident metric was added.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--session",
        type=Path,
        default=script_dir / "session-01-baseline.json",
        help="Path to the JSON session definition.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Markdown result path. Defaults to reports/<UTC timestamp>-<session id>.md.",
    )
    parser.add_argument(
        "--practice",
        action="store_true",
        help="Reveal expected coverage after each question instead of after the full session.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the session JSON and exit without running the interview.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        session = load_session(args.session)
    except SessionValidationError as exc:
        print(f"Session validation failed: {exc}", file=sys.stderr)
        return 2

    if args.validate_only:
        print(
            f"Validated {session.session_id}: {len(session.questions)} questions, "
            f"{sum(len(question.followups) for question in session.questions)} follow-ups."
        )
        return 0

    try:
        results, scores, notes = run_interactive(session, args.practice)
    except (EOFError, KeyboardInterrupt):
        print("\nSession interrupted; no report was written.", file=sys.stderr)
        return 130

    now = datetime.now(timezone.utc)
    output = args.output
    if output is None:
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        output = Path(__file__).resolve().parent / "reports" / f"{stamp}-{session.session_id}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        build_report(session, results, scores, notes, now),
        encoding="utf-8",
    )
    print(f"\nReport written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
