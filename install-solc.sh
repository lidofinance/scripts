#!/usr/bin/env bash
set -euo pipefail

SOLC_DIR="${HOME}/.solcx"

mkdir -p "${SOLC_DIR}"

SOLC_VERSIONS=(
  "0.4.24+commit.e67f0147"
  "0.5.14+commit.01f1aaa4"
  "0.5.12+commit.7709ece9"
  "0.6.12+commit.27d51765"
  "0.8.28+commit.7893614a"
  "0.8.10+commit.fc410830"
  "0.8.9+commit.e5eed63a"
  "0.8.4+commit.c7e474f2"
  "0.8.6+commit.11564f7e"
  "0.7.6+commit.7338295f"
  "0.8.15+commit.e14f2714"
  "0.8.19+commit.7dd6d404"
  "0.8.24+commit.e11b9ed9"
  "0.8.25+commit.b61c2a91"
  "0.8.21+commit.d9974bed"
  "0.6.11+commit.5ef660b1"
  "0.8.26+commit.8a97fa7a"
  "0.8.31+commit.fd3a2265"
)

for version in "${SOLC_VERSIONS[@]}"; do
  echo "========================================"
  echo "Downloading solc version: ${version}"

  # Example final URL:
  # https://binaries.soliditylang.org/linux-amd64/solc-linux-amd64-v0.6.11+commit.5ef660b1
  url="https://binaries.soliditylang.org/linux-amd64/solc-linux-amd64-v${version}"
  bin_path="${SOLC_DIR}/solc-v${version}"

  echo "URL:    ${url}"
  echo "Target: ${bin_path}"

  curl -L "${url}" -o "${bin_path}"

  chmod +x "${bin_path}"

  echo "Checking solc version for ${version}..."
  output="$("${bin_path}" --version || true)"
  echo "${output}"

  expected="Version: ${version}"

  if [[ "${output}" != *"${expected}"* ]]; then
    echo "❌ solc version mismatch!"
    echo "Expected: ${expected}"
    echo "Got:      ${output}"
    exit 1
  fi

  echo "✔ solc version ${version} is correct"
done