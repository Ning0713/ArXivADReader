param(
    [Parameter(Position = 0)]
    [ValidateSet("update", "retry", "preview", "status", "help")]
    [string]$Command = "status",
    [Parameter(Position = 1)]
    [string]$Date
)

$ErrorActionPreference = "Stop"
$repo = "Ning0713/ArXivADReader"
$workflow = "update-and-deploy.yml"
$siteUrl = "https://adpaper.ning0713.top"

function Resolve-Date([string]$value) {
    if ([string]::IsNullOrWhiteSpace($value)) {
        return (Get-Date).ToString("yyyy-MM-dd")
    }
    if ($value -eq "today") {
        return (Get-Date).ToString("yyyy-MM-dd")
    }
    if ($value -notmatch '^\d{4}-\d{2}-\d{2}$') {
        throw "Date must use YYYY-MM-DD"
    }
    try { [datetime]::ParseExact($value, "yyyy-MM-dd", $null) | Out-Null }
    catch { throw "Invalid date: $value" }
    return $value
}

function Show-Status {
    Write-Output (gh run list --repo $repo --workflow $workflow --limit 5 --json databaseId,status,conclusion,url,createdAt,displayTitle)
    try {
        $response = Invoke-WebRequest -Uri $siteUrl -UseBasicParsing -TimeoutSec 20
        Write-Output ("site_http=" + [int]$response.StatusCode)
    } catch {
        Write-Output ("site_http=unreachable: " + $_.Exception.Message)
    }
}

switch ($Command) {
    "help" {
        Write-Output "update [date] | retry [date] | preview [date] | status"
    }
    "status" { Show-Status }
    "update" {
        $target = Resolve-Date $Date
        gh workflow run $workflow --repo $repo --ref main --field date=$target --field force=false --field dry_run=false
        Write-Output ("dispatched update for " + $target)
    }
    "retry" {
        $target = Resolve-Date $Date
        gh workflow run $workflow --repo $repo --ref main --field date=$target --field force=true --field dry_run=false
        Write-Output ("dispatched retry for " + $target)
    }
    "preview" {
        $target = Resolve-Date $Date
        gh workflow run $workflow --repo $repo --ref main --field date=$target --field force=true --field dry_run=true
        Write-Output ("dispatched preview for " + $target)
    }
}
