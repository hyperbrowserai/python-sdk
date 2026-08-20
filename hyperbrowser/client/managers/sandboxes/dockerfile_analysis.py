"""Conservative Dockerfile analysis for remote build context selection.

This module intentionally does not try to execute or fully reproduce the
BuildKit Dockerfile frontend. It recognizes the context-consuming syntax the
SDK can analyze safely and requests a full context for anything ambiguous.
That keeps sparse uploads an optimization rather than a correctness
requirement.
"""

import json
import re
import shlex
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit


_KNOWN_INSTRUCTIONS = frozenset(
    {
        "ADD",
        "ARG",
        "CMD",
        "COPY",
        "ENTRYPOINT",
        "ENV",
        "EXPOSE",
        "FROM",
        "HEALTHCHECK",
        "LABEL",
        "MAINTAINER",
        "ONBUILD",
        "RUN",
        "SHELL",
        "STOPSIGNAL",
        "USER",
        "VOLUME",
        "WORKDIR",
    }
)
_KNOWN_RUN_FLAGS = frozenset({"device", "mount", "network", "security"})
_INSTRUCTION_PATTERN = re.compile(r"^([A-Za-z]+)(?:[ \t]+(.*))?$")
_DIRECTIVE_PATTERN = re.compile(
    r"(?im)^\s*#\s*(?P<name>escape|syntax)\s*=\s*(?P<value>\S+)"
)
_FLAG_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
_SCP_GIT_SOURCE_PATTERN = re.compile(r"^git@[^:/\s]+:.+")


