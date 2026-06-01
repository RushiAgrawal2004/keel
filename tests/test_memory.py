from pathlib import Path

from keel.memory import export_events_jsonl, list_events, record_event


def test_memory_records_and_exports_events(tmp_path: Path) -> None:
    record_event(tmp_path, "check", {"blocking_count": 0})

    events = list_events(tmp_path)
    out = export_events_jsonl(tmp_path)

    assert events[0]["type"] == "check"
    assert out.exists()
    assert '"blocking_count": 0' in out.read_text(encoding="utf-8")

