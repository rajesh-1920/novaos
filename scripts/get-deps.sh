#!/usr/bin/env sh
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
#
# get-deps.sh - Fetch the one external build dependency: the Limine bootloader.
#
# This clones the latest Limine *binary* branch (prebuilt boot files + the
# source for the small host-side `limine` install tool) into deps/limine and
# builds that host tool. The Limine protocol header (limine.h) and the font are
# vendored in-tree, so this is the only thing that needs the network.
#
# Re-running is safe and cheap (it pulls updates and rebuilds the host tool).
set -eu

REPO="https://github.com/limine-bootloader/limine.git"
DEPS_DIR="deps"
LIMINE_DIR="${DEPS_DIR}/limine"

mkdir -p "${DEPS_DIR}"

# Discover the newest "vN.x-binary" branch instead of hardcoding a version.
echo ">> Resolving latest Limine binary branch..."
BRANCH="$(git ls-remote --heads --refs "${REPO}" 'v*.x-binary' \
    | sed 's,.*refs/heads/,,' \
    | sort -V \
    | tail -1)"

if [ -z "${BRANCH}" ]; then
    echo "!! Could not determine a Limine binary branch (network problem?)." >&2
    exit 1
fi
echo ">> Using Limine branch: ${BRANCH}"

if [ -d "${LIMINE_DIR}/.git" ]; then
    echo ">> Updating existing checkout in ${LIMINE_DIR}..."
    git -C "${LIMINE_DIR}" fetch --depth=1 origin "${BRANCH}"
    git -C "${LIMINE_DIR}" checkout -q "${BRANCH}"
    git -C "${LIMINE_DIR}" reset -q --hard "origin/${BRANCH}"
else
    echo ">> Cloning Limine into ${LIMINE_DIR}..."
    rm -rf "${LIMINE_DIR}"
    git clone "${REPO}" --branch="${BRANCH}" --depth=1 "${LIMINE_DIR}"
fi

echo ">> Building the host 'limine' utility..."
make -C "${LIMINE_DIR}"

echo ">> Done. Limine is ready in ${LIMINE_DIR}."
