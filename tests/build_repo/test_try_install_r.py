from swesmith.build_repo.try_install_r import default_smoke_cmd, render_profile_stub
from swesmith.profiles.r import RProfile


def test_default_smoke_cmd_detects_testthat_entrypoint(tmp_path):
    repo_dir = tmp_path / "repo"
    test_dir = repo_dir / "tests"
    test_dir.mkdir(parents=True)
    (test_dir / "testthat.R").write_text("library(testthat)\n", encoding="utf-8")
    assert (
        default_smoke_cmd(repo_dir)
        == "Rscript -e \"testthat::test_local(reporter='tap')\""
    )


def test_default_smoke_cmd_returns_none_without_testthat(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True)
    assert default_smoke_cmd(repo_dir) is None


def test_render_profile_stub_contains_expected_fields():
    profile = RProfile()
    profile.owner = "marcelortizv"
    profile.repo = "triplediff"
    profile.commit = "6199f5efe02571ad677cad5a669c1a4a15caea3c"

    stub = render_profile_stub(profile)
    assert "class Triplediff6199f5ef(RProfile)" in stub
    assert 'owner: str = "marcelortizv"' in stub
    assert 'repo: str = "triplediff"' in stub
    assert 'commit: str = "6199f5efe02571ad677cad5a669c1a4a15caea3c"' in stub
