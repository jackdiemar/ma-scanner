#!/usr/bin/env python3
"""Serve dashboard files with server-side auth and FMP proxy endpoints."""

from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import hmac
import json
import os
from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

from secure_config import get_env, require_env


REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT = REPO_ROOT / "dashboards"
SESSIONS = set()
PUBLIC_SUFFIXES = {".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp"}


def _load_users():
    raw = get_env("BSC_DASHBOARD_USERS")
    if not raw:
        return {}
    try:
        users = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("BSC_DASHBOARD_USERS must be a JSON object") from exc
    if not isinstance(users, dict):
        raise RuntimeError("BSC_DASHBOARD_USERS must map usernames to password hashes")
    return users


def _verify_password(username, password):
    stored = _load_users().get(username)
    if not stored:
        return False
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(digest, digest_hex)


def _has_session(headers):
    cookie = headers.get("Cookie", "")
    return any(part.strip().removeprefix("bsc_session=") in SESSIONS for part in cookie.split(";"))


class SecureDashboardHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        relative = urlparse(path).path.lstrip("/") or "dashboard_v12.html"
        return str((ROOT / relative).resolve())

    def do_HEAD(self):
        if not self._is_public_path():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        return super().do_HEAD()

    def do_POST(self):
        if urlparse(self.path).path != "/api/auth/login":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        username = str(payload.get("username", "")).lower().strip()
        password = str(payload.get("password", ""))

        if not _verify_password(username, password):
            self.send_error(HTTPStatus.UNAUTHORIZED)
            return

        session_id = token_urlsafe(32)
        SESSIONS.add(session_id)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie", f"bsc_session={session_id}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(json.dumps({"username": username, "role": "user"}).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/scan_latest.json":
            return self._send_json_file(REPO_ROOT / "data" / "scans" / "scan_latest.json")
        if parsed.path == "/watchlist_tracking.json":
            return self._send_json_file(REPO_ROOT / "data" / "tracking" / "watchlist_tracking.json")
        if parsed.path == "/api/quotes":
            return self._proxy_quotes(parsed)
        if parsed.path != "/api/charts/historical-price":
            if not self._is_public_path():
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            return super().do_GET()

        if not _has_session(self.headers):
            self.send_error(HTTPStatus.UNAUTHORIZED)
            return

        params = parse_qs(parsed.query)
        symbol = params.get("symbol", [""])[0].upper().strip()
        from_date = params.get("from", [""])[0]
        to_date = params.get("to", [""])[0]
        if not symbol or not from_date or not to_date:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return

        query = urlencode({
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
            "apikey": require_env("FMP_API_KEY"),
        })
        url = f"https://financialmodelingprep.com/stable/historical-price-eod/full?{query}"
        with urlopen(url, timeout=15) as response:
            data = response.read()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def _proxy_quotes(self, parsed):
        params = parse_qs(parsed.query)
        symbol = params.get("symbol", [""])[0].upper().strip()
        if not symbol:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        query = urlencode({"symbol": symbol, "apikey": require_env("FMP_API_KEY")})
        url = f"https://financialmodelingprep.com/stable/quote?{query}"
        with urlopen(url, timeout=15) as response:
            data = response.read()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def _send_json_file(self, path):
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def _is_public_path(self):
        parsed_path = urlparse(self.path).path
        target = Path(self.translate_path(parsed_path))
        try:
            target.relative_to(ROOT)
        except ValueError:
            return False
        return target.suffix.lower() in PUBLIC_SUFFIXES and not any(part.startswith(".") for part in target.parts)


def main():
    port = int(get_env("PORT", "8000"))
    os.chdir(ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", port), SecureDashboardHandler)
    print(f"Serving dashboard at http://127.0.0.1:{port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
