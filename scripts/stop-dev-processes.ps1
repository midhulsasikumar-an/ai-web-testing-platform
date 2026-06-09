param(
  [int[]]$Ports = @(3000, 3001, 8001)
)

$ErrorActionPreference = "SilentlyContinue"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$escapedRoot = [regex]::Escape($repoRoot)
$candidateIds = New-Object System.Collections.Generic.HashSet[int]

function Test-ProjectDevProcess {
  param($ProcessInfo)

  $cmd = $ProcessInfo.CommandLine
  if (-not $cmd) { return $false }

  $inRepo = $cmd -match $escapedRoot
  $isFrontendDev =
    $cmd -match "npm(.cmd)?[\""]?\s+--prefix\s+frontend\s+run\s+dev" -or
    $cmd -match "next(.cmd)?[\""]?\s+dev" -or
    $cmd -match "frontend\\node_modules\\.*next"
  $isBackendDev = $cmd -match "uvicorn\s+backend\.server:app"

  return $inRepo -and ($isFrontendDev -or $isBackendDev)
}

foreach ($port in $Ports) {
  Get-NetTCPConnection -LocalPort $port -State Listen |
    ForEach-Object {
      if ($_.OwningProcess -and $_.OwningProcess -ne $PID) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($_.OwningProcess)"
        if ($owner -and (Test-ProjectDevProcess $owner)) {
          [void]$candidateIds.Add([int]$_.OwningProcess)
        }
      }
    }
}

Get-CimInstance Win32_Process |
  Where-Object { Test-ProjectDevProcess $_ } |
  ForEach-Object {
    if ($_.ProcessId -and $_.ProcessId -ne $PID) {
      [void]$candidateIds.Add([int]$_.ProcessId)
    }
  }

$stopped = @()
foreach ($id in @($candidateIds)) {
  $children = Get-CimInstance Win32_Process |
    Where-Object { $_.ParentProcessId -eq $id -and (Test-ProjectDevProcess $_) } |
    ForEach-Object { [int]$_.ProcessId }

  foreach ($childId in $children) {
    if ($childId -ne $PID) {
      [void]$candidateIds.Add($childId)
    }
  }
}

foreach ($id in @($candidateIds)) {
  $process = Get-Process -Id $id
  if (-not $process) { continue }

  try {
    Stop-Process -Id $id -Force
    $stopped += "$id/$($process.ProcessName)"
  } catch {
    Write-Warning "Could not stop process ${id}: $($_.Exception.Message)"
  }
}

if ($stopped.Count -gt 0) {
  Write-Host "Stopped stale dev processes: $($stopped -join ', ')"
} else {
  Write-Host "No stale dev processes found."
}
