param(
    [Parameter(Mandatory = $true)]
    [string]$OriginUrl
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

git remote get-url origin *> $null
if ($LASTEXITCODE -eq 0) {
    git remote set-url origin $OriginUrl
} else {
    git remote add origin $OriginUrl
}

git push -u origin upstream-main
git push -u origin pi-port-main