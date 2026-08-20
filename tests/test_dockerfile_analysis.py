import pytest

from hyperbrowser.client.managers.sandboxes.dockerfile_analysis import (
    analyze_dockerfile_sources,
)


# These cases are adapted from the BuildKit v0.30 parser/instruction suites and
# Hyperbrowser CLI's TestAnalyzeDockerfileLocalSources. The SDK may safely fall
# back to a full context for syntax outside its intentionally small subset.
@pytest.mark.parametrize(
    ("dockerfile", "expected_groups", "expected_fallback"),
    [
        pytest.param(
            """\
FROM scratch AS source
COPY ["one file", "two", "/dest/"]
COPY --chown=1:1 --chmod=0755 dir /dir
COPY --from=source /generated /generated
""",
            [["one file", "two"], ["dir"]],
            "",
            id="copy-json-flags-and-stage",
        ),
        pytest.param(
            """\
# syntax=docker/dockerfile:1-labs
FROM scratch
COPY --link --parents --exclude=*.tmp \\
  quoted-dir \\
  plain /dest/
""",
            [["quoted-dir", "plain"]],
            "",
            id="continuations-and-modern-copy-flags",
        ),
        pytest.param(
            "FROM scratch\nCOPY\tfile.txt\t/dest/\n",
            [["file.txt"]],
            "",
            id="tab-separated-copy",
        ),
        pytest.param(
            """\
FROM scratch
COPY "one file" /dest/
""",
            [["one file"]],
            "",
            id="quoted-shell-copy-source",
        ),
        pytest.param(
            """\
FROM scratch
ADD local.tar /local/
ADD https://example.com/archive.tar /remote/
ADD https://example.com/archive.tar?version=1 /remote-query/
ADD git://example.com/repository /git/
ADD git@github.com:moby/buildkit.git /ssh-git/
""",
            [["local.tar"]],
            "",
            id="local-and-remote-add",
        ),
        pytest.param(
            """\
FROM scratch
ADD assets:latest /colon/
ADD http:archive.tar /http-colon/
ADD oci-layout://example/image /unsupported-scheme/
""",
            [
                ["assets:latest"],
                ["http:archive.tar"],
                ["oci-layout://example/image"],
            ],
            "",
            id="add-colon-paths-and-unsupported-schemes-are-local",
        ),
        pytest.param(
            """\
FROM scratch AS generated
RUN --mount=type=bind,source=src,target=/src true
RUN --mount=source=vendor,target=/vendor true
RUN --mount=type=bind,target=/context true
RUN --mount=type=bind,from=generated,source=/out,target=/out true
RUN --mount=type=cache,target=/cache true
RUN echo --mount=type=bind,source=not-a-builder-flag,target=/src
""",
            [["src"], ["vendor"], ["."]],
            "",
            id="run-bind-mounts",
        ),
        pytest.param(
            "FROM scratch\nARG SOURCE=src\nCOPY $SOURCE /app\n",
            [],
            "copy_source_requires_expansion",
            id="copy-variable",
        ),
        pytest.param(
            "FROM scratch\nADD ${SOURCE} /app\n",
            [],
            "add_source_requires_expansion",
            id="add-variable",
        ),
        pytest.param(
            "FROM scratch\nRUN --mount=type=bind,source=$SOURCE,target=/src true\n",
            [],
            "run_bind_source_requires_expansion",
            id="run-bind-variable",
        ),
        pytest.param(
            "FROM scratch\nCOPY src/*.py /app\n",
            [],
            "dockerfile_source_pattern",
            id="copy-glob-uses-full-context",
        ),
        pytest.param(
            'FROM scratch\nCOPY ["foo\\\\bar", "/app/"]\n',
            [],
            "dockerfile_source_path",
            id="copy-backslash-path-uses-full-context",
        ),
        pytest.param(
            'FROM scratch\nRUN --mount=type=bind,source="dir with space",target=/src true\n',
            [],
            "run_mount_parse_failed",
            id="quoted-run-mount-uses-full-context",
        ),
        pytest.param(
            """\
# syntax=example.com/acme/custom-frontend:v2
FROM scratch
COPY src /app
""",
            [],
            "custom_dockerfile_frontend",
            id="custom-frontend",
        ),
        pytest.param(
            "FROM scratch\nCUSTOM source /app\n",
            [],
            "dockerfile_instruction_parse_failed",
            id="unknown-instruction",
        ),
        pytest.param(
            """\
FROM scratch
COPY <<EOF /inline
hello
EOF
""",
            [],
            "dockerfile_instruction_parse_failed",
            id="copy-heredoc",
        ),
        pytest.param(
            "# escape=`\nFROM scratch\nCOPY dir /dir\n",
            [],
            "dockerfile_parse_failed",
            id="alternate-escape-directive",
        ),
        pytest.param(
            "FROM scratch\n" "COPY dir \\\n" "# comment in continuation\n" "  /dir\n",
            [],
            "dockerfile_parse_failed",
            id="comment-in-continuation",
        ),
        pytest.param(
            "FROM scratch\nONBUILD ADD . /app/src\n",
            [],
            "",
            id="onbuild-does-not-consume-current-context",
        ),
    ],
)
def test_analyze_dockerfile_sources(dockerfile, expected_groups, expected_fallback):
    groups, fallback = analyze_dockerfile_sources(dockerfile.encode())

    assert groups == expected_groups
    assert fallback == expected_fallback


def test_analyze_dockerfile_sources_falls_back_for_non_utf8():
    groups, fallback = analyze_dockerfile_sources(b"FROM scratch\n# \xff\n")

    assert groups == []
    assert fallback == "dockerfile_parse_failed"
