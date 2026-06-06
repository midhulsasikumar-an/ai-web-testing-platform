from __future__ import annotations

import re
from typing import Any, Dict, List

_KEY_ALIASES = {
    "email": "email",
    "e-mail": "email",
    "mail": "email",
    "username": "username",
    "user name": "username",
    "user": "username",
    "login": "username",
    "signin": "username",
    "sign in": "username",
    "password": "password",
    "pass": "password",
    "pwd": "password",
}

_ALL_CREDENTIAL_ALIASES = sorted(_KEY_ALIASES.keys(), key=len, reverse=True)

_HEADER_RE = re.compile(r"^(?P<header>credentials?|auth(?:entication)?|login|signin|sign in)\s*[:=-]?\s*$", re.IGNORECASE)
_KEY_VALUE_RE = re.compile(r"^(?P<key>[A-Za-z][\w\s\-]{0,32})\s*[:=]\s*(?P<value>.+?)\s*$")


def _credential_pattern(key_aliases: list[str]) -> re.Pattern[str]:
    joined = "|".join(re.escape(alias) for alias in sorted(key_aliases, key=len, reverse=True))
    stop_joined = "|".join(re.escape(alias) for alias in _ALL_CREDENTIAL_ALIASES)
    return re.compile(
        rf"(?P<key>{joined})\s*[:=]\s*(?P<value>.+?)(?=(?:\s+(?:and|or|with|then|also)\s+(?:{stop_joined})\s*[:=])|[,;|.]|$)",
        re.IGNORECASE,
    )


_INLINE_PATTERNS = {
    "email": _credential_pattern(["email", "e-mail", "mail"]),
    "username": _credential_pattern(["username", "user name", "user", "login", "signin", "sign in"]),
    "password": _credential_pattern(["password", "pass", "pwd"]),
}

_VALUE_BOUNDARY_RE = re.compile(r"\s+(?:then|also|next|after|before|please|and then|and also|for|to)\b", re.IGNORECASE)


def _normalize_key(key: str) -> str:
    normalized = " ".join(str(key or "").strip().lower().replace("_", " ").split())
    return _KEY_ALIASES.get(normalized, normalized)


def _looks_like_credential_value(key: str, value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if key == "email":
        return bool(re.search(r"@[^\s]+\.[^\s]+", text)) or len(text) <= 128
    if key == "password":
        return len(text) <= 128
    if key == "username":
        lowered = text.lower()
        return len(text) <= 128 and not any(marker in lowered for marker in ["test the", "verify", "validate", "focus", "cover"])
    return len(text) <= 128


def _merge_credentials(target: Dict[str, str], source: Dict[str, Any] | None) -> None:
    if not isinstance(source, dict):
        return
    for key, value in source.items():
        normalized_key = _normalize_key(key)
        if normalized_key in {"email", "username", "password"} and value is not None:
            text = str(value).strip()
            if text:
                target[normalized_key] = text


def _extract_inline_credentials(line: str, in_credential_block: bool) -> tuple[Dict[str, str], str, List[str]]:
    extracted: Dict[str, str] = {}
    sources: List[str] = []
    remaining = line

    for canonical_key, pattern in _INLINE_PATTERNS.items():
        while True:
            match = pattern.search(remaining)
            if not match:
                break
            value = match.group("value").strip().strip('"\'`')
            boundary_match = _VALUE_BOUNDARY_RE.search(value)
            if boundary_match:
                value = value[: boundary_match.start()].strip().strip('"\'`')
            if _looks_like_credential_value(canonical_key, value):
                extracted[canonical_key] = value
                sources.append(f"line:{canonical_key}")
                remaining = (remaining[: match.start()] + " " + remaining[match.end():]).strip()
            else:
                break

    if in_credential_block:
        for canonical_key, pattern in _INLINE_PATTERNS.items():
            if canonical_key in extracted:
                continue
            match = pattern.search(line)
            if match:
                value = match.group("value").strip().strip('"\'`')
                if value:
                    extracted[canonical_key] = value
                    sources.append(f"block:{canonical_key}")

    return extracted, remaining, sources


def parse_instruction_context(instruction: str, explicit_credentials: Dict[str, Any] | None = None) -> Dict[str, Any]:
    raw_lines = str(instruction or "").splitlines()
    sanitized_lines: List[str] = []
    credentials: Dict[str, str] = {}
    credential_sources: List[str] = []
    in_credential_block = False

    _merge_credentials(credentials, explicit_credentials)

    for raw_line in raw_lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            sanitized_lines.append(line)
            in_credential_block = False
            continue

        header_match = _HEADER_RE.match(stripped)
        if header_match:
            in_credential_block = True
            credential_sources.append(f"header:{header_match.group('header').lower()}")
            continue

        inline_credentials, remaining_line, inline_sources = _extract_inline_credentials(line, in_credential_block)
        if inline_credentials:
            credentials.update(inline_credentials)
            credential_sources.extend(inline_sources)
            if remaining_line.strip():
                sanitized_lines.append(remaining_line)
            continue

        key_value_match = _KEY_VALUE_RE.match(stripped)
        if key_value_match:
            normalized_key = _normalize_key(key_value_match.group("key"))
            value = key_value_match.group("value").strip().strip('"\'`')
            if normalized_key in {"email", "username", "password"} and _looks_like_credential_value(normalized_key, value):
                credentials[normalized_key] = value
                credential_sources.append(f"line:{normalized_key}")
                continue
            if in_credential_block and normalized_key in {"email", "username", "password"}:
                credentials[normalized_key] = value
                credential_sources.append(f"block:{normalized_key}")
                continue

        if in_credential_block and stripped:
            maybe_match = _KEY_VALUE_RE.match(stripped)
            if maybe_match:
                normalized_key = _normalize_key(maybe_match.group("key"))
                value = maybe_match.group("value").strip().strip('"\'`')
                if normalized_key in {"email", "username", "password"}:
                    credentials[normalized_key] = value
                    credential_sources.append(f"block:{normalized_key}")
                    continue

        sanitized_lines.append(line)

    sanitized_instruction = "\n".join(sanitized_lines).strip()
    if not sanitized_instruction:
        sanitized_instruction = str(instruction or "").strip()

    lowered_instruction = sanitized_instruction.lower()
    return {
        "instruction": str(instruction or "").strip(),
        "sanitized_instruction": sanitized_instruction,
        "credentials": credentials,
        "credential_sources": credential_sources,
        "has_credentials": bool(credentials),
        "has_login_intent": any(token in lowered_instruction for token in ["login", "log in", "sign in", "signin", "authentication"]),
        "has_signup_intent": any(token in lowered_instruction for token in ["sign up", "signup", "register", "create account"]),
    }