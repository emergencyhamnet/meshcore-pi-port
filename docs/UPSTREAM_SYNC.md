# Upstream Sync

Keep upstream history visible and keep the Pi diff small.

Branch model:

1. `upstream-main` mirrors upstream MeshCore.
2. `pi-port-main` contains Pi-only adaptation.
3. `pi-port-integration` is optional for sync testing.

Recommended sync flow:

```powershell
git checkout upstream-main
git fetch upstream
git merge --ff-only upstream/main

git checkout pi-port-main
git merge upstream-main
```

If conflicts appear, resolve Pi platform conflicts first. Treat conflicts in donor behavior files as high-risk and require justification.