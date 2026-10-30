#!/usr/bin/env bash
# Compare the live Pi checkout against a tag, ignoring line-ending and whitespace noise.
set -u
cd /home/n2dh/meshcore-pi-port || exit 1
TAG="${1:-v0.2.0-alpha1}"
git fetch -q origin --tags 2>&1 | tail -1
echo "== HEAD"; git log --oneline -1
echo "== real diffs vs HEAD (ignore CR/space)"; git diff --ignore-cr-at-eol --ignore-all-space --stat HEAD | tail -1
echo "== real diffs vs $TAG (ignore CR/space)"; git diff --ignore-cr-at-eol --ignore-all-space --stat "$TAG" | tail -1
echo "== files with real content diffs vs $TAG (runtime-relevant paths)"
git diff --ignore-cr-at-eol --ignore-all-space --name-only "$TAG" | grep -E '^(main/|ui-native/|scripts/|deploy/|platform/|Stream\.h|FS\.h|Arduino\.h|build\.sh|README\.md)' | head -80
echo "== untracked non-ignored"
git status --short | grep '^??' | head -40
echo "== live service files"
for u in meshcore-pi-live-runtime meshcore-pi-browser-ui meshcore-pi-gateway-link; do
  echo "-- $u: $(systemctl is-active $u.service 2>/dev/null)"
  systemctl cat "$u.service" 2>/dev/null | grep -E 'ExecStart|WorkingDirectory|Environment=' | sed 's/^/   /'
done
echo "== deployed unit vs repo unit (diff lines)"
for u in meshcore-pi-live-runtime meshcore-pi-browser-ui meshcore-pi-gateway-link; do
  if [ -f "/etc/systemd/system/$u.service" ]; then
    echo "-- $u: $(diff <(tr -d '\r' < /etc/systemd/system/$u.service) <(tr -d '\r' < deploy/systemd/$u.service) | wc -l) differing lines"
  fi
done
