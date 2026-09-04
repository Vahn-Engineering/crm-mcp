"""A stand-in for vahn-crm-service, driven by a per-test route table.

Tests override `Stub.routes[path] = (status, body)` to shape a scenario, so a
guardrail test can say "this endpoint 503s" without mocking httpx internals.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Default happy-path bodies. Mirrors the shapes in crm-service/docs/read-api.md.
DEFAULTS: dict[str, dict] = {
    "/api/read/opportunities-by-stage": {
        "total": 100,
        "stages": [
            {"stage": "New Lead", "opportunities": 60, "stageRank": 1, "isLost": False},
            {"stage": "Qualified", "opportunities": 25, "stageRank": 3, "isLost": False},
            {"stage": "Paying Customer – Full Fleet", "opportunities": 10,
             "stageRank": 7, "isLost": False},
            {"stage": "Closed - Lost", "opportunities": 5, "stageRank": None,
             "isLost": True},
        ],
    },
    "/api/read/opportunities-by-status": {
        "total": 100, "byStatus": {"Open": 85, "Won": 10, "Lost": 5},
    },
    "/api/read/users": {"users": [
        {"userId": "u1", "name": "Mazhar Ali Khan", "email": "mazhar@vahn.in"},
        {"userId": "u2", "firstName": "Ravi", "lastName": "Sharma"},
    ]},
    "/api/read/team-summary": {"totalReps": 1, "reps": [
        {"name": "Mazhar Ali Khan", "tasksCreated": 4, "tasksCompleted": 2,
         "currentlyOverdue": 1, "activitiesLogged": 0},
    ]},
    "/api/read/activity-types": {"total": 2, "source": "leadsquared", "activityTypes": [
        {"activityEvent": 164, "eventName": "Customer Connect",
         "eventTypeLabel": "custom", "description": "Rep logged contact"},
        {"activityEvent": 210, "eventName": "AI Bot Call", "eventTypeLabel": "custom",
         "writtenByVahn": True, "writtenBy": "ElevenLabsWebhookService"},
    ]},
}


def envelope(content, *, page=0, size=50, total=None, sort="createdAt,DESC"):
    total = len(content) if total is None else total
    pages = max(1, -(-total // max(size, 1)))
    return {"content": content, "page": page, "size": size, "totalElements": total,
            "totalPages": pages, "hasNext": page + 1 < pages,
            "hasPrevious": page > 0, "sort": sort}


class Stub:
    """Route table shared with the running handler. Reset between tests."""

    routes: dict[str, tuple[int, object]] = {}
    calls: list[str] = []

    @classmethod
    def reset(cls):
        cls.routes = {}
        cls.calls = []

    @classmethod
    def set(cls, path: str, body, status: int = 200):
        cls.routes[path] = (status, body)

    @classmethod
    def resolve(cls, path: str):
        if path in cls.routes:
            return cls.routes[path]
        if path in DEFAULTS:
            return 200, DEFAULTS[path]
        return 404, {"error": "not found"}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _respond(self, status, body):
        raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(status)
        ctype = "text/plain" if isinstance(body, str) else "application/json"
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        Stub.calls.append(self.path)
        self._respond(*Stub.resolve(path))

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        Stub.calls.append(self.path)
        self._respond(*Stub.resolve(path))


def start() -> tuple[str, HTTPServer]:
    """Start the stub on an ephemeral port. Returns (base_url, server)."""
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    return f"http://{host}:{port}", server
