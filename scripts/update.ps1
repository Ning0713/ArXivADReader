param(
    [string]$Date = "today",
    [switch]$Force,
    [switch]$AllowArxivDiscovery,
    [string]$Config = "config/config.yml"
)
$ErrorActionPreference = "Stop"
$args = @("-m", "adpaper", "--config", $Config, "update", "--date", $Date)
if ($Force) { $args += "--force" }
if ($AllowArxivDiscovery) { $args += "--allow-arxiv-discovery" }
python @args

