# Git Bootstrap Commands

Use these commands to reproduce the local repository model from scratch.

## Create Local Repo From Upstream

```powershell
Set-Location "d:\Projects"
git clone https://github.com/meshcore-dev/MeshCore.git "meshcore-pi-port"
Set-Location "d:\Projects\meshcore-pi-port"
git remote rename origin upstream
git branch -m main upstream-main
git checkout -b pi-port-main
```

## Attach Your GitHub Repository

Replace the origin URL with your actual GitHub repository.

```powershell
Set-Location "d:\Projects\meshcore-pi-port"
git remote add origin <YOUR_GITHUB_REMOTE_URL>
git push -u origin upstream-main
git push -u origin pi-port-main
```

## Sync A New Upstream Release

```powershell
Set-Location "d:\Projects\meshcore-pi-port"
git checkout upstream-main
git fetch upstream
git merge --ff-only upstream/main
git checkout pi-port-main
git merge upstream-main
```