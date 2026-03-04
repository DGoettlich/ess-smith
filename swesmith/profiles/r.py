import re

from dataclasses import dataclass, field
from swebench.harness.constants import TestStatus
from swesmith.constants import ENV_NAME
from swesmith.profiles.base import RepoProfile, registry


@dataclass
class RProfile(RepoProfile):
    """
    Profile for R repositories.
    """

    exts: list[str] = field(default_factory=lambda: [".R", ".r"])
    test_cmd: str = "Rscript -e \"testthat::test_local(reporter='tap')\""
    r_version: str = "4.3.3"

    def log_parser(self, log: str) -> dict[str, str]:
        """Parser for test logs generated with testthat TAP reporter."""
        test_status_map = {}
        context = ""

        # we parse tap lines directly because they are stable and explicit
        # across testthat runs: "ok", "not ok", and skip directives.
        status_pattern = re.compile(
            r"^(?P<status>ok|not ok)\s+(?P<num>\d+)(?:\s+(?P<rest>.*))?$"
        )

        for line in log.splitlines():
            line = line.strip()
            if not line:
                continue

            # tap uses "# ..." lines as context headers.
            # we keep this context to make test ids less ambiguous.
            if line.startswith("#") and "SKIP" not in line.upper():
                context = line.lstrip("#").strip()
                continue

            status_match = status_pattern.match(line)
            if not status_match:
                continue

            status_word = status_match.group("status")
            test_num = status_match.group("num")
            remainder = (status_match.group("rest") or "").strip()

            if status_word == "not ok":
                status = TestStatus.FAILED.value
            elif remainder.upper().startswith("# SKIP"):
                status = TestStatus.SKIPPED.value
            else:
                status = TestStatus.PASSED.value

            # tap lines can be unnamed, especially for skip lines.
            # in that case we generate a deterministic fallback id.
            if status == TestStatus.SKIPPED.value or not remainder:
                test_name = f"tap_test_{test_num}"
            else:
                # Remove trailing TAP directives like "# TODO ...".
                test_name = remainder.split(" # ", 1)[0].strip()
                if not test_name:
                    test_name = f"tap_test_{test_num}"

            if context:
                test_name = f"{context}::{test_name}"
            test_status_map[test_name] = status

        return test_status_map

    @property
    def dockerfile(self):
        # we run tests once during image build as a warmup step.
        # this uses "|| true" so image creation still succeeds even if tests fail,
        # matching the existing repo behavior where validation happens later.
        return f"""FROM rocker/r-ver:{self.r_version}
RUN apt-get update && apt-get install -y git build-essential libcurl4-openssl-dev libssl-dev libxml2-dev \
&& rm -rf /var/lib/apt/lists/*

RUN git clone {self.mirror_url} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN Rscript -e "options(repos=c(CRAN='https://cloud.r-project.org')); install.packages(c('remotes','testthat'), Ncpus=2)"
RUN Rscript -e "remotes::install_deps(dependencies=TRUE, upgrade='never')"
RUN Rscript -e "remotes::install_local('.', dependencies=FALSE, upgrade='never', force=TRUE)"
RUN {self.test_cmd} || true
"""


@dataclass
class Triplediff6199f5ef(RProfile):
    owner: str = "marcelortizv"
    repo: str = "triplediff"
    commit: str = "6199f5efe02571ad677cad5a669c1a4a15caea3c"
    timeout: int = 300


# Register all R profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, RProfile)
        and obj.__name__ != "RProfile"
    ):
        registry.register_profile(obj)
