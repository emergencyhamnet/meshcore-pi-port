param(
    [ValidateSet('status', 'workbench', 'authority', 'both')]
    [string]$Mode = 'status',
    [switch]$Restart,
    [string]$BasestationRoot,
    [string]$PythonPath,
    [int]$WorkbenchPort = 18098,
    [int]$AuthorityPort = 8105,
    [int[]]$AdditionalWorkbenchPorts = @(18101, 8098)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-FirstExistingPath {
    param(
        [string[]]$Candidates,
        [string]$Description
    )

    foreach ($candidate in $Candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Unable to resolve $Description. Checked: $($Candidates -join ', ')"
}

function Get-PortListeners {
    param([int[]]$Ports)

    $rows = @()
    foreach ($port in $Ports) {
        $connections = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
        foreach ($connection in $connections) {
            $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($connection.OwningProcess)"
            $rows += [pscustomobject]@{
                Port = $port
                ProcessId = $connection.OwningProcess
                Name = $process.Name
                CommandLine = $process.CommandLine
            }
        }
    }

    $rows | Sort-Object Port, ProcessId -Unique
}

function Stop-PortListeners {
    param([int[]]$Ports)

    $listeners = @(Get-PortListeners -Ports $Ports)
    if ($listeners.Count -eq 0) {
        Write-Output "No listeners found on ports: $($Ports -join ', ')"
        return
    }

    foreach ($listener in $listeners) {
        Write-Output "Stopping PID $($listener.ProcessId) on port $($listener.Port): $($listener.Name)"
        Stop-Process -Id $listener.ProcessId -Force
    }
}

function Remove-BytecodeCaches {
    param([string]$Root)

    $cacheDirs = @(Get-ChildItem -Path (Join-Path $Root 'src') -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue)
    foreach ($cacheDir in $cacheDirs) {
        Remove-Item -LiteralPath $cacheDir.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Output "Removed $($cacheDirs.Count) __pycache__ directories under $Root\src"
}

function Start-WorkbenchProcess {
    param(
        [string]$RepoRoot,
        [string]$PythonExe,
        [int]$Port
    )

    $env:PYTHONPATH = Join-Path $RepoRoot 'src'
    $arguments = @(
        '-B',
        '-m', 'ehn_basestation.app.cli',
        '--env-file', (Join-Path $RepoRoot 'dev\windows\env\local-station.env'),
        'run-workbench-preview',
        '--host', '0.0.0.0',
        '--port', $Port
    )

    $process = Start-Process -FilePath $PythonExe -ArgumentList $arguments -WorkingDirectory $RepoRoot -PassThru
    Write-Output "Started workbench PID $($process.Id) on http://127.0.0.1:$Port/"
}

function Start-AuthorityProcess {
    param(
        [string]$RepoRoot,
        [string]$PythonExe,
        [int]$Port
    )

    $env:PYTHONPATH = Join-Path $RepoRoot 'src'
    $arguments = @(
        '-B',
        '-m', 'ehn_basestation.app.cli',
        '--env-file', (Join-Path $RepoRoot 'dev\windows\env\authority-station.env'),
        'run-authority-console',
        '--root', '.',
        '--host', '127.0.0.1',
        '--port', $Port
    )

    $process = Start-Process -FilePath $PythonExe -ArgumentList $arguments -WorkingDirectory $RepoRoot -PassThru
    Write-Output "Started authority console PID $($process.Id) on http://127.0.0.1:$Port/"
}

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$defaultBasestationRoot = Join-Path (Split-Path -Parent $workspaceRoot) 'ehn-basestation'
$resolvedBasestationRoot = Resolve-FirstExistingPath -Candidates @($BasestationRoot, $defaultBasestationRoot) -Description 'basestation root'
$resolvedPythonPath = Resolve-FirstExistingPath -Candidates @(
    $PythonPath,
    (Join-Path $workspaceRoot '.venv\Scripts\python.exe'),
    (Join-Path $resolvedBasestationRoot '.venv\Scripts\python.exe')
) -Description 'Python interpreter'

$workbenchPortsToClear = @($WorkbenchPort) + @($AdditionalWorkbenchPorts)
$allKnownPorts = $workbenchPortsToClear + @($AuthorityPort)

Write-Output "Basestation root: $resolvedBasestationRoot"
Write-Output "Python: $resolvedPythonPath"
Write-Output "Mode: $Mode"
Write-Output "Known ports: $($allKnownPorts -join ', ')"

if (-not $Restart) {
    $listeners = @(Get-PortListeners -Ports $allKnownPorts)
    if ($listeners.Count -eq 0) {
        Write-Output 'No active listeners found on known EHN Windows preview ports.'
    } else {
        $listeners | Format-Table Port, ProcessId, Name, CommandLine -AutoSize | Out-String | Write-Output
    }
    Write-Output 'Use -Restart with -Mode workbench, authority, or both to clean and relaunch canonical listeners.'
    return
}

switch ($Mode) {
    'workbench' {
        Stop-PortListeners -Ports $workbenchPortsToClear
        Remove-BytecodeCaches -Root $resolvedBasestationRoot
        Start-WorkbenchProcess -RepoRoot $resolvedBasestationRoot -PythonExe $resolvedPythonPath -Port $WorkbenchPort
    }
    'authority' {
        Stop-PortListeners -Ports @($AuthorityPort)
        Remove-BytecodeCaches -Root $resolvedBasestationRoot
        Start-AuthorityProcess -RepoRoot $resolvedBasestationRoot -PythonExe $resolvedPythonPath -Port $AuthorityPort
    }
    'both' {
        Stop-PortListeners -Ports $allKnownPorts
        Remove-BytecodeCaches -Root $resolvedBasestationRoot
        Start-WorkbenchProcess -RepoRoot $resolvedBasestationRoot -PythonExe $resolvedPythonPath -Port $WorkbenchPort
        Start-AuthorityProcess -RepoRoot $resolvedBasestationRoot -PythonExe $resolvedPythonPath -Port $AuthorityPort
    }
    default {
        $listeners = @(Get-PortListeners -Ports $allKnownPorts)
        if ($listeners.Count -eq 0) {
            Write-Output 'No active listeners found on known EHN Windows preview ports.'
        } else {
            $listeners | Format-Table Port, ProcessId, Name, CommandLine -AutoSize | Out-String | Write-Output
        }
    }
}

Write-Output 'After restart, reload the browser with a cache-busting query string if the UI still looks stale.'
