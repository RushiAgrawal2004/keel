from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

from keel.memory import record_event
from keel.webhook import send_governance_webhook


def test_webhook_posts_recent_events(tmp_path: Path) -> None:
    received: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            received["body"] = self.rfile.read(length).decode("utf-8")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    record_event(tmp_path, "check", {"blocking_count": 0})

    try:
        response = send_governance_webhook(tmp_path, f"http://127.0.0.1:{server.server_port}/hook")
    finally:
        server.shutdown()

    assert response["status"] == 200
    assert '"type": "keel.export"' in received["body"]
    assert '"blocking_count": 0' in received["body"]

