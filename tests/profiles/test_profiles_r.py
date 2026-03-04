from unittest.mock import patch

from swebench.harness.constants import TestStatus
from swesmith.constants import ENV_NAME
from swesmith.profiles.r import RProfile, Triplediff6199f5ef


def test_r_profile_defaults():
    profile = RProfile()
    assert profile.exts == [".R", ".r"]
    assert profile.test_cmd == "Rscript -e \"testthat::test_local(reporter='tap')\""


def test_r_profile_log_parser_tap():
    profile = RProfile()
    log = """
# preprocess
ok 1 handles preprocess input
not ok 2 fails preprocess edge case
# output
ok 3 # SKIP Reason: optional dependency
"""
    parsed = profile.log_parser(log)
    assert parsed["preprocess::handles preprocess input"] == TestStatus.PASSED.value
    assert parsed["preprocess::fails preprocess edge case"] == TestStatus.FAILED.value
    assert parsed["output::tap_test_3"] == TestStatus.SKIPPED.value


def test_r_profile_log_parser_empty():
    profile = RProfile()
    assert profile.log_parser("no tap output") == {}


def test_r_profile_dockerfile_uses_mirror_url():
    profile = Triplediff6199f5ef()
    with patch.object(type(profile), "_is_repo_private", return_value=False):
        dockerfile = profile.dockerfile
        assert "FROM rocker/r-ver:" in dockerfile
        assert (
            f"git clone https://github.com/{profile.mirror_name} /{ENV_NAME}"
            in dockerfile
        )


def test_r_profile_dockerfile_ssh_when_private():
    profile = Triplediff6199f5ef()
    with patch.object(type(profile), "_is_repo_private", return_value=True):
        dockerfile = profile.dockerfile
        assert (
            f"git clone git@github.com:{profile.mirror_name}.git /{ENV_NAME}"
            in dockerfile
        )


def test_triplediff_profile_fields():
    profile = Triplediff6199f5ef()
    assert isinstance(profile, RProfile)
    assert profile.owner == "marcelortizv"
    assert profile.repo == "triplediff"
    assert profile.commit == "6199f5efe02571ad677cad5a669c1a4a15caea3c"
    assert profile.timeout == 300
