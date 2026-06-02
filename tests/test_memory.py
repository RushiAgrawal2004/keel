from pathlib import Path

from keel.memory import (
    export_events_jsonl,
    forget_memory,
    list_events,
    list_memories,
    recall,
    record_event,
    remember,
    remember_project_context,
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
