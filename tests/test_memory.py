from pathlib import Path

from keel.memory import (
    context_pack,
    encode_memory,
    export_events_jsonl,
    forget_memory,
    list_events,
    list_memories,
    recall,
    recall_plan,
    record_event,
    remember,
    remember_project_context,
    verify_memory,
)


def test_memory_records_and_exports_events(tmp_path: Path) -> None:
    record_event(tmp_path, "check", {"blocking_count": 0})

    events = list_events(tmp_path)
    out = export_events_jsonl(tmp_path)

    assert events[0]["type"] == "check"
    assert out.exists()
    assert '"blocking_count": 0' in out.read_text(encoding="utf-8")


def test_memory_remember_recall_and_forget(tmp_path: Path) -> None:
    first = remember(
        tmp_path,
        "Always update buildkeelupdates.md after changing Keel.",
        kind="preference",
        tags=["agent", "logs"],
    )
    second = remember(tmp_path, "Run tests with python -m pytest.", kind="project", tags=["tests"])

    matches = recall(tmp_path, "how do I update logs?", limit=5)

    assert matches[0]["id"] == first
    assert matches[0]["kind"] == "preference"
    assert "logs" in matches[0]["tags"]
    assert any(item["id"] == second for item in list_memories(tmp_path))

    assert forget_memory(tmp_path, first) is True
    assert not any(item["id"] == first for item in list_memories(tmp_path))


def test_memory_bootstrap_project_context(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nRun tests with pytest.", encoding="utf-8")
    (tmp_path / "ARCHITECTURE.md").write_text("# Architecture\n\nUI reaches SERVICE.", encoding="utf-8")
    (tmp_path / ".keel.yml").write_text("version: 1\nproject:\n  name: demo\n", encoding="utf-8")

    ids = remember_project_context(tmp_path)
    matches = recall(tmp_path, "architecture service", limit=3)

    assert len(ids) == 3
    assert matches[0]["kind"] == "architecture"


def test_memory_encoding_gate_plan_context_and_verify(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")

    rejected = remember(tmp_path, "ok", gate=True)
    stored = remember(
        tmp_path,
        "Decision: use README.md as a verified source for project summaries.",
        kind="decision",
        source="README.md",
        gate=True,
    )
    matches = recall(tmp_path, "why use readme source?", verify=True)
    pack = context_pack(tmp_path, "readme source")
    encoded = encode_memory("Always run pytest after code changes.")
    plan = recall_plan("can UI access database?")
    verification = verify_memory(tmp_path, matches[0])

    assert rejected == 0
    assert stored > 0
    assert matches[0]["id"] == stored
    assert "type" in matches[0]["channels"]
    assert "Keel Memory Context" in pack
    assert encoded["kind"] in {"preference", "test"}
    assert "architecture" in plan["target_kinds"]
    assert verification["status"] == "verified"


def test_context_pack_warns_when_memory_missing(tmp_path: Path) -> None:
    pack = context_pack(tmp_path, "unknown task")

    assert "Coverage: LOW" in pack
    assert "No verified memories matched" in pack
    assert "Inspect repo files directly" in pack
