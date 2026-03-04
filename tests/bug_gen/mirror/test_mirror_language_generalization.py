from swesmith.bug_gen.mirror.generate import _extract_output, should_attempt_recovery
from swesmith.constants import KEY_PATCH


def test_extract_output_handles_generic_code_fence():
    output = "Explanation\n```r\nx <- 1\n```\n"
    assert _extract_output(output) == "x <- 1"


def test_extract_output_falls_back_to_raw_text():
    output = "x <- function(x) x + 1"
    assert _extract_output(output) == output


def test_should_attempt_recovery_with_r_extension(tmp_path):
    repo = tmp_path / "repo"
    src_dir = repo / "R"
    src_dir.mkdir(parents=True)
    (src_dir / "foo.R").write_text("foo <- function(x) x\n", encoding="utf-8")

    patch = """diff --git a/R/foo.R b/R/foo.R
index 1111111..2222222 100644
--- a/R/foo.R
+++ b/R/foo.R
@@ -1 +1 @@
-foo <- function(x) x
+foo <- function(x) x + 1
"""
    inst = {KEY_PATCH: patch}

    attempt, reason = should_attempt_recovery(inst, str(repo), exts=[".R", ".r"])
    assert attempt is True
    assert reason is None


def test_should_attempt_recovery_rejects_unsupported_extensions(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "file.py").write_text("print('hello')\n", encoding="utf-8")
    patch = """diff --git a/file.py b/file.py
index 1111111..2222222 100644
--- a/file.py
+++ b/file.py
@@ -1 +1 @@
-print('hello')
+print('world')
"""
    inst = {KEY_PATCH: patch}

    attempt, reason = should_attempt_recovery(inst, str(repo), exts=[".R"])
    assert attempt is False
    assert reason == "No supported source files changed"
