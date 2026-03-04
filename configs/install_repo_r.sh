#!/bin/bash
set -euxo pipefail

# fail early if r is missing so we do not continue with partial setup.
if ! command -v Rscript >/dev/null 2>&1; then
    echo "Error: Rscript not found in PATH"
    exit 1
fi

CRAN_MIRROR="${SWESMITH_CRAN_MIRROR:-https://cloud.r-project.org}"

# install base tools we need in most r repos.
Rscript -e "options(repos=c(CRAN='${CRAN_MIRROR}')); install.packages(c('remotes', 'testthat', 'pkgload'), Ncpus=2)"

if [ -f "renv.lock" ]; then
    # if renv is present, prefer it because it is the repo's pinned environment.
    Rscript -e "if (!requireNamespace('renv', quietly=TRUE)) install.packages('renv', Ncpus=2)"
    Rscript -e "renv::restore(prompt=FALSE)"
elif [ -f "DESCRIPTION" ]; then
    # fallback for plain package repos without renv lock files.
    Rscript -e "remotes::install_deps(dependencies=TRUE, upgrade='never')"
else
    echo "Error: Neither renv.lock nor DESCRIPTION found. Cannot resolve dependencies."
    exit 1
fi

# install the local package after deps so tests use local code, not a remote release.
Rscript -e "remotes::install_local('.', dependencies=FALSE, upgrade='never', force=TRUE)"

if [ -n "${SWESMITH_EXTRA_R_DEPS:-}" ]; then
    # optional escape hatch for missing system-specific test deps.
    Rscript -e "deps <- strsplit(Sys.getenv('SWESMITH_EXTRA_R_DEPS'), ' +')[[1]]; deps <- deps[nzchar(deps)]; if (length(deps) > 0) install.packages(deps, Ncpus=2)"
fi
