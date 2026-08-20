"""Docker-compatible ``.dockerignore`` parsing and matching.

The matching contract intentionally follows Moby ``patternmatcher`` v0.6.1,
which is also what the Hyperbrowser CLI reaches through BuildKit's filesystem
utilities.  Keeping this code separate from context traversal makes it easier
to differential-test when that upstream behavior changes.
"""

import posixpath
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Pattern, Tuple


_REGEX_META_WITHOUT_GLOB_MEANING = frozenset(".+()|{}$")


def _clean_path(value: str) -> str:
    """Apply the Unix ``filepath.Clean`` behavior used by the CLI."""

    # posixpath.normpath intentionally preserves exactly two leading slashes;
    # Go filepath.Clean on Unix collapses them, so normalize that difference.
    if value.startswith("//"):
        value = "/" + value.lstrip("/")
    return posixpath.normpath(value)


def _read_ignore_patterns(text: str) -> List[str]:
    """Parse ignore-file lines like Moby's ``ignorefile.ReadAll``."""

    patterns = []
    for index, raw_line in enumerate(text.split("\n")):
        if raw_line.endswith("\r"):
            raw_line = raw_line[:-1]
        if index == 0 and raw_line.startswith("\ufeff"):
            raw_line = raw_line[1:]
        if raw_line.startswith("#"):
            continue

        value = raw_line.strip()
        if not value:
            continue
        exclusion = value.startswith("!")
        if exclusion:
            value = value[1:].strip()
        if value:
            value = _clean_path(value)
            if len(value) > 1 and value.startswith("/"):
                value = value[1:]
        patterns.append(("!" if exclusion else "") + value)
    return patterns


@dataclass(frozen=True)
class _DockerIgnorePattern:
    value: str
    exclusion: bool
    match_type: str
    regexp: Optional[Pattern[str]]

    @classmethod
    def compile(cls, raw_pattern: str) -> "_DockerIgnorePattern":
        value = _clean_path(raw_pattern.strip())
        exclusion = value.startswith("!")
        if exclusion:
            if value == "!":
                raise ValueError('illegal exclusion pattern: "!"')
            value = value[1:]

        _validate_filepath_pattern(value)
        match_type, regexp = _compile_pattern(value)
        return cls(
            value=value,
            exclusion=exclusion,
            match_type=match_type,
            regexp=regexp,
        )

    def matches_path(self, path: str) -> bool:
        if self.match_type == "exact":
            return path == self.value
        if self.match_type == "prefix":
            return path.startswith(self.value[:-2])
        if self.match_type == "suffix":
            suffix = self.value[2:]
            return path.endswith(suffix) or (
                suffix.startswith("/") and path == suffix[1:]
            )
        if self.regexp is None:
            raise ValueError(f'invalid Docker ignore pattern: "{self.value}"')
        return self.regexp.match(path) is not None


def _compile_pattern(pattern: str) -> Tuple[str, Optional[Pattern[str]]]:
    """Compile one cleaned Moby pattern into its optimized match form."""

    regexp_parts = ["^"]
    match_type = "exact"
    cursor = 0
    token_index = 0
    while cursor < len(pattern):
        character = pattern[cursor]
        cursor += 1

        if character == "*":
            if cursor < len(pattern) and pattern[cursor] == "*":
                cursor += 1
                if cursor < len(pattern) and pattern[cursor] == "/":
                    cursor += 1

                if cursor == len(pattern):
                    if match_type == "exact":
                        match_type = "prefix"
                    else:
                        regexp_parts.append(".*")
                        match_type = "regexp"
                else:
                    regexp_parts.append("(?:.*/)?")
                    match_type = "regexp"

                if token_index == 0:
                    match_type = "suffix"
            else:
                regexp_parts.append("[^/]*")
                match_type = "regexp"
        elif character == "?":
            regexp_parts.append("[^/]")
            match_type = "regexp"
        elif character in _REGEX_META_WITHOUT_GLOB_MEANING:
            regexp_parts.append("\\" + character)
        elif character == "\\":
            if cursor < len(pattern):
                regexp_parts.append("\\" + pattern[cursor])
                cursor += 1
                match_type = "regexp"
            else:
                raise ValueError(
                    f'invalid Docker ignore pattern "{pattern}": trailing escape'
                )
        else:
            # Brackets remain regex syntax because they are also filepath glob
            # syntax. All other characters are literal in the Moby compiler.
            regexp_parts.append(character)
            if character in "[]":
                match_type = "regexp"

        token_index += 1

    if match_type != "regexp":
        return match_type, None

    regexp_parts.append("\\Z")
    try:
        return match_type, re.compile("".join(regexp_parts))
    except re.error as exc:
        raise ValueError(f'invalid Docker ignore pattern "{pattern}": {exc}') from exc


