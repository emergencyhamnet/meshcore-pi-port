#!/usr/bin/env bash
# Bundle Pi-only sources/scripts the repo is missing, plus content diffs of tracked files vs a tag.
set -u
cd /home/n2dh/meshcore-pi-port || exit 1
TAG="${1:-v0.2.0-alpha1}"
OUT=/tmp/pi-reconcile
rm -rf "$OUT"; mkdir -p "$OUT/files"
# Untracked, non-ignored, source-like files only.
git status --short | grep '^??' | awk '{print $2}' \
  | grep -v -E '^(\.build/|bin/|deploy/|docs/|meshcore-pi-port/|scripts/__pycache__/|.*\.tgz$|.*\.txt$)' \
  | while read -r p; do
      if [ -f "$p" ]; then mkdir -p "$OUT/files/$(dirname "$p")"; tr -d '\r' < "$p" > "$OUT/files/$p"; echo "$p"; fi
    done > "$OUT/untracked-list.txt"
# Content diff of tracked runtime files vs the tag, ignoring CR and whitespace.
git diff --ignore-cr-at-eol --ignore-all-space "$TAG" -- main platform Stream.h FS.h Arduino.h build.sh scripts/build-pi-live-runtime.sh scripts/run-pi-live-runtime.sh scripts/run-pi-browser-ui.sh scripts/run-pi-gateway-link.sh scripts/install-pi-live-runtime-service.sh scripts/install-pi-browser-ui-service.sh scripts/install-pi-gateway-link-service.sh ui-native > "$OUT/tracked-vs-tag.diff"
# Deployed unit files, CR-stripped.
mkdir -p "$OUT/etc-systemd"
for u in meshcore-pi-live-runtime meshcore-pi-browser-ui meshcore-pi-gateway-link; do
  [ -f "/etc/systemd/system/$u.service" ] && tr -d '\r' < "/etc/systemd/system/$u.service" > "$OUT/etc-systemd/$u.service"
done
echo "untracked files: $(wc -l < "$OUT/untracked-list.txt")"
echo "tracked diff lines: $(wc -l < "$OUT/tracked-vs-tag.diff")"
tar -czf /tmp/pi-reconcile.tgz -C /tmp pi-reconcile
ls -la /tmp/pi-reconcile.tgz
