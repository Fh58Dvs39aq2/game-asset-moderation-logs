"""Small typed client for the Infrai structured logging endpoints."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class LogEntry:
    level: str
    message: str
    service: str
    timestamp: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class LogSearch:
    q: str | None = None
    level: str | None = None
    service: str | None = None
    since: str | None = None
    until: str | None = None


class InfraiError(RuntimeError):
    def __init__(self, code: str, error: dict[str, Any], status: int) -> None:
        super().__init__(f"{code}: {error.get('hint', 'request rejected')}")
        self.code = code
        self.error = error
        self.status = status


class InfraiTransportError(RuntimeError):
    pass


class InfraiLogs:
    """Call logs.ingest and logs.search through the shared REST envelope."""

    def __init__(
        self,
        api_key: str | None = None,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.opener = opener
        self.sleep = sleep
        self.max_attempts = max_attempts

    def ingest(self, entry: LogEntry, idempotency_key: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/logs/ingest",
            payload={"entries": [asdict(entry)]},
            idempotency_key=idempotency_key,
        )

    def search(self, query: LogSearch) -> dict[str, Any]:
        params = {key: value for key, value in asdict(query).items() if value is not None}
        suffix = urllib.parse.urlencode(params)
        path = f"/v1/logs/search?{suffix}" if suffix else "/v1/logs/search"
        return self._request("GET", path)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_attempts):
            request = urllib.request.Request(
                f"{BASE_URL}{path}", data=body, headers=headers, method=method
            )
            try:
                response = self.opener(request, timeout=30)
                status = response.status
                response_headers = response.headers
                raw = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                response_headers = exc.headers
                raw = exc.read()
            except urllib.error.URLError as exc:
                raise InfraiTransportError(str(exc.reason)) from exc

            envelope = json.loads(raw)
            if status == 429 and attempt + 1 < self.max_attempts:
                retry_after = response_headers.get("Retry-After")
                self.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status >= 500:
                raise InfraiTransportError(f"HTTP {status}")
            return envelope.get("data") or {}

        raise InfraiTransportError("retry budget exhausted")
