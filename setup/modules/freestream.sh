#!/usr/bin/env bash
# freestream is a python module vendored from Duke-QCD; the wrapper imports it
# from wrapper/external_packages.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"

src="$WORKDIR/models/freestream/freestream.py"
[[ -f "$src" ]] || die "models/freestream missing — run: git submodule update --init models/freestream"
mkdir -p "$WORKDIR/wrapper/external_packages"
cp -f "$src" "$WORKDIR/wrapper/external_packages/"
log "freestream.py copied to wrapper/external_packages/"
