param(
    [Parameter(Position = 0)]
    [ValidateSet("update", "retry", "preview", "status", "help")]
    [string]$Command = "status",
    [Parameter(Position = 1)]
    [string]$Date,
    [Parameter(Position = 2)]
    [ValidateSet("ad", "ac", "all")]
    [string]$Project,
    [switch]$PlanOnly
)

$ErrorActionPreference = "Stop"
$settings = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'projects.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $Project) { $Project = $settings.default_project }

function Invoke-Gh([string[]]$Arguments) {
    & gh @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub CLI command failed. Run 'gh auth status' and retry."
    }
}

function Resolve-Date([string]$value) {
    if ([string]::IsNullOrWhiteSpace($value)) {
        $china = [TimeZoneInfo]::FindSystemTimeZoneById('China Standard Time')
        return [TimeZoneInfo]::ConvertTimeFromUtc([datetime]::UtcNow, $china).ToString('yyyy-MM-dd')
    }
    if ($value -eq "today") {
        $china = [TimeZoneInfo]::FindSystemTimeZoneById('China Standard Time')
        return [TimeZoneInfo]::ConvertTimeFromUtc([datetime]::UtcNow, $china).ToString('yyyy-MM-dd')
    }
    if ($value -notmatch '^\d{4}-\d{2}-\d{2}$') {
        throw "Date must use YYYY-MM-DD"
    }
    try { [datetime]::ParseExact($value, "yyyy-MM-dd", $null) | Out-Null }
    catch { throw "Invalid date: $value" }
    return $value
}

if ($Command -eq 'help') {
    Write-Output 'autoclaw.ps1 update|retry|preview [YYYY-MM-DD|today] -Project ad|ac|all [-PlanOnly]'
    Write-Output 'autoclaw.ps1 status -Project ad|ac|all'
    Write-Output ('default_project=' + $settings.default_project)
    exit 0
}
if ($Project -notin @('ad', 'ac', 'all')) { throw 'Unknown project' }
if ($Command -eq 'status' -and $Date) { throw 'status does not accept a date' }
if ($Command -in @('retry', 'preview') -and -not $Date) { throw 'retry/preview require a date or today' }
$targetDate = if ($Command -ne 'status') { Resolve-Date $Date } else { '' }
$targets = if ($Project -eq 'all') { @('ad', 'ac') } else { @($Project) }
$failures = @()

foreach ($projectId in $targets) {
    $entry = $settings.projects.$projectId
    if (-not $entry -or $entry.repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
        throw "Invalid repository for project $projectId"
    }
    if ($Command -eq 'status') {
        $ghArgs = @('run', 'list', '--repo', $entry.repository, '--workflow', $entry.workflow,
            '--limit', '5', '--json', 'databaseId,status,conclusion,url,createdAt,displayTitle')
    } else {
        $forceValue = if ($Command -in @('retry', 'preview')) { 'true' } else { 'false' }
        $dryValue = if ($Command -eq 'preview') { 'true' } else { 'false' }
        $ghArgs = @('workflow', 'run', $entry.workflow, '--repo', $entry.repository,
            '--ref', 'main', '--field', "date=$targetDate", '--field', "force=$forceValue",
            '--field', "dry_run=$dryValue")
    }
    if ($PlanOnly) {
        [ordered]@{ project=$projectId; repository=$entry.repository; arguments=$ghArgs } |
            ConvertTo-Json -Compress
        continue
    }
    try {
        Write-Output ("project={0} repository={1}" -f $projectId, $entry.repository)
        Invoke-Gh $ghArgs
        if ($Command -eq 'status') {
            $httpCode = & python -c 'import sys, urllib.request; print(urllib.request.urlopen(sys.argv[1], timeout=20).status)' $entry.site_url 2>$null
            if ($LASTEXITCODE -eq 0) { Write-Output "site_http=$httpCode" }
            else { Write-Output 'site_http=unreachable' }
        } else {
            Write-Output "dispatched $Command for $targetDate; use status to check completion"
        }
    } catch {
        $failures += $projectId
        Write-Warning ("project={0}: {1}" -f $projectId, $_.Exception.Message)
    }
}
if ($failures.Count) { throw ('Failed projects: ' + ($failures -join ', ')) }
