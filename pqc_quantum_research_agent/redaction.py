from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REDACTED = "[REDACTED]"
SENSITIVE_PARAMETER_NAMES = {
    "api_key",
    "apikey",
    "access_token",
    "token",
    "signature",
    "x-api-key",
}

_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)(?P<prefix>\b(?:api[_-]?key|apikey|access[_-]?token|token|signature|x-api-key)\s*(?:=|:)\s*)"
    r"(?P<value>\[REDACTED\]|[^&\s)\]}>,'\"]+)"
)
_BEARER_RE = re.compile(r"(?i)(?P<prefix>authorization\s*:\s*bearer\s+)(?P<value>\S+)")
_SAM_KEY_RE = re.compile(r"\bSAM-[A-Za-z0-9-]{16,}\b")


def redact_text(value: object) -> str:
    """Remove credentials from URLs, exception strings, logs, and persisted reports."""
    text = "" if value is None else str(value)
    text = _SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group('prefix')}{REDACTED}", text
    )
    text = _BEARER_RE.sub(
        lambda match: f"{match.group('prefix')}{REDACTED}", text
    )
    return _SAM_KEY_RE.sub(REDACTED, text)


def redact_url(value: object) -> str:
    """Redact sensitive query values while preserving a usable URL."""
    text = "" if value is None else str(value)
    try:
        parsed = urlsplit(text)
    except ValueError:
        return redact_text(text)
    if not parsed.scheme or not parsed.netloc:
        return redact_text(text)
    query = urlencode(
        [
            (name, REDACTED if name.casefold() in SENSITIVE_PARAMETER_NAMES else item)
            for name, item in parse_qsl(parsed.query, keep_blank_values=True)
        ],
        doseq=True,
    )
    return redact_text(
        urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))
    )
