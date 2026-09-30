#!/usr/bin/env bash
set -euo pipefail

readonly upstream="https://github.com/MathCancer/PhysiCell.git"
readonly tag="1.14.2"
readonly expected_sha="dbd3499250141b27600e91e501c54c46f68f2763"
readonly target="${1:-.deps/physicell}"

if [[ -d "${target}/.git" ]]; then
  actual_sha="$(git -C "${target}" rev-parse HEAD)"
  if [[ "${actual_sha}" == "${expected_sha}" ]]; then
    printf 'PhysiCell already pinned at %s\n' "${expected_sha}"
    exit 0
  fi

  printf 'Refusing to reuse %s at unexpected commit %s\n' "${target}" "${actual_sha}" >&2
  exit 1
fi

if [[ -e "${target}" ]]; then
  printf 'Refusing to overwrite existing non-git path: %s\n' "${target}" >&2
  exit 1
fi

mkdir -p "$(dirname "${target}")"
git clone --quiet --depth 1 --branch "${tag}" "${upstream}" "${target}"

actual_sha="$(git -C "${target}" rev-parse HEAD)"
if [[ "${actual_sha}" != "${expected_sha}" ]]; then
  printf 'PhysiCell tag %s resolved to %s, expected %s\n'     "${tag}" "${actual_sha}" "${expected_sha}" >&2
  exit 1
fi

printf 'Fetched PhysiCell %s at %s\n' "${tag}" "${actual_sha}"
