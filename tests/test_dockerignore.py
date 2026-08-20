import pytest

from hyperbrowser.client.managers.sandboxes.dockerignore import (
    DockerIgnoreMatcher,
)


# Representative cases from the Moby patternmatcher v0.6.1 test matrix. The
# production implementation is standalone; these cases pin its compatibility
# contract with the matcher used by the Hyperbrowser CLI.
@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("**", "file", True),
        ("**/", "file/", True),
        ("**", "dir/file", True),
        ("**/**", "dir/file", True),
        ("dir/**", "dir/file", True),
        ("dir/**", "dir/dir2/file", True),
        ("**/dir", "dir", True),
        ("**/dir", "dir/file", True),
        ("**/dir2/*", "dir/dir2/file", True),
        ("**/dir2/**", "dir/dir2/dir3/file", True),
        ("**file", "file", True),
        ("**file", "dir/dir/file", True),
        ("**/file", "dir/dir/file", True),
        ("**/file*", "dir/dir/file.txt", True),
        ("**/file*txt", "dir/dir/file.txt", True),
        ("**/file*.txt*", "dir/dir/file.txt", True),
        ("**/**/*.txt", "dir/dir/file.txt", True),
        ("**/**/*.txt2", "dir/dir/file.txt", False),
        ("**/*.txt", "file.txt", True),
        ("a**/*.txt", "a/dir/dir/file.txt", True),
        ("a/*.txt", "a/dir/file.txt", False),
        ("a/*.txt", "a/file.txt", True),
        ("a/*.txt**", "a/file.txt", True),
        ("a*", "ab/c", True),
        ("a*/b", "abc/b", True),
        ("a*/b", "a/c/b", False),
        ("a*b*c*d*e*/f", "axbxcxdxexxx/f", True),
        ("a*b*c*d*e*/f", "axbxcxdxe/xxx/f", False),
        ("a*b?c*x", "abxbbxdbxebxczzx", True),
        ("a*b?c*x", "abxbbxdbxebxczzy", False),
        ("a[b-d]e", "ae", False),
        ("a[b-d]e", "ace", True),
        ("a[b-d]e", "aae", False),
        ("a[^b-d]e", "aze", True),
        (".*", ".foo", True),
        (".*", "foo", False),
        ("abc.def", "abcdef", False),
        ("abc.def", "abc.def", True),
        ("abc.def", "abcZdef", False),
        ("abc?def", "abcZdef", True),
        ("abc?def", "abcdef", False),
        (r"a\*b", "a*b", True),
        (r"a\*b", "ab", False),
        ("a?b", "a☺b", True),
        ("a[^a]b", "a☺b", True),
        ("a???b", "a☺b", False),
        ("a[^a][^a][^a]b", "a☺b", False),
        ("[a-ζ]*", "α", True),
        ("*[a-ζ]", "A", False),
        ("a?b", "a/b", False),
        ("a*b", "a/b", False),
        (r"[\]a]", "]", True),
        (r"[\-]", "-", True),
        (r"[x\-]", "x", True),
        (r"[x\-]", "-", True),
        (r"[x\-]", "z", False),
        (r"[\-x]", "x", True),
        (r"[\-x]", "-", True),
        (r"[\-x]", "a", False),
        ("**/foo/bar", "foo/bar", True),
        ("**/foo/bar", "dir/dir2/foo/bar", True),
        ("abc/**", "abc", False),
        ("abc/**", "abc/def/ghi", True),
        ("**/.foo", ".foo", True),
        ("**/.foo", "bar.foo", False),
        ("a(b)c/def", "a(b)c/def", True),
        ("a(b)c/def", "a(b)c/xyz", False),
        ("a.|)$(}+{bc", "a.|)$(}+{bc", True),
        (
            "dist/*.whl",
            "dist/proxy.py-2.4.0rc3.dev36+g08acad9-py3-none-any.whl",
            True,
        ),
    ],
)
def test_moby_pattern_matrix(pattern, path, expected):
    matcher = DockerIgnoreMatcher.from_text(pattern)

    assert matcher.matches(path) is expected


@pytest.mark.parametrize(
    ("patterns", "path", "expected"),
    [
        ("**\n!util/docker/web\n", "util/docker/web/foo", False),
        (
            "**\n!util/docker/web\nutil/docker/web/foo\n",
            "util/docker/web/foo",
            True,
        ),
        (
            "**\n!dist/proxy.py-2.4.0rc3.dev36+g08acad9-py3-none-any.whl\n",
            "dist/proxy.py-2.4.0rc3.dev36+g08acad9-py3-none-any.whl",
            False,
        ),
        ("**\n!dist/*.whl\n", "dist/package.whl", False),
        ("docs\n!docs/README.md\n", "docs/README.md", False),
        ("docs/*\n!docs/README.md\n", "docs/README.md", False),
    ],
)
def test_ordered_patterns_and_negations(patterns, path, expected):
    matcher = DockerIgnoreMatcher.from_text(patterns)

    assert matcher.matches(path) is expected


def test_ignorefile_preprocessing_handles_bom_comments_cleaning_and_slashes():
    matcher = DockerIgnoreMatcher.from_text(
        "\ufeff# comment\n  /build/../node_modules/  \n! /node_modules/keep.js\n"
    )

    assert matcher.has_negations is True
    assert matcher.matches("node_modules/drop.js") is True
    assert matcher.matches("node_modules/keep.js") is False
    assert matcher.matches("nested/node_modules/drop.js") is False


def test_comment_detection_happens_before_whitespace_trimming():
    matcher = DockerIgnoreMatcher.from_text(" #literal\n# actual comment\n")

    assert matcher.matches("#literal") is True


@pytest.mark.parametrize(
    "pattern",
    ["!", "[", "[^", "[^bc", "abc\\", "[]a]", "[-]", "[x-]", "[-x]", "[a-b-c]"],
)
def test_invalid_patterns_are_rejected_at_load_time(pattern):
    with pytest.raises(ValueError):
        DockerIgnoreMatcher.from_text(pattern)


def test_context_root_cannot_be_ignored():
    assert DockerIgnoreMatcher.from_text("**\n").matches(".") is False
