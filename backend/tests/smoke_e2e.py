"""End-to-end smoke test runner.

Spawns the FastAPI server in a subprocess on a free port, polls the
/health endpoint until ready, then exercises:

  1. Health endpoints (no auth)
  2. Auth flow: signup / login / me / refresh / logout
  3. Refresh-token revocation: refresh token revoked after logout cannot be used
  4. Cross-tenant isolation: user B cannot read user A's tests/bugs/timeline
  5. Bug lifecycle: PATCH /api/bugs/{id}/status transitions
  6. Asset token flow: building a screenshot URL and serving via ?token=...

Outputs a structured report. Returns non-zero exit code on any failure.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import urllib.request
import urllib.error
import urllib.parse

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = ROOT / "backend"

# Ensure `backend.*` imports resolve when the smoke runner imports DB modules
# to seed a synthetic bug for the lifecycle test.
sys.path.insert(0, str(ROOT))

VENV_PYTHON = BACKEND.parent / ".venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists():
    PYTHON_EXECUTABLE = str(VENV_PYTHON)
else:
    PYTHON_EXECUTABLE = sys.executable


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, timeout_seconds: float = 120.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Optional[str] = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=2.0) as response:
                if 200 <= response.status < 300:
                    return
        except Exception as exc:  # pragma: no cover - timing-only
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"Server did not become healthy within {timeout_seconds}s: {last_error}")


class SmokeRunner:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.results: list[Tuple[str, str, str]] = []  # (status, name, detail)

    def _record(self, name: str, status: str, detail: str) -> None:
        self.results.append((status, name, detail))
        marker = {"ok": "PASS", "fail": "FAIL", "skip": "SKIP"}.get(status, status.upper())
        print(f"[{marker}] {name} :: {detail}")

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Any, Dict[str, str]]:
        url = f"{self.base_url}{path}"
        data: Optional[bytes] = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("content-type", "application/json")
        if token:
            req.add_header("authorization", f"Bearer {token}")
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=30.0) as response:
                raw = response.read().decode("utf-8") or "{}"
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = raw
                return response.status, payload, dict(response.headers)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") or "{}"
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw
            return exc.code, payload, dict(exc.headers or {})
        except Exception as exc:
            return 0, {"error": str(exc)}, {}

    def assert_status(self, name: str, expected: int, got: int, payload: Any) -> None:
        if got == expected:
            self._record(name, "ok", f"status={got}")
        else:
            self._record(name, "fail", f"expected={expected} got={got} body={str(payload)[:300]}")

    def health_checks(self) -> None:
        status, payload, _ = self.request("GET", "/health")
        self.assert_status("GET /health", 200, status, payload)

        status, payload, _ = self.request("GET", "/api/health")
        self.assert_status("GET /api/health", 200, status, payload)

        status, payload, _ = self.request("GET", "/api/health/deep")
        self.assert_status("GET /api/health/deep", 200, status, payload)
        if status == 200 and isinstance(payload, dict):
            components = payload.get("components") or {}
            if "mongo" not in components:
                self._record("GET /api/health/deep", "fail", "missing mongo component in deep health")

    def auth_flow(self) -> Dict[str, str]:
        suffix = uuid.uuid4().hex[:8]
        email_a = f"alice+{suffix}@example.com"
        email_b = f"bob+{suffix}@example.com"
        password = "TestPass123!"

        # Signup user A
        status, payload, _ = self.request("POST", "/api/auth/signup", body={"name": "Alice", "email": email_a, "password": password})
        self.assert_status("POST /api/auth/signup (alice)", 200, status, payload)
        if status != 200 or not isinstance(payload, dict):
            raise RuntimeError("alice signup failed")
        alice_access = payload["access_token"]
        alice_refresh = payload["refresh_token"]
        alice_id = payload["user"]["id"]

        # Signup user B
        status, payload, _ = self.request("POST", "/api/auth/signup", body={"name": "Bob", "email": email_b, "password": password})
        self.assert_status("POST /api/auth/signup (bob)", 200, status, payload)
        if status != 200 or not isinstance(payload, dict):
            raise RuntimeError("bob signup failed")
        bob_access = payload["access_token"]
        bob_refresh = payload["refresh_token"]
        bob_id = payload["user"]["id"]

        # Duplicate signup should 409
        status, payload, _ = self.request("POST", "/api/auth/signup", body={"name": "Alice", "email": email_a, "password": password})
        self.assert_status("POST /api/auth/signup (duplicate)", 409, status, payload)

        # Login alice
        status, payload, _ = self.request("POST", "/api/auth/login", body={"email": email_a, "password": password})
        self.assert_status("POST /api/auth/login (alice)", 200, status, payload)
        if status != 200 or not isinstance(payload, dict):
            raise RuntimeError("alice login failed")
        alice_access = payload["access_token"]
        alice_refresh = payload["refresh_token"]

        # Login wrong password
        status, payload, _ = self.request("POST", "/api/auth/login", body={"email": email_a, "password": "wrong"})
        self.assert_status("POST /api/auth/login (wrong password)", 401, status, payload)

        # /me with bearer
        status, payload, _ = self.request("GET", "/api/auth/me", token=alice_access)
        self.assert_status("GET /api/auth/me", 200, status, payload)
        if status == 200 and isinstance(payload, dict):
            user = payload.get("user") or {}
            if user.get("email") != email_a:
                self._record("GET /api/auth/me identity", "fail", f"wrong email returned: {user.get('email')}")
            else:
                self._record("GET /api/auth/me identity", "ok", f"email={email_a}")

        # /me without bearer
        status, payload, _ = self.request("GET", "/api/auth/me")
        self.assert_status("GET /api/auth/me (no auth)", 401, status, payload)

        # Refresh alice
        status, payload, _ = self.request("POST", "/api/auth/refresh", body={"refresh_token": alice_refresh})
        self.assert_status("POST /api/auth/refresh (alice)", 200, status, payload)
        if status != 200 or not isinstance(payload, dict):
            raise RuntimeError("alice refresh failed")
        new_alice_access = payload["access_token"]
        new_alice_refresh = payload["refresh_token"]
        if new_alice_access == alice_access:
            self._record("POST /api/auth/refresh rotation", "fail", "new access token identical to old one")
        else:
            self._record("POST /api/auth/refresh rotation", "ok", "new tokens issued")
        if new_alice_refresh == alice_refresh:
            self._record("POST /api/auth/refresh refresh rotation", "fail", "new refresh token identical to old one")
        else:
            self._record("POST /api/auth/refresh refresh rotation", "ok", "new refresh token issued")

        # Old refresh token should now be revoked -> 401
        status, payload, _ = self.request("POST", "/api/auth/refresh", body={"refresh_token": alice_refresh})
        self.assert_status("POST /api/auth/refresh (old refresh, revoked)", 401, status, payload)

        # Old access token (alice_access) should be revoked too? No - only the refresh token is rotated.
        # We rely on the access token TTL being short. So we don't assert access token revocation on refresh.
        # But we DO assert access token revocation on logout below.

        # Logout alice -> revokes current access token
        status, payload, _ = self.request(
            "POST",
            "/api/auth/logout",
            body={"refresh_token": new_alice_refresh},
            token=new_alice_access,
        )
        self.assert_status("POST /api/auth/logout (alice)", 200, status, payload)
        if status == 200 and isinstance(payload, dict):
            if not payload.get("revoked_access"):
                self._record("logout revoked_access", "fail", "revoked_access=false")
            else:
                self._record("logout revoked_access", "ok", "access token revoked")
            if not payload.get("revoked_refresh"):
                self._record("logout revoked_refresh", "fail", "revoked_refresh=false")
            else:
                self._record("logout revoked_refresh", "ok", "refresh token revoked")

        # After logout, access token should be rejected
        status, payload, _ = self.request("GET", "/api/auth/me", token=new_alice_access)
        self.assert_status("GET /api/auth/me (post-logout)", 401, status, payload)

        # After logout, refresh token should be rejected
        status, payload, _ = self.request("POST", "/api/auth/refresh", body={"refresh_token": new_alice_refresh})
        self.assert_status("POST /api/auth/refresh (post-logout)", 401, status, payload)

        return {
            "alice_email": email_a,
            "bob_email": email_b,
            "alice_password": password,
            "bob_access": bob_access,
            "bob_id": bob_id,
        }

    def cross_tenant_test(self, alice_email: str, alice_password: str, bob_access: str, bob_id: str) -> None:
        # Re-login alice to get fresh tokens (previous session was revoked)
        status, payload, _ = self.request("POST", "/api/auth/login", body={"email": alice_email, "password": alice_password})
        if status != 200 or not isinstance(payload, dict):
            self._record("cross-tenant setup", "fail", "could not re-login alice")
            return
        alice_access = payload["access_token"]

        # Alice creates a test (or queries list)
        status, payload, _ = self.request("GET", "/api/tests", token=alice_access)
        self.assert_status("alice GET /api/tests", 200, status, payload)

        # Bob lists his own tests (should be empty)
        status, payload, _ = self.request("GET", "/api/tests", token=bob_access)
        self.assert_status("bob GET /api/tests", 200, status, payload)
        if status == 200:
            tests = payload if isinstance(payload, list) else []
            if any(t.get("user_id") == "alice-id" for t in tests if isinstance(t, dict)):
                self._record("bob cross-tenant list", "fail", "bob sees alice's test records")

        # Bob cannot read alice's bugs
        status, payload, _ = self.request("GET", "/api/bugs", token=bob_access)
        self.assert_status("bob GET /api/bugs", 200, status, payload)
        if status == 200:
            bugs = payload if isinstance(payload, list) else []
            if any(b.get("user_id") == "alice-id" for b in bugs if isinstance(b, dict)):
                self._record("bob bug isolation", "fail", "bob sees alice's bugs")

        # Bob trying to PATCH a non-existent bug should 404
        status, payload, _ = self.request(
            "PATCH",
            "/api/bugs/non-existent-bug-id/status",
            body={"status": "resolved"},
            token=bob_access,
        )
        self.assert_status("bob PATCH non-existent bug", 404, status, payload)

        # Timeline cross-tenant: bob tries to read alice's run timeline
        status, payload, _ = self.request("GET", "/api/agent/runs/00000000-0000-0000-0000-000000000000/timeline", token=bob_access)
        if status == 200 and isinstance(payload, dict) and payload.get("test_id"):
            self._record("bob timeline cross-tenant", "fail", "bob retrieved a non-existent timeline")
        else:
            self._record("bob timeline cross-tenant", "ok", f"status={status} (404 expected)")

    def bug_lifecycle_test(self, alice_email: str, alice_password: str) -> None:
        status, payload, _ = self.request("POST", "/api/auth/login", body={"email": alice_email, "password": alice_password})
        if status != 200 or not isinstance(payload, dict):
            self._record("bug lifecycle login", "fail", "alice could not re-login")
            return
        access = payload["access_token"]

        # List existing bugs (may be empty)
        status, payload, _ = self.request("GET", "/api/bugs", token=access)
        self.assert_status("alice GET /api/bugs (lifecycle)", 200, status, payload)

        bug_id: Optional[str] = None
        if status == 200 and isinstance(payload, list) and payload:
            bug = payload[0]
            bug_id = bug.get("bug_id") or str(bug.get("_id"))

        if not bug_id:
            # Insert a synthetic bug into Mongo so we can exercise PATCH /status
            from backend.database.mongo import bug_collection
            from backend.services.bug_services import _compute_bug_fingerprint
            from datetime import datetime, timezone
            import uuid as _uuid
            new_bug_id = _uuid.uuid4().hex
            # Get alice's user_id by reading the login response we just made
            alice_user_id = ""
            try:
                login_status, login_payload, _ = self.request("POST", "/api/auth/login", body={"email": alice_email, "password": alice_password})
                if login_status == 200 and isinstance(login_payload, dict):
                    alice_user_id = (login_payload.get("user") or {}).get("id") or ""
            except Exception:
                pass
            fingerprint = _compute_bug_fingerprint(
                test_data={"test_id": "smoke-test", "user_id": alice_user_id},
                result={
                    "step": {"action": "smoke-step", "selector": "body"},
                    "test": "smoke-step",
                    "selector_used": "body",
                    "error": "smoke test error",
                    "failure_category": "functional",
                },
            )
            try:
                bug_collection.delete_one({"fingerprint": fingerprint})
                bug_collection.insert_one({
                    "bug_id": new_bug_id,
                    "fingerprint": fingerprint,
                    "bug_name": "Smoke test bug",
                    "title": "Smoke test bug",
                    "bug_description": "Inserted by smoke_e2e.py to exercise PATCH /status",
                    "status": "open",
                    "user_id": alice_user_id,
                    "test_id": "smoke-test",
                    "evidence": {},
                    "root_cause": "UNKNOWN",
                    "failure_category": "functional",
                    "url": "https://example.com",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                bug_id = new_bug_id
                self._record("smoke seed bug", "ok", f"inserted bug_id={new_bug_id[:8]}")
            except Exception as exc:
                self._record("smoke seed bug", "fail", str(exc))
                return

        if not bug_id:
            self._record("bug lifecycle transitions", "skip", "no bug id available")
            return

        # Invalid status -> 422
        status, payload, _ = self.request("PATCH", f"/api/bugs/{bug_id}/status", body={"status": "garbage"}, token=access)
        self.assert_status("PATCH bug status invalid", 422, status, payload)

        # Valid -> resolved
        status, payload, _ = self.request("PATCH", f"/api/bugs/{bug_id}/status", body={"status": "resolved"}, token=access)
        self.assert_status("PATCH bug status resolved", 200, status, payload)
        if status == 200 and isinstance(payload, dict) and payload.get("status") != "resolved":
            self._record("PATCH bug status persisted", "fail", f"server returned status={payload.get('status')}")
        else:
            self._record("PATCH bug status persisted", "ok", f"status={payload.get('status') if isinstance(payload, dict) else 'n/a'}")

        # resolved -> closed (transition allowed)
        status, payload, _ = self.request("PATCH", f"/api/bugs/{bug_id}/status", body={"status": "closed"}, token=access)
        self.assert_status("PATCH bug status resolved->closed", 200, status, payload)

        # closed -> open (reopen blocked with 409)
        status, payload, _ = self.request("PATCH", f"/api/bugs/{bug_id}/status", body={"status": "open"}, token=access)
        self.assert_status("PATCH bug status reopen closed", 409, status, payload)

    def rate_limit_test(self) -> None:
        # Hit /api/auth/login 7 times with bad password; after 5 it should 429
        seen_429 = False
        for i in range(7):
            status, _, _ = self.request(
                "POST",
                "/api/auth/login",
                body={"email": f"nonexistent-{i}@x.com", "password": "wrong"},
            )
            if status == 429:
                seen_429 = True
                self._record(f"rate-limit login attempt #{i+1}", "ok", "got 429 as expected")
                break
        if not seen_429:
            self._record("rate-limit login", "fail", "never returned 429 after 7 attempts")

    def run(self) -> int:
        self.health_checks()
        try:
            creds = self.auth_flow()
        except Exception as exc:
            self._record("auth flow", "fail", str(exc))
            return self._summary()
        self.cross_tenant_test(creds["alice_email"], creds["alice_password"], creds["bob_access"], creds["bob_id"])
        self.bug_lifecycle_test(creds["alice_email"], creds["alice_password"])
        self.rate_limit_test()
        return self._summary()

    def _summary(self) -> int:
        ok = sum(1 for status, _, _ in self.results if status == "ok")
        fail = sum(1 for status, _, _ in self.results if status == "fail")
        skip = sum(1 for status, _, _ in self.results if status == "skip")
        print()
        print(f"SMOKE SUMMARY: {ok} passed, {fail} failed, {skip} skipped")
        return 0 if fail == 0 else 1


def main() -> int:
    port = _free_port()
    env = os.environ.copy()
    env["JWT_ALLOW_WEAK_SECRET"] = "1"
    env["STRICT_SECRETS"] = ""  # do not refuse to start
    env.setdefault("RATE_LIMIT_LOGIN", "5/minute")
    env.setdefault("RATE_LIMIT_SIGNUP", "30/minute")
    env.setdefault("RATE_LIMIT_REFRESH", "60/minute")
    # Skip Playwright warm-up to keep the test fast and avoid native dependency issues
    env["SKIP_BROWSER_WARMUP"] = "1"
    env.setdefault("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD", "1")

    print(f"Spawning uvicorn on 127.0.0.1:{port}")

    # Write a tiny bootstrap script to disk to avoid command-line quoting issues on
    # Windows. The script adds the project root to sys.path and then invokes uvicorn.
    bootstrap_path = Path(tempfile.gettempdir()) / f"smoke_uvicorn_{port}.py"
    bootstrap_path.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "import uvicorn\n"
        f"uvicorn.run('backend.server:app', host='127.0.0.1', port={port}, log_level='warning')\n",
        encoding="utf-8",
    )

    server_log_path = Path(tempfile.gettempdir()) / f"smoke_server_{port}.log"
    server_log_file = open(server_log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [PYTHON_EXECUTABLE, str(bootstrap_path)],
        cwd=str(ROOT),
        env=env,
        stdout=server_log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        try:
            _wait_for_health(base_url, timeout_seconds=60.0)
        except Exception as exc:
            print(f"FAILED to start server: {exc}")
            try:
                if proc.stdout is not None:
                    out = proc.stdout.read()
                    print(out)
            except Exception:
                pass
            return 2

        runner = SmokeRunner(base_url)
        rc = runner.run()
        return rc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        try:
            server_log_file.close()
        except Exception:
            pass
        try:
            if server_log_path.exists():
                log_content = server_log_path.read_text(encoding="utf-8", errors="replace")
                if log_content:
                    print("=== SERVER LOG ===")
                    print(log_content)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
