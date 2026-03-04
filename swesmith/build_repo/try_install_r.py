"""
Purpose: Test whether a set of installation commands works for a given R repository.

Usage: python -m swesmith.build_repo.try_install_r owner/repo configs/install_repo_r.sh --commit <commit>
"""

import argparse
import os
import subprocess

from dataclasses import dataclass
from pathlib import Path
from swesmith.constants import ENV_NAME, LOG_DIR_ENV
from swesmith.profiles.r import RProfile

DEFAULT_SMOKE_CMD = "Rscript -e \"testthat::test_local(reporter='tap')\""


def cleanup(repo_name: str) -> None:
    if os.path.exists(repo_name):
        subprocess.run(
            f"rm -rf {repo_name}",
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("> Removed repository")


def default_smoke_cmd(repo_dir: Path) -> str | None:
    # we only auto-run smoke tests when the repo has the standard
    # testthat entrypoint. this avoids guessing commands for custom layouts.
    testthat_entrypoint = repo_dir / "tests" / "testthat.R"
    if testthat_entrypoint.exists():
        return DEFAULT_SMOKE_CMD
    return None


def render_profile_stub(profile: RProfile) -> str:
    class_name = (
        f"{profile.repo.title().replace('-', '').replace('_', '')}{profile.commit[:8]}"
    )
    return f"""from dataclasses import dataclass
from swesmith.profiles.r import RProfile


@dataclass
class {class_name}(RProfile):
    owner: str = "{profile.owner}"
    repo: str = "{profile.repo}"
    commit: str = "{profile.commit}"
"""


def write_repro_artifacts(
    profile: RProfile, install_script: str, smoke_cmd: str | None
) -> None:
    # this folder gives us a replay trail for arbitrary repos:
    # one shell script to re-run the same setup, and one profile stub
    # to turn an ad-hoc install into a checked-in profile later.
    env_dir = LOG_DIR_ENV / profile.repo_name
    env_dir.mkdir(parents=True, exist_ok=True)

    with open(install_script, encoding="utf-8") as install_f:
        install_lines = [
            line.rstrip("\n") for line in install_f.readlines() if line.strip()
        ]

    replay_script = env_dir / f"sweenv_{profile.repo_name}.sh"
    replay_lines = [
        "#!/bin/bash",
        "set -euxo pipefail",
        f"git clone {profile._source_read_url}",
        f"cd {profile.repo}",
        f"git checkout {profile.commit}",
    ] + install_lines

    if smoke_cmd:
        replay_lines.append(smoke_cmd)

    with open(replay_script, "w", encoding="utf-8") as replay_f:
        replay_f.write("\n".join(replay_lines) + "\n")
    replay_script.chmod(0o755)

    with open(env_dir / "profile_stub.py", "w", encoding="utf-8") as stub_f:
        stub_f.write(render_profile_stub(profile) + "\n")

    print(f"> Wrote reproducibility artifacts to {env_dir}")


def build_image_profile(profile: RProfile, test_cmd: str) -> None:
    # this ad-hoc class lets us call the existing profile image builder
    # without adding a permanent profile to the registry.
    def _dockerfile(self):
        return f"""FROM rocker/r-ver:{self.r_version}
RUN apt-get update && apt-get install -y git build-essential libcurl4-openssl-dev libssl-dev libxml2-dev \
&& rm -rf /var/lib/apt/lists/*

RUN git clone {self._source_read_url} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN Rscript -e "options(repos=c(CRAN='https://cloud.r-project.org')); install.packages(c('remotes','testthat'), Ncpus=2)"
RUN Rscript -e "remotes::install_deps(dependencies=TRUE, upgrade='never')"
RUN Rscript -e "remotes::install_local('.', dependencies=FALSE, upgrade='never', force=TRUE)"
RUN {self.test_cmd} || true
"""

    adhoc_profile_cls = dataclass(
        type(
            "AdHocRProfile",
            (RProfile,),
            {
                "owner": profile.owner,
                "repo": profile.repo,
                "commit": profile.commit,
                "dockerfile": property(_dockerfile),
            },
        )
    )
    adhoc_profile = adhoc_profile_cls()
    adhoc_profile.test_cmd = test_cmd
    adhoc_profile.build_image()


def main(
    repo: str,
    install_script: str,
    commit: str = "latest",
    no_cleanup: bool = False,
    force: bool = False,
    smoke_cmd: str | None = None,
    skip_smoke: bool = False,
    extra_r_deps: str | None = None,
    build_image: bool = False,
) -> None:
    # this command is intentionally profile-free: users can test any repo first,
    # then promote it to a real profile once setup is stable.
    print(f"> Building R environment for {repo} at commit {commit or 'latest'}")
    owner, repo_name = repo.split("/")
    profile = RProfile()
    profile.owner = owner
    profile.repo = repo_name

    assert os.path.exists(install_script), (
        f"Installation script {install_script} does not exist"
    )
    assert install_script.endswith(".sh"), "Installation script must be a bash script"
    install_script = os.path.abspath(install_script)

    env = os.environ.copy()
    if extra_r_deps:
        env["SWESMITH_EXTRA_R_DEPS"] = extra_r_deps

    base_cwd = os.getcwd()
    try:
        profile._configure_ssh_env()
        if not os.path.exists(profile.repo):
            subprocess.run(
                f"git clone {profile._source_read_url}",
                check=True,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        os.chdir(profile.repo)

        if commit != "latest":
            subprocess.run(
                f"git checkout {commit}",
                check=True,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # pin to current head so artifact paths and replay scripts are reproducible.
            commit = subprocess.check_output(
                "git rev-parse HEAD", shell=True, text=True
            ).strip()
        profile.commit = commit
        print(f"> Cloned {profile.repo} at commit {commit}")

        env_dir = LOG_DIR_ENV / profile.repo_name
        if env_dir.exists() and not force:
            # we ask before overwrite to avoid quietly mixing old and new runs.
            overwrite = input(
                f"> Artifact directory {env_dir} already exists. Overwrite? (y/n) "
            ).strip()
            if overwrite.lower() != "y":
                raise RuntimeError("Terminating without overwrite")

        print("> Running installation script...")
        subprocess.run(
            ["bash", "-lc", f". {install_script}"],
            check=True,
            env=env,
        )
        print("> Successfully installed repository")

        if not skip_smoke:
            resolved_smoke_cmd = smoke_cmd or default_smoke_cmd(Path.cwd())
            if resolved_smoke_cmd is None:
                raise ValueError(
                    "No default smoke test found (expected tests/testthat.R). Use --smoke-cmd or --skip-smoke."
                )
            print(f"> Running smoke test: {resolved_smoke_cmd}")
            subprocess.run(
                resolved_smoke_cmd,
                check=True,
                shell=True,
                env=env,
            )
            print("> Smoke test passed")
        else:
            resolved_smoke_cmd = None
            print("> Skipping smoke test")

        os.chdir(base_cwd)
        write_repro_artifacts(profile, install_script, resolved_smoke_cmd)

        if build_image:
            image_test_cmd = resolved_smoke_cmd or DEFAULT_SMOKE_CMD
            print("> Building Docker image with ad-hoc R profile...")
            build_image_profile(profile, image_test_cmd)
            print(f"> Built image: {profile.image_name}")

    except Exception as e:
        print(f"> Installation procedure failed: {e}")
    finally:
        os.chdir(base_cwd)
        if not no_cleanup:
            cleanup(profile.repo)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "repo", type=str, help="Repository name in the format of 'owner/repo'"
    )
    parser.add_argument(
        "install_script",
        type=str,
        help="Bash script with installation commands (e.g. configs/install_repo_r.sh)",
    )
    parser.add_argument(
        "-c",
        "--commit",
        type=str,
        help="Commit hash to build at (default: latest)",
        default="latest",
    )
    parser.add_argument(
        "--no_cleanup",
        action="store_true",
        help="Do not remove the cloned repository after installation",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite of existing build artifacts",
    )
    parser.add_argument(
        "--smoke-cmd",
        type=str,
        help="Optional smoke test command to run after install",
        default=None,
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip running smoke tests after install",
    )
    parser.add_argument(
        "--extra-r-deps",
        type=str,
        help="Additional space-separated R packages to install",
        default=None,
    )
    parser.add_argument(
        "--build-image",
        action="store_true",
        help="Build a Docker image after a successful install",
    )

    args = parser.parse_args()
    main(**vars(args))
