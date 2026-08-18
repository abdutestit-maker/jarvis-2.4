"""Local Sprint 12 demo using production personality/relationship components."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.living.service import LivingIntelligence
from core.memory.relationship import PreferenceLearner, RelationshipMemoryStore
from core.personality import PersonalityEngine


def run_demo(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    relationship_dir = output_dir / "relationship"
    store = RelationshipMemoryStore(relationship_dir)
    learner = PreferenceLearner(store)
    personality = PersonalityEngine()
    living = LivingIntelligence(output_dir / "living", relationship_learner=learner)

    short_observations = []
    for request in (
        "Отвечай кратко.",
        "Пожалуйста, отвечай кратко, без длинных объяснений.",
        "Дальше тоже отвечай короче.",
    ):
        short_observations.append(learner.observe_user_message(request))
    short_profile = learner.profile()
    short_style = personality.style_for(
        task_type="conversation", user_preference=short_profile,
    )
    sample = "Проверил первый пункт. Второй тоже в порядке. Ошибок нет. Детали сохранены."
    short_response = personality.adapt_response(sample, short_style)

    acceptance_scores = [living.record_suggestion_feedback(
        "report_automation", outcome="accepted", useful=True,
        suggestion="Автоматизировать такой отчёт?",
    ) for _ in range(3)]

    changed = learner.observe_user_message("Теперь объясняй подробно и по шагам.")
    detailed_profile = learner.profile()
    detailed_style = personality.style_for(
        task_type="learning", user_preference=detailed_profile,
    )

    private_record = store.remember(
        "password=demo-secret", source="demo", confidence=1.0,
        importance=1.0, category="preference", key="credential",
    )
    reloaded = PreferenceLearner(RelationshipMemoryStore(relationship_dir))
    persisted_profile = reloaded.profile()

    checks = {
        "repeated_short_requests_learned": short_profile.communication_style == "short",
        "short_response_bounded": short_response.count(".") <= short_style.max_sentences,
        "accepted_help_confidence_increased": all(
            right > left for left, right in zip(acceptance_scores, acceptance_scores[1:])
        ),
        "sprint11_feedback_recorded": living.memory.affinity("report_automation") > 0,
        "changed_preference_applied": (
            changed.get("communication_style") == "detailed"
            and detailed_style.verbosity == "detailed"
        ),
        "changed_preference_persisted": persisted_profile.communication_style == "detailed",
        "secret_not_stored": private_record is None,
    }
    report = {
        "sprint": 12,
        "mode": "local_production_components",
        "inputs": {
            "short_requests": 3,
            "accepted_help_events": 3,
            "preference_change": "detailed",
        },
        "observed": {
            "short_style": short_style.__dict__,
            "short_response": short_response,
            "acceptance_confidence": acceptance_scores,
            "changed_style": detailed_style.__dict__,
            "persisted_communication_style": persisted_profile.communication_style,
            "relationship_records": len(store.all_memories()),
        },
        "checks": checks,
        "verified": all(checks.values()),
    }
    report_path = output_dir / "live_demo_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_demo(args.output_dir.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