class _AnalysisFallback(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class _DockerfileSourceAnalyzer:
    def __init__(self, data: bytes):
        self._data = data

    def analyze(self) -> Tuple[List[List[str]], str]:
        try:
            text = self._data.decode("utf-8")
        except UnicodeDecodeError:
            return [], "dockerfile_parse_failed"

        try:
            self._validate_parser_directives(text)
            # Heredocs are valid BuildKit syntax, but treating the entire
            # Dockerfile as full context is safer than partially parsing them.
            if "<<" in text:
                raise _AnalysisFallback("dockerfile_instruction_parse_failed")
            logical_lines = self._logical_lines(text)
            return self._analyze_lines(logical_lines), ""
        except _AnalysisFallback as exc:
            return [], exc.reason

    @staticmethod
    def _validate_parser_directives(text: str) -> None:
        for match in _DIRECTIVE_PATTERN.finditer(text):
            name = match.group("name").lower()
            value = match.group("value")
            if name == "escape" and value != "\\":
                raise _AnalysisFallback("dockerfile_parse_failed")
            if name == "syntax" and not _is_official_dockerfile_frontend(value):
                raise _AnalysisFallback("custom_dockerfile_frontend")

    @staticmethod
    def _logical_lines(text: str) -> List[str]:
        logical_lines = []
        parts: List[str] = []
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not parts and (not stripped or stripped.startswith("#")):
                continue
            if parts and (not stripped or stripped.startswith("#")):
                # BuildKit has nuanced rules for comments and empty lines in a
                # continuation. Full context is the safe answer here.
                raise _AnalysisFallback("dockerfile_parse_failed")
            if stripped.endswith("\\"):
                parts.append(stripped[:-1].rstrip())
                continue
            parts.append(stripped)
            logical_lines.append(" ".join(parts))
            parts = []
        if parts:
            raise _AnalysisFallback("dockerfile_parse_failed")
        return logical_lines

    def _analyze_lines(self, logical_lines: List[str]) -> List[List[str]]:
        groups = []
        for line in logical_lines:
            instruction, body = _parse_instruction(line)
            if instruction not in _KNOWN_INSTRUCTIONS:
                raise _AnalysisFallback("dockerfile_instruction_parse_failed")
            if instruction in ("COPY", "ADD"):
                group = self._analyze_copy_or_add(instruction, body)
                if group:
                    groups.append(group)
            elif instruction == "RUN":
                groups.extend(self._analyze_run(body))
        return groups

    @staticmethod
    def _analyze_copy_or_add(instruction: str, body: str) -> List[str]:
        try:
            flags, values = _parse_copy_add_values(body)
        except (ValueError, json.JSONDecodeError):
            raise _AnalysisFallback("dockerfile_instruction_parse_failed")

        if instruction == "COPY" and "from" in flags:
            return []

        local_sources = []
        for source in values[:-1]:
            if "$" in source or "\x00" in source:
                reason = (
                    "copy_source_requires_expansion"
                    if instruction == "COPY"
                    else "add_source_requires_expansion"
                )
                raise _AnalysisFallback(reason)
            if "\\" in source:
                # A backslash is a path character on Unix but a separator on
                # Windows. Full context keeps selection platform-independent.
                raise _AnalysisFallback("dockerfile_source_path")
            if instruction == "ADD" and _is_remote_add_source(source):
                continue
            if _source_has_pattern(source):
                # Python glob semantics differ from Go filepath.Match for
                # dotfiles, character classes, and recursive patterns.
                raise _AnalysisFallback("dockerfile_source_pattern")
            local_sources.append(source)
        return local_sources

    @staticmethod
    def _analyze_run(body: str) -> List[List[str]]:
        try:
            flags, _ = _split_leading_flags(body)
        except ValueError:
            raise _AnalysisFallback("run_mount_parse_failed")

        groups = []
        for name, value in flags:
            if name not in _KNOWN_RUN_FLAGS:
                raise _AnalysisFallback("dockerfile_instruction_parse_failed")
            if name != "mount":
                continue
            if not value or any(character in value for character in ('"', "'")):
                raise _AnalysisFallback("run_mount_parse_failed")
            options = _parse_mount_options(value)
            if options.get("type", "bind") != "bind" or options.get("from"):
                continue
            source = options.get("source") or options.get("src") or "."
            if "$" in source or "\x00" in source:
                raise _AnalysisFallback("run_bind_source_requires_expansion")
            groups.append([source])
        return groups


def analyze_dockerfile_sources(data: bytes) -> Tuple[List[List[str]], str]:
    """Return local source groups or a reason to upload the full context."""

    return _DockerfileSourceAnalyzer(data).analyze()


def _parse_instruction(line: str) -> Tuple[str, str]:
    match = _INSTRUCTION_PATTERN.fullmatch(line)
    if match is None:
        raise _AnalysisFallback("dockerfile_parse_failed")
    return match.group(1).upper(), match.group(2) or ""


def _parse_copy_add_values(body: str) -> Tuple[Dict[str, str], List[str]]:
    parsed_flags, remaining = _split_leading_flags(body)
    flags = dict(parsed_flags)
    if remaining.startswith("["):
        values = json.loads(remaining)
        if not isinstance(values, list) or not all(
            isinstance(value, str) for value in values
        ):
            raise ValueError("invalid JSON COPY/ADD")
    else:
        if "\\" in remaining:
            # BuildKit's shell-form COPY/ADD word splitting is not POSIX shlex.
            # Backslash-containing forms use the full context rather than risk
            # selecting a different set of sources.
            raise ValueError("escaped shell COPY/ADD requires full context")
        values = shlex.split(remaining, posix=True)
    if len(values) < 2:
        raise ValueError("COPY/ADD is missing source or destination")
    return flags, values


def _split_leading_flags(body: str) -> Tuple[List[Tuple[str, str]], str]:
    flags = []
    remaining = body.lstrip()
    while remaining.startswith("--"):
        raw_token, remaining = _take_word(remaining)
        decoded = shlex.split(raw_token, posix=True)
        if len(decoded) != 1 or not decoded[0].startswith("--"):
            raise ValueError("invalid Dockerfile instruction flag")
        key, has_value, value = decoded[0][2:].partition("=")
        key = key.lower()
        if not _FLAG_NAME_PATTERN.fullmatch(key):
            raise ValueError("invalid Dockerfile instruction flag")
        if key == "mount" and any(character in raw_token for character in ('"', "'")):
            # BuildKit parses mount values as CSV after Dockerfile word
            # processing. Quoted CSV values are deliberately outside the
            # subset implemented here.
            raise ValueError("quoted RUN mount requires full context")
        flags.append((key, value if has_value else ""))
        remaining = remaining.lstrip()
    return flags, remaining


def _take_word(value: str) -> Tuple[str, str]:
    quote: Optional[str] = None
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == "\\" and quote != "'":
            escaped = True
            continue
        if quote is not None:
            if character == quote:
                quote = None
            continue
        if character in ('"', "'"):
            quote = character
        elif character.isspace():
            return value[:index], value[index:]
    if quote is not None or escaped:
        raise ValueError("unterminated Dockerfile instruction word")
    return value, ""


def _parse_mount_options(value: str) -> Dict[str, str]:
    options = {}
    for field in value.split(","):
        key, has_value, option_value = field.partition("=")
        key = key.strip().lower()
        if not key:
            raise _AnalysisFallback("run_mount_parse_failed")
        options[key] = option_value.strip() if has_value else ""
    return options


def _source_has_pattern(source: str) -> bool:
    return any(character in source for character in ("*", "?", "["))


def _is_official_dockerfile_frontend(reference: str) -> bool:
    normalized = reference.strip()
    if normalized.startswith("docker-image://"):
        normalized = normalized[len("docker-image://") :]
    normalized = normalized.split("@", 1)[0]
    last_slash = normalized.rfind("/")
    last_colon = normalized.rfind(":")
    if last_colon > last_slash:
        normalized = normalized[:last_colon]
    return normalized in {
        "docker/dockerfile",
        "docker.io/docker/dockerfile",
        "index.docker.io/docker/dockerfile",
        "docker/dockerfile-upstream",
        "docker.io/docker/dockerfile-upstream",
        "index.docker.io/docker/dockerfile-upstream",
    }


def _is_remote_add_source(source: str) -> bool:
    if _SCP_GIT_SOURCE_PATTERN.match(source):
        return True
    try:
        parsed = urlsplit(source)
    except ValueError:
        return False
    return bool(parsed.scheme and parsed.scheme.lower() != "file")
