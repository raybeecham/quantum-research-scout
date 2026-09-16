"""Private loopback-only research desk with a bounded AI endpoint. Not a public server."""

import argparse
import json
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pqc_quantum_research_agent.paper_search import PaperSearch
from pqc_quantum_research_agent.question_ai import clean_input, generate
from pqc_quantum_research_agent.reading_ai import assist_reading, clean_reading

ROOT = Path(__file__).resolve().parents[1]


def load_key(variable="GEMINI_API_KEY"):
    # Explicit providers only: never fall back to the previous OpenAI key.
    if variable not in {"GEMINI_API_KEY", "GROQ_API_KEY"}:
        raise ValueError("Unsupported key variable")
    for line in (ROOT / ".env.local").read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() == variable:
            key = value.strip().strip("\"'")
            if len(key) >= 20 and not any(c.isspace() for c in key):
                return key
    raise ValueError(
        f"Add {variable} to the gitignored .env.local file, then restart the private server."
    )


class Budget:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.last = 0.0

    def reserve(self, calls=1):
        with self.lock:
            today = datetime.now(timezone.utc).date().isoformat()
            state = json.loads(self.path.read_text()) if self.path.exists() else {}
            count = state.get("attempts", 0) if state.get("date") == today else 0
            if not isinstance(calls, int) or calls < 1 or calls > 20:
                raise ValueError("Invalid call reservation")
            if not isinstance(count, int) or count < 0 or count + calls > 20:
                raise ValueError("Daily pilot limit reached (20 attempts, resets at midnight UTC).")
            if time.monotonic() - self.last < 10:
                raise ValueError("Please wait ten seconds between requests.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps({"date": today, "attempts": count + calls}))
            temp.replace(self.path)
            self.last = time.monotonic()


def handler(site, key, port, budget, backup_key=""):
    token = secrets.token_urlsafe(32)
    origin = f"http://127.0.0.1:{port}"
    busy = threading.Lock()
    papers = PaperSearch()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site), **kwargs)

        def log_message(self, *_args):
            pass  # Do not log user topics, paths or API error payloads.

        def allowed(self):
            return self.headers.get("Host") == f"127.0.0.1:{port}"

        def reply(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self.allowed():
                return self.reply(403, {"error": "Local host only"})
            if self.path == "/api/lab/config":
                return self.reply(200, {"token": token, "daily_limit": 20})
            path = (site / unquote(urlsplit(self.path).path).lstrip("/")).resolve()
            if not path.is_relative_to(site) or any(
                p.startswith(".") for p in path.relative_to(site).parts
            ):
                return self.reply(404, {"error": "Not found"})
            if path.is_dir() and not (path / "index.html").is_file():
                return self.reply(404, {"error": "Not found"})
            super().do_GET()

        def do_HEAD(self):
            self.reply(405, {"error": "Method not supported"})

        def do_POST(self):
            if (
                not self.allowed()
                or self.path not in {"/api/lab/generate", "/api/lab/papers", "/api/lab/read"}
                or self.headers.get("Origin") != origin
                or not secrets.compare_digest(self.headers.get("X-Scout-Token", ""), token)
                or self.headers.get("Content-Type") != "application/json"
            ):
                return self.reply(403, {"error": "Local same-origin requests only"})
            if not busy.acquire(blocking=False):
                return self.reply(429, {"error": "A lab request is already running. Please wait."})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size < 1 or size > 24000:
                    return self.reply(400, {"error": "Input exceeds the pilot size limit"})
                self.connection.settimeout(180)
                raw = json.loads(self.rfile.read(size))
                if self.path == "/api/lab/papers":
                    if not isinstance(raw, dict):
                        raise ValueError("Invalid search request")
                    return self.reply(200, papers.search(raw.get("query")))
                reading = self.path == "/api/lab/read"
                data = clean_reading(raw) if reading else clean_input(raw)
                provider = raw.get("provider", "gemini")
                if provider not in {"gemini", "groq"}:
                    raise ValueError("Unsupported AI provider")
                if provider == "groq" and raw.get("backup_consent") is not True:
                    raise ValueError("Explicit consent is required to send this request to Groq")
                selected_key = key if provider == "gemini" else backup_key
                if not selected_key:
                    return self.reply(
                        503,
                        {
                            "error": f"{provider.title()} is not configured. Add {'GEMINI_API_KEY' if provider == 'gemini' else 'GROQ_API_KEY'} to .env.local and restart the private server. Never paste the key into chat."
                        },
                    )
                budget.reserve(
                    1 if reading else 2
                )  # Reserve draft + critique before either call; no refunds/retries.
                result = (
                    assist_reading(data, selected_key, provider)
                    if reading
                    else (
                        generate(data, selected_key)
                        if provider == "gemini"
                        else generate(data, selected_key, provider="groq")
                    )
                )
                self.reply(200, result)
            except ValueError as exc:
                self.reply(
                    400,
                    {
                        "error": str(exc)
                        if not isinstance(exc, json.JSONDecodeError)
                        else "Invalid JSON"
                    },
                )
            except RuntimeError as exc:
                self.reply(502, {"error": str(exc)})
            except Exception:
                self.reply(503, {"error": "Lab service unavailable. No automatic retry was made."})
            finally:
                busy.release()

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        key = load_key()
    except (OSError, ValueError):
        key = ""
        print(
            "Gemini key not configured; generation disabled until GEMINI_API_KEY is added to .env.local.",
            flush=True,
        )
    site = (ROOT / "site").resolve()
    try:
        backup_key = load_key("GROQ_API_KEY")
    except (OSError, ValueError):
        backup_key = ""
    budget = Budget(ROOT / ".local-intelligence" / "question-ai-usage.json")
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), handler(site, key, args.port, budget, backup_key)
    )
    print(f"Private AI lab: http://127.0.0.1:{args.port}/#questions (20 attempts/day)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
