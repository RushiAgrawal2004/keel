import sys
from pathlib import Path

from keel.record import blackbox_report, get_session, list_sessions, log_action, record_note, run_command, start_session
from keel.serve import blackbox_note, blackbox_report_text, blackbox_run, blackbox_sessions, blackbox_start, graph_state


def test_record_replay_orders_events(tmp_path: Path) -> None:
    session_id = start_session(tmp_path)
    log_action(tmp_path, session_id, "start", {"ok": True})
    log_action(tmp_path, session_id, "finish", {"ok": True})

    events = get_session(tmp_path, session_id)

    assert [event["kind"] for event in events] == ["start", "finish"]


def test_blackbox_records_command_output_and_snapshot(tmp_path: Path) -> None:
    command = f'"{sys.executable}" -c "print(123)"'
    session_id = start_session(tmp_path, label="test")

    result = run_command(tmp_path, command, session_id=session_id)
    record_note(tmp_path, "Use the blackbox as evidence.", session_id=session_id, kind="decision")
    sessions = list_sessions(tmp_path)
    report = blackbox_report(tmp_path, session_id)

    assert result["ok"] is True
    assert result["returncode"] == 0
    assert "123" in result["stdout_tail"]
    assert result["graph"]["exists"] is False
    assert sessions[0]["label"] == "test"
    assert "Use the blackbox as evidence." in report
    assert "command" in report


def test_serve_graph_status_helper(tmp_path: Path) -> None:
    status = graph_state(tmp_path)

    assert status["exists"] is False
    assert status["nodes"] == 0


def test_serve_blackbox_helpers(tmp_path: Path) -> None:
    session = blackbox_start(label="mcp", repo_path=tmp_path)
    command = f'"{sys.executable}" -c "print(789)"'

    run = blackbox_run(command, session_id=session["session_id"], repo_path=tmp_path)
    note = blackbox_note("MCP decision", session_id=session["session_id"], kind="decision", repo_path=tmp_path)
    sessions = blackbox_sessions(repo_path=tmp_path)
    report = blackbox_report_text(session["session_id"], repo_path=tmp_path)

    assert run["ok"] is True
    assert "789" in run["stdout_tail"]
    assert note["ok"] is True
    assert sessions[0]["label"] == "mcp"
    assert "MCP decision" in report
