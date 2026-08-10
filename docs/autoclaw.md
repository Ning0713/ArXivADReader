# AutoClaw and QQ Operations

The project data and code live in this repository. AutoClaw only dispatches a
GitHub Actions workflow through `ops/autoclaw.ps1`; it does not read or edit the
C-drive workspace during normal operation.

## First-time setup

```powershell
gh auth login -h github.com
gh auth status
```

Run commands from the repository root, or configure the AutoClaw tool to call
the absolute script path. The script validates dates and accepts only:

```text
update [date]
retry [date]
preview [date]
status
help
```

The corresponding QQ phrases are `更新论文`, `补跑 YYYY-MM-DD`, `预览
YYYY-MM-DD`, `状态`, and `帮助`. A scheduled status task can call `status` at
22:30 Asia/Shanghai on workdays and forward the compact result to QQ.

Never interpolate arbitrary QQ text into PowerShell. Never put QQ tokens or
GitHub credentials in this repository.