def _validate_filepath_pattern(pattern: str) -> None:
    """Reject malformed patterns using Go filepath.Match's Unix grammar."""

    cursor = 0
    while cursor < len(pattern):
        character = pattern[cursor]
        if character == "\\":
            cursor += 1
            if cursor == len(pattern):
                raise ValueError(
                    f'invalid Docker ignore pattern "{pattern}": trailing escape'
                )
        elif character == "[":
            cursor = _validate_character_class(pattern, cursor + 1)
            continue
        cursor += 1


def _validate_character_class(pattern: str, cursor: int) -> int:
    if cursor < len(pattern) and pattern[cursor] == "^":
        cursor += 1

    ranges = 0
    while True:
        if cursor < len(pattern) and pattern[cursor] == "]" and ranges:
            return cursor + 1
        cursor = _consume_character_class_value(pattern, cursor)
        if cursor < len(pattern) and pattern[cursor] == "-":
            cursor = _consume_character_class_value(pattern, cursor + 1)
        ranges += 1


def _consume_character_class_value(pattern: str, cursor: int) -> int:
    if cursor >= len(pattern) or pattern[cursor] in "-]":
        raise ValueError(f'invalid Docker ignore pattern "{pattern}"')
    if pattern[cursor] == "\\":
        cursor += 1
        if cursor >= len(pattern):
            raise ValueError(f'invalid Docker ignore pattern "{pattern}"')
    cursor += 1
    if cursor >= len(pattern):
        raise ValueError(f'invalid Docker ignore pattern "{pattern}"')
    return cursor


class DockerIgnoreMatcher:
    """Ordered Docker ignore matcher with parent-directory semantics."""

    def __init__(self, patterns: Iterable[str]):
        compiled = []
        for pattern in patterns:
            cleaned = pattern.strip()
            if not cleaned:
                continue
            compiled.append(_DockerIgnorePattern.compile(cleaned))
        self._patterns = tuple(compiled)
        self.has_negations = any(pattern.exclusion for pattern in self._patterns)

    @classmethod
    def from_file(cls, path: Path) -> "DockerIgnoreMatcher":
        text = path.read_bytes().decode("utf-8-sig")
        return cls(_read_ignore_patterns(text))

    @classmethod
    def from_text(cls, text: str) -> "DockerIgnoreMatcher":
        return cls(_read_ignore_patterns(text))

    def matches(self, relative_path: str) -> bool:
        # Traversal supplies slash-delimited paths. On Unix, a backslash can
        # be part of a filename and must remain available for glob escaping.
        path = _clean_path(relative_path)
        if path == ".":
            return False

        parent = posixpath.dirname(path)
        parent_parts = parent.split("/") if parent != "." else []
        matched = False
        for pattern in self._patterns:
            # An exclusion can only re-include an ignored path, and a normal
            # pattern only needs checking while the path is included.
            if pattern.exclusion != matched:
                continue

            pattern_matches = pattern.matches_path(path)
            if not pattern_matches:
                for length in range(1, len(parent_parts) + 1):
                    candidate = "/".join(parent_parts[:length])
                    if pattern.matches_path(candidate):
                        pattern_matches = True
                        break

            if pattern_matches:
                matched = not pattern.exclusion

        return matched
