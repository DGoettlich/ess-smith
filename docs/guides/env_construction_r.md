# R Environment Options

This guide covers R-specific repository setup using `try_install_r`.

## Quickstart

```bash
python -m swesmith.build_repo.try_install_r marcelortizv/triplediff configs/install_repo_r.sh \
    --commit 6199f5efe02571ad677cad5a669c1a4a15caea3c
```

If successful, artifacts are written under `logs/build_images/env/<owner>__<repo>.<hash>/`:

- `sweenv_<owner>__<repo>.<hash>.sh`: replay script for install + smoke test
- `profile_stub.py`: starter `RProfile` subclass definition

## Flags

- `--smoke-cmd "<cmd>"`: override default smoke command
- `--skip-smoke`: skip smoke testing
- `--extra-r-deps "pkg1 pkg2"`: install additional CRAN packages
- `--build-image`: build a Docker image after successful install
- `--force`: overwrite existing artifact directory without prompt
- `--no_cleanup`: keep local clone after completion

## Default Smoke Test

When `tests/testthat.R` is present, the default smoke command is:

```bash
Rscript -e "testthat::test_local(reporter='tap')"
```

If `tests/testthat.R` is missing, pass `--smoke-cmd` or `--skip-smoke`.
