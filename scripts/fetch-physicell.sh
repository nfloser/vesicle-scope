#!/usr/bin/env bash
set -euo pipefail

readonly script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly repo_root="$(cd "${script_dir}/.." && pwd)"
readonly pin_file="${repo_root}/vesiclescope/engines/physicell.env"

# This file is repository-controlled metadata, not user input.
# shellcheck source=/dev/null
source "${pin_file}"

: "${PHYSICELL_RELEASE:?missing PHYSICELL_RELEASE in pin metadata}"
: "${PHYSICELL_COMMIT:?missing PHYSICELL_COMMIT in pin metadata}"
: "${BIOFVM_VERSION:?missing BIOFVM_VERSION in pin metadata}"

readonly upstream="https://github.com/MathCancer/PhysiCell.git"
readonly target="${1:-.deps/physicell}"

verify_checkout() {
  local checkout="$1"
  local actual_sha
  local actual_biofvm_version

  actual_sha="$(git -C "${checkout}" rev-parse HEAD)"
  if [[ "${actual_sha}" != "${PHYSICELL_COMMIT}" ]]; then
    printf 'PhysiCell checkout is %s, expected %s\n'       "${actual_sha}" "${PHYSICELL_COMMIT}" >&2
    return 1
  fi

  actual_biofvm_version="$(
    sed -n 's/.*BioFVM_Version = "\([^"]*\)".*/\1/p'       "${checkout}/BioFVM/BioFVM_MultiCellDS.cpp" | head -n 1
  )"
  if [[ "${actual_biofvm_version}" != "${BIOFVM_VERSION}" ]]; then
    printf 'BioFVM source reports version %s, expected %s\n'       "${actual_biofvm_version:-<missing>}" "${BIOFVM_VERSION}" >&2
    return 1
  fi
}

if [[ -d "${target}/.git" ]]; then
  verify_checkout "${target}"
  printf 'PhysiCell already pinned at %s (BioFVM %s)\n'     "${PHYSICELL_COMMIT}" "${BIOFVM_VERSION}"
  exit 0
fi

if [[ -e "${target}" ]]; then
  printf 'Refusing to overwrite existing non-git path: %s\n' "${target}" >&2
  exit 1
fi

mkdir -p "$(dirname "${target}")"
git clone --quiet --depth 1 --branch "${PHYSICELL_RELEASE}" "${upstream}" "${target}"
verify_checkout "${target}"

printf 'Fetched PhysiCell %s at %s (BioFVM %s)\n'   "${PHYSICELL_RELEASE}" "${PHYSICELL_COMMIT}" "${BIOFVM_VERSION}"
