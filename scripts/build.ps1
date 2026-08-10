param([string]$Config = "config/config.yml")
$ErrorActionPreference = "Stop"
python -m adpaper --config $Config build

